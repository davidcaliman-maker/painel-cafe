# Painel do Agro

Cotações do café (Conilon 7/8 e Arábica Rio calculados a partir de Londres, Nova York e dólar)
e previsão de chuva para Itamaraju-BA nos próximos 10 dias.

- **Android:** `bash build-apk.sh` gera `build/PainelCafe.apk` (usa só o Android SDK local).
- **iPhone / navegador:** a mesma interface (`app/src/main/assets`) é publicada no GitHub Pages
  a cada push na `main`. No iPhone: abrir no Safari → Compartilhar → Adicionar à Tela de Início.

## Como mudar o preço físico (só o corretor)

Edite `app/src/main/assets/config.json` no GitHub (lápis ✏️ → **Commit changes**).
Em 1–2 minutos todos os celulares passam a usar os novos valores.

| Campo | O que é | Exemplo |
|---|---|---|
| `diferencialConilon` | Deságio do Conilon 7/8 sobre Londres, em US$/t | `-278.95` |
| `diferencialArabica` | Deságio do Arábica Rio sobre Nova York, em ¢/lb | `-113.13` |
| `contratoLondres` / `contratoNovaYork` | `"auto"` troca sozinho; ou fixe um código, ex. `"RCF2027"` | `"auto"` |
| `posicaoLondres` / `posicaoNovaYork` | Qual vencimento usar no modo auto (1 = o mais próximo) | `2` / `1` |

Use ponto como separador decimal (`-278.95`, não `-278,95`).
Troca automática: cada vencimento é usado até o dia 15 do mês anterior.
