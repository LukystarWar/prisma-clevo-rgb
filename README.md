# Prisma

Painel de controle (PySide6) para o RGB do teclado de um notebook Gigabyte
G5 KC (base Clevo, chip Insyde). Permite:

- Escolher um efeito predefinido: **Estático**, **Arco-íris (cycle)**,
  **Respiração** ou **Desligado**.
- Um único seletor de **Cor**, que vale para o efeito selecionado: cor fixa
  no **Estático**, cor em torno da qual a **Respiração** pulsa. (Não há
  controle por zona: este teclado foi testado e confirmado como tendo uma
  única zona física de luz, ver `CLAUDE.md`.)
- Pausar/retomar a tarefa agendada `KeyboardColorCycle` (que já faz um ciclo
  automático em segundo plano) para os dois não disputarem o LED ao mesmo
  tempo.
- Iniciar com o Windows (minimizado na bandeja) e rodar na bandeja do
  sistema: fechar a janela (X) só esconde o app, o efeito continua ativo;
  "Sair" pelo menu da bandeja é que encerra de verdade.

Não existe app/driver oficial de terceiros envolvido além da própria DLL da
Insyde que já vem com o `ControlCenter` do fabricante; este projeto fala
direto com ela. Veja `CLAUDE.md` para o protocolo e como cada parte foi
validada no hardware real.

## Requisitos

- Windows com `C:\Program Files (x86)\ControlCenter\InsydeDCHU.dll` presente
  (instalado junto com o utilitário do fabricante; é essa DLL que fala com
  o teclado; a UI deste projeto não precisa do app do fabricante aberto).
- Python 3.12 (instale pelo [python.org](https://www.python.org/downloads/)
  ou via `winget install Python.Python.3.12`).

## Rodando

Na pasta do projeto:

```powershell
.venv\Scripts\python.exe main.py
```

O ambiente virtual `.venv` já tem o `PySide6-Essentials` instalado (ver
`requirements.txt`). Para recriar do zero:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Empacotando (.exe + atalho)

Gera um executável standalone (não precisa do Python instalado para rodar)
com o ícone próprio do Prisma. Na pasta do projeto:

```powershell
.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --name Prisma --icon assets\icon.ico --paths src --add-data "assets;assets" main.py
```

Gera `dist\Prisma\Prisma.exe` (+ pasta `_internal`). Para recriar o ícone a
partir do SVG (`assets/icon.svg`), rode `tools\build_icon.py` antes.

## Estrutura

```
main.py                  ponto de entrada
src/clevo_kb.py           wrapper ctypes da InsydeDCHU.dll (zonas, cores, Kb_Type)
src/effects.py            matemática dos efeitos (hue->RGB, respiração) - sem Qt/hardware
src/scheduled_task.py      pausa/retoma a tarefa agendada KeyboardColorCycle
src/gui.py                 janela PySide6 (monta o layout e liga os eventos aos módulos acima)
src/theme.py               paleta de cores + QSS (tema escuro/verde) + dark titlebar (DWM)
src/icons.py               ícones SVG inline dos efeitos, recoloridos em runtime
src/widgets.py             ToggleSwitch (switch deslizante animado) e outros widgets customizados
src/startup.py              liga/desliga "iniciar com o Windows" via registro (HKCU\...\Run)
assets/icon.svg            arte original do ícone (prisma dividindo luz em RGB)
assets/icon.ico            ícone multi-resolução gerado a partir do SVG (usado no .exe e na janela)
tools/build_icon.py        regenera assets/icon.ico a partir de assets/icon.svg
scripts/ColorCycle.ps1      script da tarefa agendada (ciclo contínuo, já instalado)
scripts/install_task.ps1    (re)instala a tarefa agendada a partir do script acima
docs/reference/             dump de IL do app oficial (CC.RGBKB, CC.InsydeAcpiProt) -
                            é a fonte de onde o protocolo foi extraído
```

## Manutenção

Para qualquer mudança no protocolo de hardware (novas zonas, novos efeitos,
outro modelo de teclado), leia **CLAUDE.md** primeiro - ele documenta as
regras de zona/cor, o que foi testado fisicamente e o que é só inferência da
engenharia reversa (IL), e os efeitos colaterais conhecidos.

## Créditos

Desenvolvido por **CastroLabs**.
