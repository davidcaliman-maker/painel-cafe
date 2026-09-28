# Painel do Agro

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
  (`painel-agro-vN` → `vN+1`; hoje v22).
- Teste no navegador (larguras 375 e 412 px) antes de publicar. Para testar local: servidor
  `python -m http.server 8765 -d app/src/main/assets` (contador Umami fica desligado fora do site oficial).

## Telas (barra de abas no rodapé: PAINEL · CHUVA · NOTÍCIAS; roteamento por `#chuva`/`#noticias`)
- **Painel:** card destaque do Conilon (preço grande, selo AO VIVO/FECHAMENTO dd/mm, variação do
  dia vs fechamento anterior), cards Dólar/Londres/N.York (vermelho/verde), botão ATUALIZAR,
  gráfico com seletor HOJE/SEMANA (escolha salva no aparelho; abas Conilon/Londres/N.York/Dólar).
  - SEMANA: 7 pregões (`historico.json`).
  - HOJE: pontos de 5 em 5 min, eixo 05h–18h, linha pontilhada = fechamento anterior, máx/mín,
    arrastar o dedo mostra preço/hora no topo. Dados em `intradia.json` (~5 KB), baixado SÓ com
    HOJE aberto e no máximo a cada 10 min (pedido do usuário: pouco tráfego); o último ponto vem
    da cotação que o app já busca (`pontosDia`). Fim de semana mostra o último pregão.
    Conilon do dia usa a calibração do Cepea ANTERIOR ao dia (a linha não muda quando o Cepea sai);
    depois do Cepea o topo mostra "fechamento Cepea".
- **Chuva:** previsão de 10 dias (Open-Meteo). Padrão Itamaraju-BA; usuário escolhe qualquer
  cidade do Brasil (busca no geocoding do Open-Meteo), salvo no aparelho. O ícone da aba mostra
  o total de mm dos 10 dias.
- **Notícias:** `noticias.json` — seção "Sul da Bahia e Espírito Santo" em destaque + "Mercado,
  clima e safra" com filtro por tema. Só título/fonte/link (abre a matéria original).
- **Tema rosa:** botão no canto superior direito (ícone de mulher de chapéu com óculos, SVG
  inline). Cores em variáveis CSS; `html[data-tema="rosa"]`. Verde/vermelho de alta e baixa não mudam.
- Sem faixa "Indicadores Técnicos do Mercado Físico", sem botão "?" nem janela de ajuda (inclusive o
  "Testar alerta") — retirados a pedido do usuário em 28/09/2026. O aviso de privacidade (Umami) fica
  numa linha do rodapé do Painel. `Native.testarAlerta` continua no APK, só não é usado.
- Preço do Conilon mostrado arredondado de 10 em 10 centavos (`arred10`: card, variação e gráfico).
  O fechamento do app (ex. 952,70) pode diferir em centavos do Cepea/cotacaodocafe (952,72) — intencional.
- Dólar (`dolarVigente`): ao vivo só das 9h até o fechamento do pregão de câmbio (~18h Brasília);
  fora disso e no fim de semana vale o último fechamento, com a data desse pregão no card.
  (O `AlertaService.java` ainda usa o dólar ao vivo e o preço sem arredondar — diferença mínima.)
- Card do Conilon NÃO deve mostrar ajuste, arroba nem faixa de indicadores (pedido do usuário).
  Não há preço físico do Arábica (só cotação de NY).

## Dados e automações (GitHub Actions)
- Cotações ao vivo: `scanner.tradingview.com` (não oficial, grátis, ~10 min de atraso; pode parar).
- `scripts/historico.py`: fechamentos diários (canal de gráficos do TradingView), indicador
  Cepea/Esalq do Conilon (Robusta) e a calibração → `historico.json` (gerado, não versionado).
  Preço do Conilon = Cepea + `ajusteConilonCepea` (hoje 0). Durante o pregão o app estima por
  Londres × dólar a partir do último Cepea; quando o Cepea do dia sai (~21h), vira FECHAMENTO.
