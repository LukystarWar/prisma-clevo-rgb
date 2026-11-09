"""PySide6 control panel for the Clevo/Gigabyte keyboard RGB LED.

Dark, neon-green visual theme (see theme.py). Functionally: pick a
predefined effect (static color, rainbow cycle, breathing, off). There is
no per-zone control: this keyboard (Kb_Type 6, Gigabyte G5 KC) was
confirmed to have a single physical LED zone - see CLAUDE.md "Regras de
zona e cor" for how that was established.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import effects
import scheduled_task
import startup
import theme
from clevo_kb import RGB, ClevoKeyboard, KeyboardNotSupportedError
from icons import make_icon
from widgets import ToggleSwitch

C = theme.COLORS

EFFECTS = (
    ("static", "ESTÁTICO"),
    ("rainbow", "ARCO-ÍRIS"),
    ("breathing", "RESPIRAÇÃO"),
    ("off", "DESLIGADO"),
)
def _app_root() -> Path:
    """Project root in dev, or the PyInstaller bundle dir when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


ICON_PATH = _app_root() / "assets" / "icon.ico"
TICK_MS_RANGE = (20, 120)  # fastest..slowest timer interval, mapped from the speed slider
SPEED_LABELS = {range(1, 4): "LENTO", range(4, 8): "MÉDIO", range(8, 11): "RÁPIDO"}


def _rgb_to_qcolor(c: RGB) -> QColor:
    return QColor(c.r, c.g, c.b)


def _qcolor_to_rgb(c: QColor) -> RGB:
    return RGB(c.red(), c.green(), c.blue())


def _add_shadow(widget: QWidget) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(28)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 0, 0, 160))
    widget.setGraphicsEffect(shadow)


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("card")
    _add_shadow(card)
    outer = QVBoxLayout(card)
    outer.setContentsMargins(18, 16, 18, 16)
    outer.setSpacing(12)
    label = QLabel(title)
    label.setObjectName("sectionLabel")
    outer.addWidget(label)
    return card, outer


