# Pregão do Café (antes "Painel do Agro")

**Nome do app desde 28/10/2026: "Pregão do Café"** (escolhido pelo usuário; "Preço do Café" foi descartado por ser
genérico e parecido com "Painel do Café", app pago de terceiros). Trocado só nos lugares de pouco impacto: título
do topo ("PREGÃO DO" + "CAFÉ"), `<title>`, apple-mobile-web-app-title, manifest, mensagem do WhatsApp, instalar.html
e textos do perfil do iPhone. MANTIDOS de propósito: URLs/repo `painel-cafe`, arquivos `PainelAgro.apk`/
`PainelAgro.mobileconfig` (e identificadores), cache `painel-agro-vN` e o nome no Android (`AndroidManifest.xml`
label "Painel do Agro" — só muda com APK novo; oferecido junto com ícone novo). Quem já instalou o atalho vê o nome antigo até reinstalar.
**29/10/2026 (pedido: "em todos os lugares"):** links do instalar.html nas mensagens viraram `instalar.html?v=pregao`
(o WhatsApp guardava o resumo antigo do link); perfil do iPhone renomeado para `PregaoDoCafe.mobileconfig`; botão
Android baixa `PregaoDoCafe.apk` (o pages.yml copia o APK da última release também com esse nome; `PainelAgro.apk`
continua para links antigos); `AndroidManifest.xml` label "Pregão do Café" e `build-apk.sh` 3.1 (code 9) — APK 3.1
publicado na release v3.1 (assets PregaoDoCafe.apk + PainelAgro.apk + PainelCafe.apk, mesma assinatura), autorizado pelo
usuário; link alternativo (btnApk2) já aponta para PregaoDoCafe.apk. README renomeado.
**Ícone novo (29/10/2026):** grão escuro (#04172E) sobre azul (#38A3FF), igual ao logo do topo: `res/drawable/ic_launcher.xml`
(APK 3.1), `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` e o ícone embutido no `PregaoDoCafe.mobileconfig`
(gerados com Pillow; risco do grão encurtado ~12,5% em cada ponta, pontas redondas).

App de cotação do café Conilon para um corretor de café do Sul da Bahia (Itamaraju-BA).
O usuário fala português e não é programador: responda em português, com passos simples e
numerados. Ele usa Android; o app também é distribuído para iPhone.

## Links
- App (site): https://davidcaliman-maker.github.io/painel-cafe/
- **Página de instalação (link para divulgar):** https://davidcaliman-maker.github.io/painel-cafe/instalar.html
- APK Android (sempre a última versão): https://github.com/davidcaliman-maker/painel-cafe/releases/latest/download/PainelAgro.apk
  (o nome antigo `PainelCafe.apk` também é publicado em cada release, para links antigos)
- Repositório: https://github.com/davidcaliman-maker/painel-cafe (público; `gh` CLI logado na conta davidcaliman-maker)
- Estatísticas: https://cloud.umami.is (conta do usuário; website id ddb0784e-ceb5-43d2-a619-468fb27c0b8c)

## Como o app funciona
- **Toda a interface está em `app/src/main/assets/index.html`** (HTML/CSS/JS num arquivo só).
- Cada push na `main` publica essa pasta no GitHub Pages via `.github/workflows/pages.yml`.
- **Android** (APK) e **iPhone** (atalho do Safari/PWA ou perfil) carregam a página do site e se
  recarregam sozinhos quando há versão nova (`versao.json`, carimbado pelo workflow com o commit).
  → Mudança de tela = editar `index.html` e dar push. Não precisa gerar APK.
- A cada mudança em `index.html`, suba o nome do cache em `app/src/main/assets/sw.js`
  (`painel-agro-vN` → `vN+1`; hoje v59).
- Teste no navegador (larguras 375 e 412 px) antes de publicar. Para testar local: servidor
  `python -m http.server 8765 -d app/src/main/assets` (contador Umami fica desligado fora do site oficial;
  `.claude/launch.json` tem a configuração "painel" para o preview do Claude). Os JSON gerados
  (historico/intradia/cotacoes/noticias) não existem na cópia local: para simular, gere com
  `python scripts/historico.py ...` em `build/teste/` e copie para assets — e APAGUE antes do commit.
- Antes de publicar uma mudança visual, mostrar ao usuário (preview) e pedir o "pode publicar".

## Topo
- Título "A + D" (28/10/2026): grão num quadradinho arredondado da cor do tema (`.logo`) + "PAINEL DO" fino/claro
  e "AGRO" em negrito na cor do tema (`h1 small`), uma linha só; à direita, botões WhatsApp e tema.

## Telas (barra de abas no rodapé: PAINEL · CÁLCULO · CHUVA · NOTÍCIAS; roteamento por `#calculo`/`#chuva`/`#noticias`)
- **Painel:** card destaque do Conilon (preço grande, selo AO VIVO/FECHADO dd/mm/FERIADO, variação =
  movimento do mercado no dia "+R$ x no dia"), cards Dólar/Londres/N.York (modelo "E" escolhido em 28/10/2026:
  fundo tingido + contorno + número + rodapé "▲ +0,45%"/"▼ −0,69%" em verde/vermelho; 0,00% cinza), faixa em
  pílula "Cotações de HH:MM (há N min)" + botão "↻ ATUALIZAR" (setinha gira enquanto atualiza; modelo "B", 28/10),
  gráfico com seletor HOJE/SEMANA (título `#chTitulo` menor, 24px, pedido 28/10; escolha salva no aparelho; abas Conilon/Londres/N.York/Dólar).
  - SEMANA: 7 pregões (`historico.json`).
  - HOJE: pontos de 5 em 5 min, eixo 05h–18h, linha pontilhada = fechamento anterior, máx/mín,
    arrastar o dedo mostra preço/hora no topo. Dados em `intradia.json` (~5 KB), baixado SÓ com
    HOJE aberto e no máximo a cada 10 min (pedido do usuário: pouco tráfego); o último ponto vem
    da cotação que o app já busca (`pontosDia`). Fim de semana mostra o último pregão.
    Conilon do dia = mesma conta do app sobre a base do dia (fechamento de ontem ou preço combinado).
    Depois do fechamento de Londres/NY o gráfico mostra o último negócio (ex. 3.376) e o card o ajuste
    oficial (3.375). Em 06/10 o usuário PEDIU para igualar: depois do fechamento da bolsa (`fechouBolsa`:
    Londres 17h30 de Londres, NY 13h30 de NY, com horário de verão UK/EUA) o gráfico de Londres/NY ganha um
    último ponto com o ajuste oficial (= quadrado) e o topo diz "fechamento".
- **Indicar para um amigo (28/10/2026):** ícone verde do WhatsApp no topo (ao lado do tema) e botão largo
  "INDICAR PARA UM AMIGO" embaixo do gráfico → `https://wa.me/?text=` + `MSG_INDICAR` (mensagem com 5 benefícios,
  link do instalar.html e "No iPhone, abra pelo Safari"). No APK, links de fora abrem no app (openExternal).
  Umami: evento `indicar` (local: topo/painel). Título do topo diminuiu para 6vw para caber os 2 botões. Usuário confirmou
  no celular (28/10) que abre o WhatsApp com a mensagem.
- **Cálculo (aba CÁLCULO, 29/10/2026):** calda de defensivos no Conilon. Espaçamento (linhas × plantas, m →
  plantas/ha), equipamento (costal 20 L, tanques 400/1.000/2.000 L), via folha (calda L/ha, padrão 400) ou via solo
  (drench 30/50 mL ou "Outro", 1 ou 2 drench por planta). Produtos livres (nome + dose POR HECTARE em L/mL/kg/g,
  vários). Folha: área/tanque = volume ÷ calda/ha. Solo: calda/planta = nº × volume; plantas/tanque = volume ÷
  calda/planta; área = plantas ÷ plantas/ha. Produto/tanque = dose/ha × área. Botão "ENVIAR PELO WHATSAPP"
  (wa.me com a recomendação + aviso "siga a bula e o agrônomo"). Tudo salvo no aparelho (chave `calculo`).
  Dois botões: "ENVIAR COMPLETA" (detalhada, termina com o link do app) e "ENVIAR RESUMIDA" (`textoCurto`, para
  leigo, SEM nome do app: "PRODUTO - DOSE POR EQUIPAMENTO - EQUIPAMENTO" por linha; via solo começa com
  "Drench: N × V mL por planta"). Pedido 29/10/2026.
  Umami: `calculo-whatsapp` (modo, equipamento, produtos, mensagem completa/resumida). Dose por ha nos dois modos.
  Equipamento "Outro (digitar os litros)" (`equipOutro`; até 30 L = "bomba", acima = "tanque"). Campo QUADRA/TALHÃO
  (opcional) na 1ª linha das duas mensagens. Resumida com negrito; ícone SÓ na quadra e sem linha em branco: 📍 *Quadra*,
  *Via folha* ou *Via solo:* N drench de V mL por planta, depois *Produto* - *dose* - Equipamento (ajuste de 29/10) ("5" → "Quadra: 5"; "Quadra 3"/"Talhão…" fica como digitado). 29/10/2026.
- **Consulta de produtos registrados para café (29/10/2026):** botão "🔎 CONSULTAR PRODUTOS REGISTRADOS PARA CAFÉ" na aba
  CÁLCULO abre `#agroModal`: busca sem acento por praga/doença/planta daninha/produto/ingrediente ativo + filtro por tipo;
  até 50 resultados; "+ USAR NO CÁLCULO" põe o nome no cálculo; "VER BULA" = pesquisa no Google. Dados:
  `assets/agrofit-cafe.json` (versionado; ~310 KB; 1.272 produtos em 29/10) gerado por `scripts/agrofit_cafe.py` a partir do
  CSV aberto do Agrofit/MAPA (CC-BY, ~400 MB lido em fluxo; só CULTURA = "Café" e SITUACAO TRUE; "Todas as culturas" fica
  de fora). O CSV NÃO tem dose nem calda (estão na bula; API da Embrapa AgroAPI talvez tenha — exigiria conta do usuário).
  `.github/workflows/agrofit.yml`: toda segunda 06:17, regrava só se mudou, faz commit e chama o pages.yml.
  Umami: `agrofit` (acao: abrir/usar/bula). Crédito "Fonte: Agrofit/MAPA" no fim da janela (exigido pela licença).
- **Chuva:** previsão de 10 dias (Open-Meteo). Padrão Itamaraju-BA; usuário escolhe qualquer
  cidade do Brasil (busca no geocoding do Open-Meteo), salvo no aparelho. O ícone da aba mostra
  o total de mm dos 10 dias.
- **Notícias:** `noticias.json` (listas `regional` e `mercado`, juntas na tela) com filtro por tema. Só título/fonte/link (abre a matéria original).
  Desde 06/10: UMA lista só (regionais com borda laranja, sem seção separada), ordem impacto → data.
  Temas: Todas · ⚡ Impacto · Sul da BA e ES (filtro `regional`) · Dólar · Mercado · Clima · Safra · Consumo. Logística, Geopolítica e
  Concorrentes RETIRADOS a pedido (exceto Vietnã/robusta, mantido em Safra). Dólar entra sem "café" no título (`BUSCAS_DOLAR`, máx. 8). Selo IMPACTO
  (`IMPACTO` em noticias.py: dispara/despenca/desaba/geada/quebra de safra/forte alta…) vai para o topo.
- **Temas azul (PADRÃO) / rosa:** botão no canto superior direito (ícone de mulher de chapéu com óculos, SVG
  inline); cada toque troca azul ↔ rosa (salvo no aparelho, chave `tema`). Desde 28/10/2026 o azul é o padrão
  e o PRETO SAIU (pedido do usuário): quem tinha "padrao" salvo vê o azul. `:root` ainda tem as cores pretas,
  mas a página sempre põe `data-tema` (azul/rosa); manifest e theme-color = #07111f.
  Cores em variáveis CSS; `html[data-tema="rosa"]` e `html[data-tema="azul"]` (azul-marinho, destaque
  azul-céu #38a3ff, pedido 28/10/2026). Os 3 quadrados Dólar/Londres/N.York seguem vermelho/verde em todos.
- Sem faixa "Indicadores Técnicos do Mercado Físico", sem botão "?" nem janela de ajuda (inclusive o
  "Testar alerta") — retirados a pedido do usuário em 28/09/2026. O aviso de privacidade (Umami) fica
  numa linha do rodapé do Painel. `Native.testarAlerta` continua no APK, só não é usado.
- Rodapés NÃO mostram de onde vêm as cotações (pedido do usuário). Única exceção, pequena no
  Painel: "Previsão do tempo: Open-Meteo" (crédito exigido pela licença; Cepea retirado em 24/10).
- Preço do Conilon mostrado arredondado de 10 em 10 centavos (`arred10`: card, variação e gráfico).
- Dólar (`dolarVigente`): ao vivo só das 9h até o fechamento do pregão de câmbio (~18h Brasília);
  fora disso e no fim de semana vale o último fechamento, com a data desse pregão no card.
  Enquanto o dólar de HOJE não saiu (antes das 9h, fim de semana) o card fica cinza e sem
  percentual "(–)"; à noite mantém a cor e a variação do dia (pedido do usuário 29/09).
  A variação % do dólar é calculada com o valor de 2 casas (5,23 × 5,23 = 0,00%, card cinza), pedido 02/10.
  (O `AlertaService.java` ainda usa o dólar ao vivo e o preço sem arredondar — diferença mínima.)
- Card do Conilon NÃO deve mostrar ajuste, arroba nem faixa de indicadores (pedido do usuário).
- Pouco texto na tela (pedido 28/10/2026): RETIRADOS "R$ por saca de 60 kg", "Variação nos últimos 7 pregões" e
  "De 5 em 5 minutos…" (o `#chSub` só aparece no fim de semana: "Último pregão: …").
- Card do Conilon tem a linha "Referência diária: CCCV (Vitória-ES)" (`.hero-ref`, cor de destaque), pedido
  28/10/2026 — única menção de fonte de preço na tela; NÃO citar os + R$ 10,00 (escolha do usuário).
- Feriados nacionais (`feriado()` no index.html; fixos + Carnaval seg/ter, Sexta Santa, Corpus Christi
  pela Páscoa): selo roxo FERIADO no lugar de AO VIVO (estimativa continua). Pedido do usuário em 01/10.
- Variação do dia >= 3% (`VARIACAO_FORTE` no index.html, não é o `alertaVariacaoPct`): card brilha,
  selo FORTE ALTA/BAIXA, fogos + 💵💰 subindo (alta) ou 💸 voando (baixa) em `#efeito`. O preço NÃO
  aumenta de tamanho (usuário preferiu os fogos). Respeita "reduzir animações".
  Não há preço físico do Arábica (só cotação de NY).

## Dados e automações (GitHub Actions)
- Cotações ao vivo: `scanner.tradingview.com` (não oficial, grátis, ~10 min de atraso; pode parar).
- `scripts/historico.py`: fechamentos diários (canal de gráficos do TradingView) e o preço do Conilon do
  app → `historico.json` (gerado, não versionado).
  **PREÇO DO CONILON (pedido do usuário em 24/10/2026, vale desde 26/10/2026; o Cepea NÃO é mais usado):**
  - Cada dia começa no FECHAMENTO DO APP no dia anterior (`baseConilon` = `fechamentoApp` de ontem).
    Preço = (Londres + diferencial) × 0,06 × dólar; diferencial = base / (0,06 × dólar de ontem) − Londres de
    ontem. Na prática o diferencial fica constante e o preço só segue Londres e o dólar.
  - **Desde 27/10/2026 (`config.json` `cccvDesde`, pedido em 26/10): o dia começa no CCCV Tipo 7/8 EXATO do
    dia anterior** (Centro do Comércio de Café de Vitória; `cccv_conilon()` lê
    noticiasagricolas.com.br/cotacoes/cafe/cafe-conillon-disponivel-vitoria-es, ~10 últimos pregões; fica em
    `dias[].cccv`). Prioridade da base: `inicios` (preço combinado) → CCCV do dia anterior → fechamento do app.
    Se o CCCV ainda não saiu, o dia começa no fechamento do app e é REFEITO quando ele sair (escolha do usuário).
    **Desde 27/10/2026 (pedido do usuário em 27/10): base = CCCV + R$ 10,00** (`config.json` `cccvAcrescimo`: 10.0;
    vale para hoje e em diante; 27/10 começou em 905 + 10 = 915,00). Preço combinado em `inicios` continua na frente.
    `calibracao.cepeaConilon`/`diferencialConilon` = base do próximo dia (para o alerta do APK).
    Comparação 19–23/10 (app × CCCV): app fechou +27,70 / +15,20 / +12,90 / +34,40 / −3,90 acima do CCCV.
  - Recalibração: de vez em quando o usuário passa um preço para começar um dia → `config.json`
    `inicios` [{data, preco}]. O 1º é 26/10/2026: 925,00 (pedido do usuário na manhã de 26/10; antes 894,10 = fechamento do app em 23/10).
  - Depois que o câmbio fecha (17h NY → 18h30 no horário de verão dos EUA, 19h30 fora; `minutoFechado`
    no app = `minuto_fechado` no historico.py) o card mostra FECHADO dd/mm com `fechamentoApp`.
    Madrugada/fim de semana/Londres fechada: mostra o último FECHADO.
  - Dias passados ficam como foram publicados (`marcar_fechamentos` copia `baseConilon`/`fechamentoApp`
    do historico.json no ar): troca de contrato de Londres não muda preços antigos. Dias até 23/10
    (época do Cepea) só repetem o publicado. Sem nenhum fechamento → historico.py falha (mantém o publicado).
  - Mesma regra no app (`baseDe` no index.html: `baseConilon` do dia → `inicios` → fechamento de ontem)
    e no gráfico HOJE (`gerar_intradia`). `calibracao` = último dia fechado + `inicios`.
  - Variação mostrada: movimento do dia = preço − base ("no dia"). FORTE ALTA/BAIXA usa essa variação.
    Gráfico SEMANA = fechamentos do app; HOJE: linha pontilhada = fechamento de ontem (`anterior.conilon`).
  - `AlertaService.java` (APK) lê os nomes antigos `calibracao.cepeaConilon`/`ajusteConilonCepea`: o
    historico.py ainda publica esses dois (= último fechamento, 0) para o alerta continuar funcionando
    durante o dia sem APK novo. Depois do fechamento o alerta não dispara (não acha `cepeaConilon` nos dias).
  - Histórico: 03/10–23/10/2026 = opção B (base = último Cepea anterior; −10 desde 06/10, −20 desde 23/10;
    reserva de 920,00 em 23/10 se faltasse o Cepea de 22/10).
- Dias do histórico (`montar_dias`): toda data em que Londres OU NY negociou. Bolsa fechada (feriado
  UK/EUA, ex. 26/11 Ação de Graças, 28/12 Boxing Day) repete o último fechamento e vai em "fechadas".
- Contratos trocam sozinhos (dia 15 do mês anterior ao vencimento; Londres 2ª posição, NY 1ª),
  sem salto no preço (ajuste pela diferença entre contratos).
- Rede: `pedir()` no index.html tenta Native → fetch do WebView → Native de novo após 3 s (no 5G o
  celular às vezes dá "Unable to resolve host"). Faixa vermelha só após 3 falhas seguidas (~3 min).
  Se ainda falhar, `scan()` usa a RESERVA `cotacoes.json` (gerada por `historico.py`/`cotacoes_scanner`
  a cada rodada do pages.yml, ~15 min; 4 vencimentos de cada bolsa + dólar) e mostra "atualizado às HH:MM".
  Solução mista escolhida pelo usuário (01/10): direto primeiro, GitHub só como reserva.
  A reserva NÃO é usada se for mais velha que a última busca direta (`ultimoDireto`), e o dólar nunca
  volta para um pregão mais antigo (`fxVisto`) — bug de 05/10: no 5G o dólar pulava de 4,99 para o 5,22 de sexta.
- **Segunda fonte do dólar (AwesomeAPI, desde 26/10/2026):** nesse dia o TradingView travou o FX_IDC:USDBRL
  em 4,97 (fechamento de sexta) com o dólar real a R$ 5,60 (+12%, eleição). App (`dolarAwesome` no index.html)
  e historico.py (`dolar_awesome`) buscam `economia.awesomeapi.com.br/json/last/USD-BRL`; se discordar do
  TradingView mais de 0,5% (ou o TradingView falhar), valia a AwesomeAPI (no historico.py só para hoje,
  depois das 9h). O dia fica `usdFonte: "awesome"` no historico.json e, depois de passado, mantém o dólar
  publicado. Gráfico HOJE: pontos do dólar da AwesomeAPI acumulados a cada rodada (`intradia.usdFonte`).
  **CORRIGIDO no mesmo dia:** a notícia dos R$ 5,60 (+12%) não bateu com nenhuma fonte (TradingView 4,9652
  ao vivo, Yahoo 4,9993 atrasado, AwesomeAPI 429 no GitHub). O TradingView NÃO tinha travado. Agora as
  fontes extras só entram se o TradingView FALHAR (sem dólar de hoje), nunca por discordância.
  Se a AwesomeAPI falhar, tenta o Yahoo Finanças (BRL=X, `dolar_yahoo`/`dolarYahoo`; no navegador pode dar
  CORS, no Android vai pela ponte). O app espera no máximo 8 s pelas fontes extras. Cada rodada do pages.yml
  deixa uma anotação "Dólar" com o que cada fonte mandou (API: check-runs/{id}/annotations).
- `scripts/noticias.py`: Google Notícias RSS (últimos 7 dias), filtra fora do assunto e repetidas.
- `historico.py` também gera `intradia.json` (barras de 5 min do TradingView; `gerar_intradia`).
- **cron-job.org (desde 22/10/2026):** o agendamento do GitHub passou a pular a maioria das rodadas (22/10:
  6 rodadas em vez de ~70; gráfico HOJE 4 h parado). O usuário cria no cron-job.org (conta dele) uma tarefa
  POST `https://api.github.com/repos/davidcaliman-maker/painel-cafe/actions/workflows/pages.yml/dispatches`,
  headers Accept `application/vnd.github+json`, Authorization `Bearer <token>`, X-GitHub-Api-Version
  `2022-11-28`; corpo `{"ref":"main","inputs":{"agendado":"sim"}}`; a cada 10 min, 5h–21h, seg–sex (fuso
  America/Sao_Paulo); resposta 204. Token = fine-grained PAT só do repo painel-cafe, permissão Actions
  read/write, criado SEM vencimento (22/10/2026; job cron-job.org nº 8703655, teste 204 OK). Se um dia
  for apagado/regenerado, as rodadas voltam a depender do GitHub.
  A API avisou: versão `2022-11-28` obsoleta desde 10/03/2026 e DESLIGADA em 10/03/2028 → antes disso trocar
  o header X-GitHub-Api-Version no cron-job.org pela versão atual (docs.github.com/rest/about-the-rest-api/api-versions).
  `agendado=sim` faz a rodada se comportar como agendada (só republica se mudou). Agendas do GitHub ficam
  como reserva. Nunca pedir/ver o token: o usuário cola direto no cron-job.org.
- `pages.yml` roda: dias úteis a cada 15 min das 05h às 22h (Brasília);
  sáb/dom 09h, 15h, 20h. Agendadas só republicam se histórico ou notícias mudaram. Keepalive incluso.
- **Cepea removido em 24/10/2026** (pedido do usuário): apagados `conferencia.yml` ("Cepea do dia", e-mail
  das 22h30), `scripts/cepea_do_dia.py`, `scripts/acerto.py` e o passo do acerto no pages.yml (que voltou a
  `contents: read`); `cepea_conilon`, `cepea_reserva`, `dia_da_rotina` e os `ajustes` saíram do historico.py.
  `dados/acerto.csv` ficou como registro (07/10–23/10). Não recriar sem o usuário pedir.
- **`dados/fechamentos.csv`** (pedido 24/10/2026): registro PERMANENTE do Conilon do app, uma linha por
  pregão (data, abertura, fechamento, variacao, londres, dolar, nova_york). `scripts/fechamentos.py` roda
  em toda rodada do pages.yml (de novo `contents: write`) e o robô faz commit → `git pull` antes de mexer.
  Começa em 12/10/2026 (o que ainda estava no historico.json); dias antigos não foram reconstruídos.
- `app/src/main/assets/config.json`: `inicios` (preços combinados), contratos/posições, `alertaVariacaoPct` (2.0).

## Monitoramento local (fora do repositório)
- `monitoramento/` é ignorada pelo git (NÃO vai para o repo público). Leia
  `monitoramento/captura-app-painel-do-cafe/LEIA-ME.md` antes de mexer: captura diária de preços de
  referência no PC do usuário (emulador Android + OCR), tarefa do Agendador do Windows (seg–sex, a partir
  das 17h, de 30 em 30 min, ao sair da suspensão e ao entrar no Windows) e planilha em
  `Documentos\Painel do Café - preços.csv`. Rodar na nuvem foi tentado e descartado em 24/10/2026.
- Esses números são só referência do usuário para recalibrar (`inicios`); NÃO exibir no app público.

## Segurança
- Repo público: nada secreto nele (sem senhas, tokens nem a chave do APK). `config.json`, IDs do
  Umami e scripts são públicos por natureza.
- Commits usam o e-mail anônimo do GitHub (configurado no repo local); os 35 primeiros commits têm
  o Gmail do usuário no histórico.
- Ação de terceiros (`liskin/gh-workflow-keepalive`) fixada por SHA; as demais são oficiais do GitHub.
- Maior risco: invasão da conta GitHub (controla o app de todos). Recomendar 2FA.

## Trabalho em mais de um lugar
- O usuário também edita pelo Claude Code na web (branches `claude/...` + pull request na `main`).
  Antes de mexer, rode `git pull` para pegar essas mudanças (o robô também faz commit de `dados/fechamentos.csv`).
- Orientação dada: abrir sessão nova no Claude Code escolhendo a pasta `D:\PROJETOS_CLAUDE\painel-cafe`
  (este arquivo é lido sozinho). A única coisa fora do GitHub é `~/.android/debug.keystore`.

## Regras combinadas com o usuário
- **Nunca altere `config.json` (preço/início do dia) sem aprovação explícita.**
- Conilon: ver "PREÇO DO CONILON" (desde 26/10/2026: começa no fechamento do app do dia anterior;
  Cepea não é mais usado).
- Confirmar com o usuário antes de publicar/instalar coisas que custem ou que baixem ferramentas grandes
  (ele recusou baixar Gradle/SDK novo; APK é feito sem Gradle).

## APK Android (só para mudanças nativas: ícone, nome, Java, alertas) — versão atual 3.1 (code 9)
- `bash build-apk.sh` → `build/PainelCafe.apk` (sem Gradle; Android SDK build-tools 30.0.0 +
  platform android-30 + JDK 17; targetSdk 30).
- Assinado com `~/.android/debug.keystore`. **Esse arquivo precisa ser o mesmo em qualquer
  computador**, senão o APK novo não instala por cima. Não fica no GitHub (repo público);
  usuário foi orientado a guardar cópia em pen drive/Drive.
- Publicar: aumentar `--version-code/--version-name` no `build-apk.sh`, copiar para
  `build/PainelAgro.apk` e `gh release create vX.Y build/PainelAgro.apk build/PainelCafe.apk`.
  Depois rode `gh workflow run pages.yml`: o deploy copia o APK da última release para o site
  (`/painel-cafe/PainelAgro.apk`), que é o link do botão "Baixar para Android" em `instalar.html`
  (link direto, sem redirecionamentos — o link do GitHub Releases falhava em alguns celulares).
- `MainActivity.java`: WebView que carrega o site (fallback offline para a cópia nos assets),
  ponte `Native` (post/get HTTP sem CORS, load/save, openUrl, testarAlerta).
- `AlertaService.java`: JobScheduler a cada ~15 min (5h–22h), app fechado; notifica FORTE ALTA /
  FORTE BAIXA quando a variação do dia passa de `alertaVariacaoPct` (repete a cada novo degrau).
  Usuário confirmou que o alerta de teste chegou (26/09/2026).
- Emulador não roda neste PC (virtualização desligada na BIOS) → testes nativos só no celular do usuário.

## iPhone
- Funciona pelo Safari → Compartilhar → Adicionar à Tela de Início (PWA, abre em tela cheia).
- `PainelAgro.mobileconfig` (Web Clip) cria o ícone via perfil. GitHub Pages serve como
  octet-stream; o botão de `instalar.html` refaz o arquivo como `application/x-apple-aspen-config`.
  **Ainda não testado num iPhone real** — pedir ao usuário o resultado antes de divulgar para iPhone.
- iPhone não recebe alertas (precisaria serviço de push, ex. OneSignal, conta do usuário).

## Divulgação
- Divulgar o LINK `instalar.html` (detecta iPhone/Android/computador), não o arquivo.
- `divulgacao/cartaz-pregao-do-cafe.png` (A5 1240×1748 com QR; refeito em 29/10/2026 com nome/ícone novos, fundo azul-
  marinho, 6 itens incluindo o cálculo de calda; o antigo cartaz-painel-do-agro.png foi apagado) e `divulgacao/qrcode-instalar.png`.
- Mensagem de WhatsApp sugerida: título, 5 benefícios, link, "No iPhone, abra pelo Safari".
- **Não contar o dono nas estatísticas (29/10/2026):** 5 toques seguidos no logo (grão do topo) liga/desliga
  `localStorage["umami.disabled"]` (o script do Umami não envia nada com essa chave) e mostra um aviso. Feito no celular
  do usuário por ele mesmo (confirmou o aviso em 29/10); no navegador do Claude (painel do Claude Code) já foi ligado no site oficial. A cópia local
  (localhost) já não conta (data-domains). Se o usuário limpar os dados do app, precisa repetir.
- Umami: eventos `abertura` (plataforma, tema, cidade_chuva), `aba`, `tema`, `cidade-chuva`,
  `noticia`, `atualizar`, `instalar` (tipo).

## Custos e riscos conhecidos (explicados ao usuário)
- GitHub: grátis enquanto o repo for público. Umami: grátis até 100 mil eventos/mês.
- Open-Meteo: plano grátis é para uso não comercial → risco; alternativa grátis comercial: MET Norway.
- TradingView: não oficial, pode bloquear. Dólar poderia ir para fonte oficial grátis (BCB/AwesomeAPI).
- Cepea: consulta livre; republicação comercial pode exigir autorização (sugerido e-mail ao Cepea).
- Play Store: US$ 25 uma vez + teste fechado 14 dias/12 testadores; exigiria targetSdk atual, AAB
  (Gradle), chave própria, política de privacidade. Usuário decidiu "por enquanto não".
- App Store: US$ 99/ano, precisa Mac (ou Mac na nuvem via GitHub), risco de recusa (4.2 "só site").
- Google anunciou verificação obrigatória de desenvolvedores Android no Brasil a partir de set/2026
  (pode afetar APK por link) — conferir situação atual.

## Análises já feitas (para não refazer do zero)
- Fechamento do app = Cepea arredondado (diferença máx. 4 centavos). As diferenças estão na
  ESTIMATIVA AO VIVO: em 14 pregões (14/09–01/10) erro médio ~R$ 10/saca (1,1%), sem vício para um
  lado (média +R$ 0,5); maior erro R$ 24 (23/09). O físico anda menos que Londres × dólar no dia.
- Simulações nos mesmos 14 dias (erro médio / maior erro):
  movimento inteiro (atual) 10,04 / 24,14 · regra do usuário "abrir pela média (fechamento do app +
  Cepea)/2" 10,24 / 19,95 (empatou, não adotar) · 75% do movimento 7,49 · **50% do movimento 5,74 /
  14,81** · 35% 5,85. Fórmula NÃO foi mudada: esperar `dados/acerto.csv` ter 3–4 semanas (fim de
  out/2026), refazer a análise e só então propor (precisa aprovação do usuário).
- Refeito em 03–05/10 com 15/09–02/10 (fechamento do app = opção B; base = Cepea anterior, 1º dia
  base 14/09 = 992,35). Fórmula: preço = base + fator × (estimativa cheia − base). Erro médio (R$/saca):
  fator 0% 9,90 · 20% 7,91 · 30% 7,05 · 40% 6,67 · **50% 6,46** · 60% 6,75 · **70% 7,46** · 80% 8,32 ·
  90% 9,18 · 100% (atual) 10,11 (maior erro 24,10 em 23/09). Faixa 40–60% quase igual; 70% pedido pelo
  usuário para comparar (gráfico mostrado). App fechou acima do Cepea 5/14 dias, abaixo 9/14, média −0,50.
  Outras ideias testadas e REJEITADAS: abrir pela média (app+Cepea)/2 (10,24); abrir R$ 10 abaixo do
  Cepea (~13,6, pior — desconto fixo corrige um lado e piora o outro).
  Se aplicar o fator: mudar `fisicoConilon`/estimativa no index.html, `gerar_intradia` e
  `marcar_fechamentos` no historico.py (mesmo fator nos três); considerar baixar `VARIACAO_FORTE` (3%)
  e o `alertaVariacaoPct`; `AlertaService.java` só muda com APK novo.
- 05/10/2026: dólar abriu −4,4% (5,22 → 4,99; confirmado no Yahoo). Bom dia de teste para o acerto.
- Atraso das bolsas: ICE (Londres/NY) só tem tempo real pago e com licença de redistribuição (cara);
  grátis = 10–15 min. Dólar (FX_IDC) já vem com ~1–2 min. Explicado ao usuário (01/10).
- Dólar: app mostra 2 casas arredondando (5,2271 → 5,23); Google às vezes mostra 5,22. Explicado.

## Perguntas já respondidas ao usuário
- Feriado nacional (ex. 12/10): o app NÃO para — Londres/NY abrem, selo FERIADO, estimativa pela bolsa;
  o dia tem FECHAMENTO normal e o dia seguinte começa nele.
- Londres fecha nos feriados bancários do Reino Unido em dia de semana: 25 e 28/12/2026; em 2027:
  01/01, 26/03 (Sexta Santa), 29/03 (Páscoa UK), 03/05, 31/05, 30/08, 27 e 28/12. 24/12 e 31/12 fecham
  mais cedo. NY fecha nos feriados dos EUA (ex. 26/11/2026 Ação de Graças). Tratado em `montar_dias`.
- Recalibrar: o usuário passa "amanhã começa em R$ X" → acrescentar {"data": dia, "preco": X} em
  `inicios` no config.json (aprovado por ele ao pedir). Vale também para o dia de hoje (o gráfico e o
  card recalculam na próxima rodada).

- Gráfico HOJE × card FECHADO (explicado em 29/10/2026): o gráfico termina no último NEGÓCIO de Londres (ex. 3.160 →
  R$ 913,70) e o FECHADO usa o AJUSTE oficial (3.167 → R$ 916,00). Opções oferecidas: A) fechamento = último ponto do
  gráfico; B) gráfico do Conilon ganhar o ponto final com o ajuste. Usuário decidiu DEIXAR COMO ESTÁ.
