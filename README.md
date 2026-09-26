# Painel do Agro

Cotações do café (Conilon 7/8 e Arábica Rio calculados a partir de Londres, Nova York e dólar)
e previsão de chuva para Itamaraju-BA nos próximos 10 dias.

- **Android:** `bash build-apk.sh` gera `build/PainelCafe.apk` (usa só o Android SDK local).
- **iPhone / navegador:** a mesma interface (`app/src/main/assets`) é publicada no GitHub Pages
  a cada push na `main`. No iPhone: abrir no Safari → Compartilhar → Adicionar à Tela de Início.

## Preço do Conilon 7/8 (automático)

Todo dia o GitHub lê o **Indicador do Café Robusta Cepea/Esalq** e calibra o Conilon:

    preço do dia = último Cepea + ajusteConilonCepea
    diferencial  = preço do dia / (0,06 × dólar) − Londres   (fechamentos do mesmo dia)

Durante o dia o app aplica esse diferencial a Londres e ao dólar ao vivo. O gráfico da semana
mostra, nos dias fechados, o próprio Cepea + ajuste. Na troca de vencimento o preço não salta.
No card, **AO VIVO · ESTIMATIVA PELA BOLSA** aparece durante o pregão; quando o Cepea do dia sai,
o preço vira **FECHAMENTO CEPEA** (Cepea + ajuste), que é também a abertura do dia seguinte.
Tudo é gerado por `scripts/historico.py` (GitHub Actions nos dias úteis: de hora em hora das 6h
às 15h e a cada 15 min das 16h às 22h, horário de Brasília).
Se o Cepea ficar fora do ar, o app mantém a última calibração e o GitHub avisa por e-mail.

O Arábica aparece só como cotação de Nova York (sem preço físico).

## Configuração (`app/src/main/assets/config.json`)

Só é preciso mexer se quiser mudar o ajuste. Edite no GitHub (lápis ✏️ → **Commit changes**).

| Campo | O que é | Valor |
|---|---|---|
| `ajusteConilonCepea` | Diferença do seu Conilon 7/8 para o Cepea, em R$/saca | `-11.0` |
| `contratoLondres` / `contratoNovaYork` | `"auto"` troca sozinho; ou fixe um código, ex. `"RCF2027"` | `"auto"` |
| `posicaoLondres` / `posicaoNovaYork` | Qual vencimento usar no modo auto (1 = o mais próximo) | `2` / `1` |

Use ponto como separador decimal. Cada vencimento é usado até o dia 15 do mês anterior.
