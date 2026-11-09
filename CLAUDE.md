# CLAUDE.md - contexto para manutenção

Projeto: controle do RGB do teclado de um notebook **Gigabyte G5 KC**
(chassi Clevo, EC/chip **Insyde**). Veio com o app oficial
`CLEVOCO.LedKeyboardSetting` (pacote MSIX em
`C:\Program Files\WindowsApps\CLEVOCO.LedKeyboardSetting_3.32.0.0_x64__6h6z29zh29qx0\`)
e o `ControlCenter` do fabricante, que instala
`C:\Program Files (x86)\ControlCenter\InsydeDCHU.dll`.

O app oficial nunca foi usado para controlar o teclado neste fluxo - ele
serviu só como fonte para engenharia reversa (dump de IL). Todo o controle
real passa direto pela DLL via `ctypes`/P-Invoke.

## Como o protocolo foi descoberto

`LedKeyboardSetting.exe` é .NET. Fizemos `ReflectionOnlyLoadFrom` nele e
dumpamos o IL de bytecode das classes relevantes (script em
`docs/reference/dump_il.ps1`, saídas em `docs/reference/*.txt`):

- `CC.RGBKB` (`docs/reference/rgbkb.txt`) - a classe que de fato monta e
  envia os comandos de LED (`SetColor`, `SetCycleMode`, `SetBreathMode`
  etc.) via `InsydeAcpiProt::SetDCHU_Data`.
- `CC.InsydeAcpiProt` (`docs/reference/acpiprot.txt`) - camada de
  leitura/escrita de "AppSettings" (um cache/registro próprio do app, **não**
  é o hardware) e das poucas chamadas que de fato tocam o hardware
  (`GetDCHU_Data_Integer`, `GetDCHU_Data_Buffer`, `SetDCHU_Data` -
  essas três são P/Invoke extern, por isso não aparecem com corpo no dump).
- `CC.KBModule` (`docs/reference/kbmodule.txt`) - orquestra qual sub-classe
  (RGBKB/WhiteKB/PerkeyKB) trata cada `Kb_Type`.

**Importante:** a maior parte das funções em `acpiprot.txt`
(`ReadAcpi*`/`WriteAcpi*`) só lê/escreve o cache de configurações do app
(`ReadAppSettings`/`WriteAppSettings`, offsets numéricos tipo "offset 80 =
Status"). Isso **não é o estado real do LED** - é só o que o app lembra que
mandou. O único caminho que realmente fala com o teclado é
`SetDCHU_Data(103, bytes, 4)` (escrita) e `GetDCHU_Data_Integer`/
`GetDCHU_Data_Buffer` (leitura). `src/clevo_kb.py` usa só esse caminho.

## Regras de zona e cor (confirmado fisicamente)

Hardware deste notebook: `Kb_Type = 6` (lido via `ClevoKeyboard.get_kb_type()`).
`SUPPORTED_KB_TYPES = (2, 6, 22)` em `src/clevo_kb.py` são os tipos que a
classe `RGBKB` trata (vs. `WhiteKB`/`PerkeyKB` para outros `Kb_Type`) - só
`6` foi testado no hardware real; `2` e `22` são inferência do IL.

Toda escrita de LED é uma única chamada:

```
SetDCHU_Data(command=103, data=<4 bytes little-endian de `payload`>, length=4)
payload = (zone_code << 24) + color_value
```

**Código de zona** (`src/clevo_kb.py::Zone`), vindo de `RGBKB::SetColor`:

| Zona      | código  | Funciona neste hardware? |
|-----------|---------|---------------------------|
| Esquerda  | `0x00`  | **Não** - confirmado no-op |
| Meio      | `0xF0`  | **Sim** - é o único que funciona |
| Direita   | `0xF1`  | **Não** - confirmado no-op |

### ESTE TECLADO TEM UMA ÚNICA ZONA FÍSICA DE LUZ

Isso foi mal entendido numa versão anterior deste documento (que assumia 3
zonas independentes porque enviar a mesma cor para as 3 "funcionava" - mas
isso não provava independência, só que a cor igual mascarava o problema).
Testado depois, passo a passo, com o usuário olhando o teclado físico entre
cada comando:

1. `Left=Red` isolado → **nada mudou**.
2. (depois, como novo baseline) `Mid=Yellow` isolado → **teclado inteiro
   ficou amarelo**.
3. `Right=Blue` isolado → **nada mudou** (continuou amarelo).
4. Os três em sequência (`Left=Red, Mid=Green, Right=Blue`) → **teclado
   inteiro ficou verde** (a cor do `Mid`, não a última enviada nem cores
   separadas por zona).

Conclusão: **só o código `0xF0` (Mid) tem efeito visível; `0x00` e `0xF1`
são aceitos pela DLL (não dão erro, retornam o mesmo `103` de sempre) mas
não acendem nada.** `src/clevo_kb.py::WORKING_ZONE = Zone.MID` e o método
`ClevoKeyboard.set_color()` usam só esse código. **Não use
`set_zone_color(Zone.LEFT, ...)` ou `Zone.RIGHT` esperando efeito nesta
máquina** - eles existem só para documentar o protocolo (e para o caso de
testar em outro modelo que realmente tenha 3 zonas).

(O IL também mostra `0xF2`→`0xF3`→`0xF6` para `KbPart` 4..6, e que Logo
(`KbPart=7`)/LightBar (`KbPart=8`) parecem cair no mesmo código `0x00` que
Esquerda - nenhum desses foi testado; dado que até os códigos "oficiais"
Left/Right não funcionam aqui, não há motivo para supor que funcionariam.)

Se outro notebook/modelo (`Kb_Type` diferente, ou um G5 com firmware
diferente) for suportado no futuro, **repita este teste de isolar cada
zona uma por vez com o usuário olhando** antes de assumir que as zonas
existem de verdade nesse hardware.

**`color_value`** - há duas fórmulas no IL, escolhidas por `Kb_Type`:

- `Kb_Type == 6 ou 22` (**nosso caso, confirmado**): sem escala -
  `color_value = (B << 16) | (R << 8) | G`.
- qualquer outro tipo (ramo "else", não testado): o canal B é escalado por
  `0.784313725` antes de entrar - `color_value = (round(B*0.784313725) << 16) | (R << 8) | G`.
  Se algum dia este projeto rodar em outro `Kb_Type`, implemente esse
  segundo ramo antes de confiar na cor.

Fórmula de cor validada visualmente (vermelho/verde/azul, via `Zone.MID`):
ver tabela e histórico de testes acima. Use sempre `ClevoKeyboard.set_color()`
(não `set_zone_color` com `Zone.LEFT`/`Zone.RIGHT`, que são no-ops aqui).

### A respeito do valor de retorno de `SetDCHU_Data`

Em todos os testes, `SetDCHU_Data` retornou `103` - o próprio código do
comando enviado, não um indicador de sucesso/erro. **Não trate o retorno
como status.** A única forma confiável de saber se funcionou é olhar o
teclado (ou, para testes futuros, perguntar ao usuário - não há leitura de
hardware que confirme a cor atual de forma confiável; `ReadAcpi*Color` lê o
cache do app, não o LED).

## O que NÃO funcionou (e por quê isso importa)

O comando de "modo" nativo do firmware (ex.: `SetCycleMode` do IL, que manda
`SetDCHU_Data(103, 0x33010000, 4)` uma única vez para ativar o efeito de
ciclo embutido do EC) foi testado isoladamente e **não produziu nenhuma
mudança visível**. Por isso:

- `scripts/ColorCycle.ps1` **não** usa o modo nativo - ele mesmo gera a
  animação (loop de HSV→RGB escrevendo as 3 zonas a cada ~55ms).
- `src/effects.py` + `src/gui.py` seguem o mesmo princípio: todo efeito
  (arco-íris, respiração) é um loop no próprio processo que escreve cor via
  `set_all_zones` repetidamente - nunca um "selecionar modo X e deixar o EC
  animar sozinho".

Se um dia for necessário investigar o modo nativo de novo, o resto do
dispatch de modos está em `RGBKB::SetMode()` dentro de `rgbkb.txt` (switch
por `Mode`: 1=Custom, 2=Breath, 3=Random, 4=Flash, 5=Tempo, 6=Dance,
7=Wave, 8=Cycle, default=AllColor) - mas antes de confiar neles, repita o
mesmo processo de teste manual com o usuário descrito abaixo.

## Conflito conhecido: tarefa agendada vs. este app

A tarefa agendada `KeyboardColorCycle` (instalada por
`scripts/install_task.ps1`, roda `scripts/ColorCycle.ps1` como SYSTEM, sem
limite de tempo, nos gatilhos boot/logon/retomada de suspensão) fica
escrevendo cor nas mesmas 3 zonas em loop infinito. Se ela estiver ativa
**ao mesmo tempo** que este app, as duas vão alternar/disputar o LED de
forma visualmente quebrada.

`src/scheduled_task.py` dá `pause()`/`resume()` (via `schtasks.exe /End` +
`/DISABLE`, e `/ENABLE` + `/Run` para voltar) - exposto na GUI como o
checkbox "Pausar o ciclo automático...". Como a tarefa roda como SYSTEM,
`pause()`/`resume()` **exigem processo elevado** (admin); sem elevação,
`schtasks.exe` retorna erro e `scheduled_task.py` levanta `PermissionError`
- a GUI já trata isso com um `QMessageBox` avisando para rodar como admin.

Fechar a janela (`closeEvent`) so esconde para a bandeja agora (ver secao
"Bandeja do sistema" abaixo) - a tarefa so e retomada automaticamente ao
"Sair" de verdade pelo menu da bandeja (`_quit_app`), nao ao fechar a janela.

**Recomendação de deploy:** não rode a tarefa agendada e o Prisma com
"Iniciar com o Windows" ativo ao mesmo tempo - escolha um dos dois como
dono do LED. Se o Prisma for o principal, desabilite a tarefa
(`schtasks /Change /TN KeyboardColorCycle /DISABLE`); para voltar ao ciclo
automático antigo, reative com `/ENABLE`.

## Metodologia de teste (siga isso ao mudar o protocolo)

Não há como ler o estado real do LED pelo software (ver seção de retorno de
`SetDCHU_Data` acima). Toda vez que uma hipótese sobre o protocolo for
testada, o fluxo que funcionou nesta sessão foi:

1. Escrever um script/trecho pequeno e isolado que manda **um** comando
   específico.
2. Rodar e perguntar diretamente ao usuário o que ele está vendo no teclado
   *agora* (não assumir sucesso pelo valor de retorno nem pela ausência de
   exceção).
3. Só generalizar/gravar a regra no código depois da confirmação visual.

Isso vale tanto para novos efeitos quanto para dar suporte a outro
`Kb_Type`/modelo de notebook.

## Visual (tema escuro/verde "Razer-like")

A GUI foi redesenhada para um visual escuro premium com acento verde neon,
a pedido do usuário. Decisão: **continuar em PySide6 Widgets** (não migrar
para Qt Quick/QML, Electron, web, etc.) - para uma janela utilitária de
~440px de largura, QSS + alguns widgets customizados (`QPainter`) já dão
controle visual total, e trocar de stack só adicionaria risco/esforço sem
ganho real. Se um dia a UI crescer muito (múltiplas telas, navegação), vale
reconsiderar.

- `src/theme.py` é a ÚNICA fonte da paleta (`COLORS`) e do QSS
  (`app.setStyleSheet(theme.QSS)` em `gui.py::main()`). Para mudar cores,
  edite só esse dicionário.
- **Ícones SVG não recolorem via QSS** (um `QIcon` é um pixmap já
  renderizado). `icons.make_icon(name, color)` gera um novo pixmap a cada
  cor - por isso os pills de efeito trocam de ícone manualmente no
  `toggled` (`_on_pill_toggled` em `gui.py`) em vez de confiar no QSS para
  o estado `:checked`.
- `widgets.ToggleSwitch` anima via uma `Property` Qt customizada
  (`thumbPos`) + `QPropertyAnimation` - é o padrão certo para animar algo
  dentro de um `paintEvent` próprio; não dá para animar isso só com QSS.
- `theme.enable_dark_titlebar()` é best-effort (ignora qualquer erro) -
  chama `DwmSetWindowAttribute` via `ctypes` para pintar a barra de título
  nativa escura no Windows 10 20H1+/11. Puramente cosmético; nunca deixe
  isso derrubar o app.

## Bandeja do sistema e "iniciar com o Windows"

- `app.setQuitOnLastWindowClosed(False)` em `gui.py::main()` e obrigatorio -
  sem isso, o Qt mata o processo quando a janela principal fecha, mesmo com
  o icone de bandeja ainda visivel. `MainWindow.closeEvent` faz
  `event.ignore()` + `self.hide()` em vez de fechar de verdade; so
  `_quit_app()` (menu "Sair" da bandeja) encerra o processo de fato.
- `src/startup.py` usa `HKEY_CURRENT_USER\...\Run` (nao precisa de admin,
  ao contrario da tarefa agendada em `scheduled_task.py`, que roda como
  SYSTEM). O valor gravado inclui `--minimized`, que `gui.py::main()` le em
  `sys.argv` para nao mostrar a janela ao abrir sozinho no boot - so o
  icone da bandeja aparece.
- Em modo dev (nao congelado), `startup.py` registra `pythonw.exe` (nao
  `python.exe`) para nao piscar uma janela de console no boot.

## Gotchas de desenvolvimento da GUI

- **`.venv\Scripts\python.exe` gera um processo FILHO** com o interpretador
  real (`...\Programs\Python\Python312\python.exe`) em vez de substituir o
  processo. Ao reiniciar o app durante o desenvolvimento, matar só o PID do
  `Start-Process` (ou filtrar por `.Path` contendo o caminho do projeto) mata
  apenas o processo-pai/stub e **deixa a janela real (filho) travada em
  segundo plano** - isso já causou uma sessão inteira de "a janela não
  responde" porque o usuário estava clicando numa janela velha órfã enquanto
  eu abria janelas novas por cima. Para matar de verdade, filtre por
  `CommandLine` (que contém `ClevoKeyboardControl` em ambos os processos):
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'ClevoKeyboardControl' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  ```
- **Um `QTimer` já em execução não aplica um `setValue`/novo cálculo de
  intervalo sozinho.** O slider de velocidade só mudava a velocidade na
  próxima vez que o efeito fosse reselecionado, até conectarmos
  `speed_slider.valueChanged` a um handler que chama
  `self.timer.setInterval(...)` diretamente (`_on_speed_changed` em
  `gui.py`). Qualquer novo controle "ao vivo" (ex.: brilho) precisa do mesmo
  padrão: atualizar o timer/estado imediatamente, não só no próximo restart
  do efeito.
- **A ordem de inicialização importa:** `_build_ui()` roda
  `_on_effect_changed()` uma vez antes de `self.kb` existir (ela só monta a
  tela); por isso `__init__` chama `_on_effect_changed()` de novo depois de
  `_init_hardware()`, senão o estado inicial nunca é de fato enviado ao
  hardware.

## Onde cada coisa roda

- `main.py` / `src/gui.py`: processo do usuário normal, **não precisa** de
  elevação para ler `Kb_Type` ou escrever cor (confirmado - funcionou sem
  prompt de UAC). Só precisa de admin para o checkbox de pausar a tarefa
  agendada.
- `scripts/ColorCycle.ps1` via tarefa agendada: roda como SYSTEM (ver
  `scripts/install_task.ps1`), ininterruptamente, até ser pausado/desativado.