- 29/10/2026: app abriu 916 (CCCV 28/10 906 + 10), fechou 916,00 (Londres −16 e dólar +0,03 se anularam) e o CCCV de
  29/10 também deu 916 — coincidência, explicada ao usuário.

## Pendências / ideias oferecidas e ainda não feitas
- Nome do card "CONILON 7/8" — usuário não decidiu se renomeia.
- A análise de fatores (50%/70%) prevista para fim de out/2026 perdeu o sentido: sem Cepea não há com o
  que comparar. `dados/acerto.csv` (07/10–23/10) fica no repo como registro.
- Bloqueio só para convidados — opções explicadas (28/09): 1) código único no app (simples, burlável;
  "Jeito A" = todos, inclusive quem já usa, digitam uma vez — recomendado), 2) código por pessoa com
  lista/cancelamento (Cloudflare Worker), 3) Cloudflare Access por e-mail (grátis até 50 pessoas; muda
  hospedagem). Usuário não decidiu nem escolheu o código.
- Cloudflare Worker como intermediário das cotações (ao vivo, esconde a fonte, menos risco de
  bloqueio; precisa conta do usuário). Recomendado só se a reserva do GitHub não bastar no 5G ou junto
  com o bloqueio por convite (opção 2).
- (Obsoleto desde 24/10: o app não espera mais o Cepea à noite.)
- Dólar com 3–4 casas no card — oferecido, sem resposta. Aviso "10 min atraso" nos cards de Londres/NY
  — oferecido, sem resposta.
- Trocas gratuitas: chuva → MET Norway; dólar → fonte oficial — oferecido, não feito.
- Alertas no iPhone (OneSignal) — oferecido, não feito.
- Tarefas agendadas locais `monitor-conilon-itamaraju(-tarde)` estão DESATIVADAS (substituídas pelo GitHub).
