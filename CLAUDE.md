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
  (`painel-agro-vN` → `vN+1`; hoje v30).
- Teste no navegador (larguras 375 e 412 px) antes de publicar. Para testar local: servidor
  `python -m http.server 8765 -d app/src/main/assets` (contador Umami fica desligado fora do site oficial;
  `.claude/launch.json` tem a configuração "painel" para o preview do Claude). Os JSON gerados
  (historico/intradia/cotacoes/noticias) não existem na cópia local: para simular, gere com
  `python scripts/historico.py ...` em `build/teste/` e copie para assets — e APAGUE antes do commit.
- Antes de publicar uma mudança visual, mostrar ao usuário (preview) e pedir o "pode publicar".

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
    Depois do fechamento de Londres/NY o gráfico mostra o último negócio (ex. 3.376) e o card o ajuste
    oficial (3.375): diferença de poucos pontos, explicada ao usuário, que NÃO quis igualar (29/09).
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
- Rodapés NÃO mostram de onde vêm as cotações (pedido do usuário). Única exceção, pequena no
  Painel: "Fontes: Cepea/Esalq · Open-Meteo" (crédito exigido por essas duas; não retirar).
- Preço do Conilon mostrado arredondado de 10 em 10 centavos (`arred10`: card, variação e gráfico).
  O fechamento do app (ex. 952,70) pode diferir em centavos do Cepea/cotacaodocafe (952,72) — intencional.
- Dólar (`dolarVigente`): ao vivo só das 9h até o fechamento do pregão de câmbio (~18h Brasília);
  fora disso e no fim de semana vale o último fechamento, com a data desse pregão no card.
  Enquanto o dólar de HOJE não saiu (antes das 9h, fim de semana) o card fica cinza e sem
  percentual "(–)"; à noite mantém a cor e a variação do dia (pedido do usuário 29/09).
  A variação % do dólar é calculada com o valor de 2 casas (5,23 × 5,23 = 0,00%, card cinza), pedido 02/10.
  (O `AlertaService.java` ainda usa o dólar ao vivo e o preço sem arredondar — diferença mínima.)
- Card do Conilon NÃO deve mostrar ajuste, arroba nem faixa de indicadores (pedido do usuário).
- Feriados nacionais (`feriado()` no index.html = `cepea_do_dia.py`; fixos + Carnaval seg/ter, Sexta Santa,
  Corpus Christi pela Páscoa): selo roxo FERIADO no lugar de AO VIVO (estimativa continua) e a rotina das
  22h30 não manda e-mail. Pedido do usuário em 01/10. Manter as duas listas iguais.
- Variação do dia >= 3% (`VARIACAO_FORTE` no index.html, não é o `alertaVariacaoPct`): card brilha,
  selo FORTE ALTA/BAIXA, fogos + 💵💰 subindo (alta) ou 💸 voando (baixa) em `#efeito`. O preço NÃO
  aumenta de tamanho (usuário preferiu os fogos). Respeita "reduzir animações".
  Não há preço físico do Arábica (só cotação de NY).

## Dados e automações (GitHub Actions)
- Cotações ao vivo: `scanner.tradingview.com` (não oficial, grátis, ~10 min de atraso; pode parar).
- `scripts/historico.py`: fechamentos diários (canal de gráficos do TradingView), indicador
  Cepea/Esalq do Conilon (Robusta) e a calibração → `historico.json` (gerado, não versionado).
  Preço do Conilon = Cepea + `ajusteConilonCepea` (hoje 0). Durante o pregão o app estima por
  Londres × dólar a partir do último Cepea; quando o Cepea do dia sai (~21h), vira FECHAMENTO.
- Dias do histórico (`montar_dias`): toda data em que Londres OU NY negociou OU o Cepea publicou. Bolsa
  fechada (feriado UK/EUA, ex. 26/11 Ação de Graças, 28/12 Boxing Day, 29/03/2027 Páscoa UK) repete o
  último fechamento e vai em "fechadas" → o Cepea desses dias é usado normalmente (corrigido 01/10).
- Contratos trocam sozinhos (dia 15 do mês anterior ao vencimento; Londres 2ª posição, NY 1ª),
  sem salto no preço (ajuste pela diferença entre contratos).
- Rede: `pedir()` no index.html tenta Native → fetch do WebView → Native de novo após 3 s (no 5G o
  celular às vezes dá "Unable to resolve host"). Faixa vermelha só após 3 falhas seguidas (~3 min).
  Se ainda falhar, `scan()` usa a RESERVA `cotacoes.json` (gerada por `historico.py`/`cotacoes_scanner`
  a cada rodada do pages.yml, ~15 min; 4 vencimentos de cada bolsa + dólar) e mostra "atualizado às HH:MM".
  Solução mista escolhida pelo usuário (01/10): direto primeiro, GitHub só como reserva.
- `scripts/noticias.py`: Google Notícias RSS (últimos 7 dias), filtra fora do assunto e repetidas.
- `historico.py` também gera `intradia.json` (barras de 5 min do TradingView; `gerar_intradia`).
- `pages.yml` roda: dias úteis a cada 15 min das 05h às 22h (Brasília);
  sáb/dom 09h, 15h, 20h. Agendadas só republicam se histórico ou notícias mudaram. Keepalive incluso.
- `conferencia.yml` (nome "Cepea do dia e acerto da estimativa"): dias úteis 22h30.
  1) `scripts/cepea_do_dia.py --corrigir`: se o app não tem o Cepea de hoje e o Cepea já publicou, roda o
     pages.yml de novo e reconfere; se ainda faltar (ou Cepea não publicou/fora do ar/Londres sem pregão),
     a execução FALHA → e-mail do GitHub ao usuário (pedido 01/10). Motivo no resumo da execução.
  2) `acerto.py`. Falha passageira do Cepea numa rodada do pages.yml NÃO marca erro (evita e-mail a cada 15 min).
  A comparação com o cotacaodocafe.com foi RETIRADA em 01/10 a pedido do usuário (o site só copia o
  Cepea); `conferencia.py` e `monitor.py` foram apagados. Não recriar.