class ColorSwatchButton(QPushButton):
    """A button that shows its assigned color as its own background."""

    def __init__(self, color: RGB) -> None:
        super().__init__()
        self.color = color
        self.setFixedSize(52, 52)
        self.setCursor(Qt.PointingHandCursor)
        self._refresh()

    def set_color(self, color: RGB) -> None:
        self.color = color
        self._refresh()

    def _refresh(self) -> None:
        self.setStyleSheet(
            f"background-color: rgb({self.color.r},{self.color.g},{self.color.b});"
            f"border: 2px solid {C['border']}; border-radius: 12px;"
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Prisma - Keyboard RGB Control")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        else:
            self.setWindowIcon(make_icon("rainbow", C["accent"], 64))
        self.setMinimumWidth(440)

        self.kb: ClevoKeyboard | None = None
        self.kb_supported = False
        self.color = RGB(0, 150, 255)  # used by "Estático" (direct) and "Respiração" (as base color)
        self._hue = 0.0
        self._phase = 0.0
        self._task_paused = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self._build_ui()
        self._init_hardware()
        # _build_ui() already ran _on_effect_changed() once, but self.kb didn't
        # exist yet at that point, so nothing was actually sent - do it now.
        self._on_effect_changed()

    # ---------- hardware ----------

    def _init_hardware(self) -> None:
        try:
            self.kb = ClevoKeyboard()
            kb_type = self.kb.get_kb_type()
            self.kb.assert_supported()
            self.kb_supported = True
            self._set_status(True, f"Kb_Type {kb_type} detectado")
        except KeyboardNotSupportedError as exc:
            self.kb_supported = False
            self._set_status(False, str(exc))
            self._set_controls_enabled(False)
        except OSError as exc:
            self.kb = None
            self.kb_supported = False
            self._set_status(False, f"InsydeDCHU.dll não encontrada: {exc}")
            self._set_controls_enabled(False)

    def _set_status(self, ok: bool, detail: str) -> None:
        self.status_pill.setText("●  ONLINE" if ok else "●  ERRO")
        self.status_pill.setObjectName("statusPillOk" if ok else "statusPillError")
        self.status_pill.setStyleSheet("")  # force re-polish with the new objectName
        self.subtitle_label.setText(detail)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.effects_card.setEnabled(enabled)
        self.speed_card.setEnabled(enabled)
        self.color_card.setEnabled(enabled)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("root")
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 26)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel(f'<span style="color:{C["accent"]}">PRISMA</span>')
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addStretch()
        self.status_pill = QLabel("●  ...")
        self.status_pill.setObjectName("statusPillOk")
        header.addWidget(self.status_pill)
        root.addLayout(header)

        self.subtitle_label = QLabel("Inicializando...")
        self.subtitle_label.setObjectName("subtleLabel")
        root.addWidget(self.subtitle_label)

        # Effect card
        self.effects_card, eff_layout = _card("EFEITO")
        pills_row = QHBoxLayout()
        pills_row.setSpacing(8)
        self.effect_group = QButtonGroup(self)
        self.effect_group.setExclusive(True)
        self._effect_icons: dict[str, QToolButton] = {}
        for key, label in EFFECTS:
            btn = QToolButton()
            btn.setObjectName("effectPill")
            btn.setCheckable(True)
            btn.setText(label)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(22, 22))
            btn.setIcon(make_icon(key, C["text_secondary"]))
            btn.setMinimumHeight(64)
            btn.setProperty("effectKey", key)
            btn.toggled.connect(lambda checked, k=key, b=btn: self._on_pill_toggled(b, k, checked))
            self.effect_group.addButton(btn)
            pills_row.addWidget(btn, 1)
            self._effect_icons[key] = btn
        eff_layout.addLayout(pills_row)
        root.addWidget(self.effects_card)
        self._effect_icons["static"].setChecked(True)

        # Color card
        self.color_card, color_layout = _card("COR")
        color_row = QHBoxLayout()
        color_row.setSpacing(14)
        self.color_button = ColorSwatchButton(self.color)
        self.color_button.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_button)

        color_text_col = QVBoxLayout()
        color_text_col.setSpacing(2)
        self.hex_label = QLabel(self._hex_text())
        self.hex_label.setObjectName("hexLabel")
        color_text_col.addWidget(self.hex_label)
        hint = QLabel("Usada pelo Estático e como base da Respiração")
        hint.setObjectName("subtleLabel")
        color_text_col.addWidget(hint)
        color_row.addLayout(color_text_col)
        color_row.addStretch()

        choose_btn = QPushButton("ESCOLHER")
        choose_btn.setObjectName("ghostButton")
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.clicked.connect(self._pick_color)
        color_row.addWidget(choose_btn)

        color_layout.addLayout(color_row)
        root.addWidget(self.color_card)

        # Speed card
        self.speed_card, speed_layout = _card("VELOCIDADE")
        speed_row = QHBoxLayout()
        speed_row.setSpacing(14)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self.speed_slider, 1)
        self.speed_value_label = QLabel(self._speed_text())
        self.speed_value_label.setObjectName("sectionLabel")
        self.speed_value_label.setMinimumWidth(56)
        speed_row.addWidget(self.speed_value_label)
        speed_layout.addLayout(speed_row)
        root.addWidget(self.speed_card)

        # Automation card
        automation_card, automation_layout = _card("AUTOMAÇÃO")
        automation_row = QHBoxLayout()
        automation_row.setSpacing(14)
        automation_text_col = QVBoxLayout()
        automation_text_col.setSpacing(2)
        auto_title = QLabel("Pausar ciclo automático")
        auto_title.setObjectName("sectionLabel")
        automation_text_col.addWidget(auto_title)
        auto_hint = QLabel("Evita que a tarefa agendada dispute o LED com este app")
        auto_hint.setObjectName("subtleLabel")
        automation_text_col.addWidget(auto_hint)
        automation_row.addLayout(automation_text_col)
        automation_row.addStretch()
        self.pause_task_switch = ToggleSwitch()
        self.pause_task_switch.toggled.connect(self._on_pause_task_toggled)
        automation_row.addWidget(self.pause_task_switch)
        automation_layout.addLayout(automation_row)

        startup_row = QHBoxLayout()
        startup_row.setSpacing(14)
        startup_text_col = QVBoxLayout()
        startup_text_col.setSpacing(2)
        startup_title = QLabel("Iniciar com o Windows")
        startup_title.setObjectName("sectionLabel")
        startup_text_col.addWidget(startup_title)
        startup_hint = QLabel("Abre minimizado na bandeja ao ligar o PC")
        startup_hint.setObjectName("subtleLabel")
        startup_text_col.addWidget(startup_hint)
        startup_row.addLayout(startup_text_col)
        startup_row.addStretch()
        self.startup_switch = ToggleSwitch()
        self.startup_switch.blockSignals(True)
        self.startup_switch.setChecked(startup.is_enabled())
        self.startup_switch.blockSignals(False)
        self.startup_switch.toggled.connect(self._on_startup_toggled)
        startup_row.addWidget(self.startup_switch)
        automation_layout.addLayout(startup_row)

        root.addWidget(automation_card)

        root.addStretch()
        self.setCentralWidget(central)
        self._on_effect_changed()
        self._build_tray()

    # ---------- effect selection ----------

    def _on_pill_toggled(self, button: QToolButton, key: str, checked: bool) -> None:
        button.setIcon(make_icon(key, C["accent_strong"] if checked else C["text_secondary"]))
        if checked:
            self._on_effect_changed()

    def _current_effect(self) -> str:
        for key, btn in self._effect_icons.items():
            if btn.isChecked():
                return key
        return "static"

    def _speed_to_interval_ms(self) -> int:
        fastest, slowest = TICK_MS_RANGE
        speed = self.speed_slider.value()  # 1 (slow) .. 10 (fast)
        return int(slowest - (speed - 1) * (slowest - fastest) / 9)

    def _speed_text(self) -> str:
        speed = self.speed_slider.value()
        for rng, label in SPEED_LABELS.items():
            if speed in rng:
                return label
        return ""

    def _hex_text(self) -> str:
        return f"#{self.color.r:02X}{self.color.g:02X}{self.color.b:02X}"

    def _on_effect_changed(self) -> None:
        self.timer.stop()
        effect = self._current_effect()
        if not self.kb_supported:
            return
        if effect == "static":
            self.kb.set_color(self.color)
        elif effect == "off":
            self.kb.set_color(RGB(0, 0, 0))
        elif effect == "rainbow":
            self._hue = 0.0
            self.timer.start(self._speed_to_interval_ms())
        elif effect == "breathing":
            self._phase = 0.0
            self.timer.start(self._speed_to_interval_ms())

    def _on_speed_changed(self) -> None:
        self.speed_value_label.setText(self._speed_text())
        if self.timer.isActive():
            self.timer.setInterval(self._speed_to_interval_ms())

    def _tick(self) -> None:
        effect = self._current_effect()
        if effect == "rainbow":
            self.kb.set_color(effects.hue_to_rgb(self._hue))
            self._hue = (self._hue + 2) % 360
        elif effect == "breathing":
            factor = effects.breathing_scale(self._phase)
            self.kb.set_color(effects.scale_rgb(self.color, factor))
            self._phase = (self._phase + 2) % 360
        else:
            self.timer.stop()

    # ---------- color picker ----------

    def _pick_color(self) -> None:
        from PySide6.QtWidgets import QColorDialog

        chosen = QColorDialog.getColor(_rgb_to_qcolor(self.color), self, "Cor")
        if not chosen.isValid():
            return
        self.color = _qcolor_to_rgb(chosen)
        self.color_button.set_color(self.color)
        self.hex_label.setText(self._hex_text())
        if self._current_effect() == "static" and self.kb:
            self.kb.set_color(self.color)

    # ---------- scheduled task ----------

    def _on_pause_task_toggled(self, checked: bool) -> None:
        try:
            if checked:
                scheduled_task.pause()
                self._task_paused = True
            else:
                scheduled_task.resume()
                self._task_paused = False
        except PermissionError as exc:
            self.pause_task_switch.blockSignals(True)
            self.pause_task_switch.setChecked(not checked)
            self.pause_task_switch.blockSignals(False)
            QMessageBox.warning(
                self,
                "Permissão insuficiente",
                "Não foi possível alterar a tarefa agendada (ela roda como SYSTEM).\n"
                f"Execute este app como administrador para isso funcionar.\n\nDetalhe: {exc}",
            )

    def _on_startup_toggled(self, checked: bool) -> None:
        try:
            startup.set_enabled(checked)
        except OSError as exc:
            self.startup_switch.blockSignals(True)
            self.startup_switch.setChecked(not checked)
            self.startup_switch.blockSignals(False)
            QMessageBox.warning(self, "Erro", f"Não foi possível alterar a inicialização: {exc}")

    # ---------- system tray ----------

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Prisma - controle RGB do teclado")

        menu = QMenu()
        show_action = QAction("Abrir Prisma", self)
        show_action.triggered.connect(self._restore_from_tray)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self._tray_notice_shown = False
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self) -> None:
        if self._task_paused:
            try:
                scheduled_task.resume()
            except PermissionError:
                pass
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Closing the window just sends it to the tray - the effect keeps
        # running. Only the tray menu's "Sair" actually exits the app.
        event.ignore()
        self.hide()
        if not self._tray_notice_shown:
            self.tray.showMessage(
                "Prisma continua rodando",
                "O efeito continua ativo. Clique no ícone da bandeja para abrir de novo.",
                self.windowIcon(),
                3000,
            )
            self._tray_notice_shown = True


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # stay alive in the tray after the window is hidden
    app.setStyleSheet(theme.QSS)
    window = MainWindow()
    theme.enable_dark_titlebar(window)
    if "--minimized" not in sys.argv:
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