- Contratos trocam sozinhos (dia 15 do mês anterior ao vencimento; Londres 2ª posição, NY 1ª),
  sem salto no preço (ajuste pela diferença entre contratos).
- `scripts/noticias.py`: Google Notícias RSS (últimos 7 dias), filtra fora do assunto e repetidas.
- `historico.py` também gera `intradia.json` (barras de 5 min do TradingView; `gerar_intradia`).
- `pages.yml` roda: dias úteis a cada 15 min das 05h às 22h (Brasília);
  sáb/dom 09h, 15h, 20h. Agendadas só republicam se histórico ou notícias mudaram. Keepalive incluso.
- `conferencia.yml` + `scripts/conferencia.py`: dias úteis 22h30 confere o Cepea do app × preço
  principal do cotacaodocafe.com; se divergir (data ou > R$ 0,50) falha e o GitHub avisa por e-mail.
- `scripts/monitor.py`: comparação manual app × cotacaodocafe.com (grava `monitoramento/conilon.csv`, local).
- cotacaodocafe.com NÃO calcula: copia o Cepea (preço principal, atualiza 1x/dia ~21h), CCCV/Cooabriel
  via Notícias Agrícolas (regionais ES; "Sul da Bahia" = mesmo valor de Vitória 7/8), PTAX (dólar).
- `app/src/main/assets/config.json`: `ajusteConilonCepea` (0), contratos/posições, `alertaVariacaoPct` (2.0).

## Segurança
- Repo público: nada secreto nele (sem senhas, tokens nem a chave do APK). `config.json`, IDs do
  Umami e scripts são públicos por natureza.
- Commits usam o e-mail anônimo do GitHub (configurado no repo local); os 35 primeiros commits têm
  o Gmail do usuário no histórico.
- Ação de terceiros (`liskin/gh-workflow-keepalive`) fixada por SHA; as demais são oficiais do GitHub.
- Maior risco: invasão da conta GitHub (controla o app de todos). Recomendar 2FA.

## Trabalho em mais de um lugar
- O usuário também edita pelo Claude Code na web (branches `claude/...` + pull request na `main`).
  Antes de mexer, rode `git pull` para pegar essas mudanças.

## Regras combinadas com o usuário
- **Nunca altere `config.json` (preço/ajuste) sem aprovação explícita.**
- Conilon = indicador Cepea (= preço principal do cotacaodocafe.com).
- Confirmar com o usuário antes de publicar/instalar coisas que custem ou que baixem ferramentas grandes
  (ele recusou baixar Gradle/SDK novo; APK é feito sem Gradle).

## APK Android (só para mudanças nativas: ícone, nome, Java, alertas) — versão atual 3.0
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
- `divulgacao/cartaz-painel-do-agro.png` (A5 com QR) e `divulgacao/qrcode-instalar.png`.
- Mensagem de WhatsApp sugerida: título, 5 benefícios, link, "No iPhone, abra pelo Safari".
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

## Pendências / ideias oferecidas e ainda não feitas
- Nome do card "CONILON 7/8" × dado do Cepea (Robusta tipo 6 peneira 13): renomear para
  "Conilon · Indicador Cepea" ou usar o Tipo 7/8 do CCCV (Notícias Agrícolas) — usuário não decidiu.
- Medir acerto da estimativa ao vivo (snapshots 10h/13h/16h × fechamento) — oferecido, não feito.
- Trocas gratuitas: chuva → MET Norway; dólar → fonte oficial — oferecido, não feito.
- Alertas no iPhone (OneSignal) — oferecido, não feito.
- Ícone da tela inicial ainda é "A + grão" (o logo dentro do app é só o grão).
- Tarefas agendadas locais `monitor-conilon-itamaraju(-tarde)` estão DESATIVADAS (substituídas pelo GitHub).