- `scripts/acerto.py` (no conferencia.yml, 22h30): anota em `dados/acerto.csv` a estimativa AO VIVO das
  10h/13h/16h/fim × Cepea do dia (+ base anterior, para testar outras fórmulas). Pedido do usuário em 01/10:
  juntar 3–4 semanas e então avaliar "amortecer" o movimento de Londres/dólar (físico anda ~metade).
  O robô do GitHub faz commit desse arquivo → sempre `git pull` antes de mexer.
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
  Antes de mexer, rode `git pull` para pegar essas mudanças (o robô do GitHub também faz commits
  em `dados/acerto.csv` toda noite).
- Orientação dada: abrir sessão nova no Claude Code escolhendo a pasta `D:\PROJETOS_CLAUDE\painel-cafe`
  (este arquivo é lido sozinho). A única coisa fora do GitHub é `~/.android/debug.keystore`.

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

## Análises já feitas (para não refazer do zero)
- Fechamento do app = Cepea arredondado (diferença máx. 4 centavos). As diferenças estão na
  ESTIMATIVA AO VIVO: em 14 pregões (14/09–01/10) erro médio ~R$ 10/saca (1,1%), sem vício para um
  lado (média +R$ 0,5); maior erro R$ 24 (23/09). O físico anda menos que Londres × dólar no dia.
- Simulações nos mesmos 14 dias (erro médio / maior erro):
  movimento inteiro (atual) 10,04 / 24,14 · regra do usuário "abrir pela média (fechamento do app +
  Cepea)/2" 10,24 / 19,95 (empatou, não adotar) · 75% do movimento 7,49 · **50% do movimento 5,74 /
  14,81** · 35% 5,85. Fórmula NÃO foi mudada: esperar `dados/acerto.csv` ter 3–4 semanas (fim de
  out/2026), refazer a análise e só então propor (precisa aprovação do usuário).
- Atraso das bolsas: ICE (Londres/NY) só tem tempo real pago e com licença de redistribuição (cara);
  grátis = 10–15 min. Dólar (FX_IDC) já vem com ~1–2 min. Explicado ao usuário (01/10).
- Dólar: app mostra 2 casas arredondando (5,2271 → 5,23); Google às vezes mostra 5,22. Explicado.

## Perguntas já respondidas ao usuário
- Feriado nacional (ex. 12/10): o app NÃO para — Londres/NY abrem, selo FERIADO, estimativa pela bolsa a
  partir do último Cepea; sem FECHAMENTO no dia; volta ao normal no dia seguinte.
- Londres fecha nos feriados bancários do Reino Unido em dia de semana: 25 e 28/12/2026; em 2027:
  01/01, 26/03 (Sexta Santa), 29/03 (Páscoa UK), 03/05, 31/05, 30/08, 27 e 28/12. 24/12 e 31/12 fecham
  mais cedo. NY fecha nos feriados dos EUA (ex. 26/11/2026 Ação de Graças). Tratado em `montar_dias`.
- Se o Cepea da noite não for buscado: o dia seguinte começa do ÚLTIMO Cepea que o app tem (a estimativa
  aplica o movimento de Londres/dólar desde então; card mostra "vs dd/mm" daquele Cepea). Corrige sozinho:
  22h30 manda publicar de novo; rodadas de 15 em 15 min a partir das 05h pegam o dia que faltou (a página
  do Cepea lista os últimos dias). Se continuar faltando, e-mail das 22h30 diz com qual preço o dia começa.

## Pendências / ideias oferecidas e ainda não feitas
- Nome do card "CONILON 7/8" × dado do Cepea (Robusta tipo 6 peneira 13): renomear para
  "Conilon · Indicador Cepea" ou usar o Tipo 7/8 do CCCV (Notícias Agrícolas) — usuário não decidiu.
- **~22–29/10/2026: analisar `dados/acerto.csv`** (o usuário vai pedir "analisa o acerto da estimativa
  do Conilon"): comparar fórmula atual × amortecida (50% etc.) por horário (10h/13h/16h/fim).
- Bloqueio só para convidados — opções explicadas (28/09): 1) código único no app (simples, burlável;
  "Jeito A" = todos, inclusive quem já usa, digitam uma vez — recomendado), 2) código por pessoa com
  lista/cancelamento (Cloudflare Worker), 3) Cloudflare Access por e-mail (grátis até 50 pessoas; muda
  hospedagem). Usuário não decidiu nem escolheu o código.
- Cloudflare Worker como intermediário das cotações (ao vivo, esconde a fonte, menos risco de
  bloqueio; precisa conta do usuário). Recomendado só se a reserva do GitHub não bastar no 5G ou junto
  com o bloqueio por convite (opção 2).
- App conferir o historico.json a cada 5 min das 17h às 22h (troca para FECHAMENTO logo que o Cepea
  sai; hoje confere a cada 30 min) — oferecido, sem resposta.
- Dólar com 3–4 casas no card — oferecido, sem resposta. Aviso "10 min atraso" nos cards de Londres/NY
  — oferecido, sem resposta.
- Trocas gratuitas: chuva → MET Norway; dólar → fonte oficial — oferecido, não feito.
- Alertas no iPhone (OneSignal) — oferecido, não feito.
- Ícone da tela inicial ainda é "A + grão" (o logo dentro do app é só o grão).
- Tarefas agendadas locais `monitor-conilon-itamaraju(-tarde)` estão DESATIVADAS (substituídas pelo GitHub).
