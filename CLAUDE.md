# Painel do Agro

App de cotação do café Conilon para um corretor de café do Sul da Bahia. O usuário fala
português e não é programador: responda em português, com passos simples.

## Como o app funciona
- **Toda a interface está em `app/src/main/assets/index.html`** (HTML/CSS/JS num arquivo só).
- Cada push na `main` publica essa pasta no GitHub Pages
  (https://davidcaliman-maker.github.io/painel-cafe/) via `.github/workflows/pages.yml`.
- **Android** (APK) e **iPhone** (atalho do Safari/PWA) carregam essa página do site e se
  recarregam sozinhos quando há versão nova (`versao.json`, carimbado pelo workflow).
  → Mudança de tela = editar `index.html` e dar push. Não precisa gerar APK.
- A cada mudança em `index.html`, suba o nome do cache em `app/src/main/assets/sw.js`
  (`painel-agro-vN` → `vN+1`).

## Dados
- Cotações ao vivo: `scanner.tradingview.com` (não oficial, ~10 min de atraso).
- `scripts/historico.py` (no workflow): fechamentos diários, indicador Cepea/Esalq do
  Conilon e a calibração do preço → `historico.json` (gerado, não versionado).
- `scripts/noticias.py` (no workflow): notícias do Google Notícias → `noticias.json`.
- `.github/workflows/conferencia.yml` + `scripts/conferencia.py`: todo dia útil às 22h30 confere
  o Cepea do app × preço principal do cotacaodocafe.com; se divergir, falha e o GitHub avisa por e-mail.
- Chuva: Open-Meteo (cidade escolhida pelo usuário, padrão Itamaraju-BA).
- `app/src/main/assets/config.json`: ajuste do Conilon sobre o Cepea (hoje 0), regra de
  contratos e limite dos alertas (`alertaVariacaoPct`).

## Regras combinadas com o usuário
- **Nunca altere `config.json` (preço/ajuste) sem aprovação explícita.**
- Conilon 7/8 = indicador Cepea (preço principal do cotacaodocafe.com). Não mostrar o ajuste,
  arroba nem faixa de indicadores no card do Conilon. Arábica só como cotação de NY.
- Teste no navegador (larguras 375 e 412 px) antes de publicar.

## APK Android (só para mudanças nativas: ícone, nome, Java, alertas)
- `bash build-apk.sh` → `build/PainelCafe.apk` (sem Gradle; usa Android SDK build-tools
  30.0.0 + platform android-30 + JDK 17).
- Assinado com `~/.android/debug.keystore`. **Esse arquivo precisa ser o mesmo em qualquer
  computador**, senão o APK novo não instala por cima do antigo. Ele não fica no GitHub.
- Publicar: aumentar `--version-code/--version-name` no `build-apk.sh` e criar release com
  `gh release create vX.Y build/PainelAgro.apk build/PainelCafe.apk`.
- Alertas de FORTE ALTA/BAIXA: `app/src/main/java/br/painelcafe/AlertaService.java`.
