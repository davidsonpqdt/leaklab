# LeakLab — Project Context for Claude Code

## Branding
- **Nome:** LeakLab
- **Tagline:** Poker MTTs
- **Idioma:** PT-BR (toda comunicação, UI, comentários)

## What this project is

Personal poker analysis tool for **Davidson** (nick: **Noshovepls** on iPoker network), pensado pra distribuir publicamente como alternativa simples ao Hand2Note.

**Goals:**
1. Parse iPoker XML hand histories
2. Compute HUD-style statistics (78 stats em 14 secoes)
3. Render preflop range matrices (13x13 grids) com filtros multi-select estilo H2N
4. Detect leaks comparando jogo real com ranges GTO da biblioteca
5. Replay individual hands visualmente
6. Quiz GTO baseado nas mãos da borda dos ranges
7. View de torneio individual com curva de BB

**Público-alvo:** jogadores MTT brasileiros que **não têm Hand2Note** (caro/complexo). UX precisa ser amigável pra não-devs.

## Tech stack

- **Backend (parser/builder):** Python 3.10+, stdlib + openpyxl
- **Frontend (app):** Single-file HTML/CSS/JS vanilla (sem frameworks)
- **Distribuição:** Standalone HTML (build_app.py embute dados) ou GitHub Pages
- **Persistência client-side:** localStorage (ranges, benchmarks, quiz state)

## File layout

```
poker-leak-finder/
├── CLAUDE.md                          # este arquivo
├── README.md                          # docs publicas
├── requirements.txt                   # openpyxl
├── src/
│   ├── parser.py                      # parser iPoker XML
│   ├── tournament_classifier.py       # classifica vanilla/bounty/mystery
│   ├── hud_generator.py               # HUD HTML estatico (legado)
│   ├── range_chart.py                 # range chart estatico (legado)
│   ├── leaklab.html                   # ← APP PRINCIPAL (interativo, ~3000 linhas)
│   ├── app_template.html              # template antigo (legado, manter por enquanto)
│   ├── build_app.py                   # bake hands+ranges+benchmarks no leaklab.html
│   └── gen_ranges.py                  # gera JSONs dos ranges transcritos das prints GTO
├── data/
│   ├── benchmarks_default.json        # 78 stats com min/ideal/max em 14 secoes
│   ├── ranges/                        # 8 ranges GTO (BTN/CO/HJ/MP/EP em 30bb + BTN 50/80bb + SB 30bb)
│   └── samples/                       # 3 XMLs de teste
├── docs/
│   ├── DEPLOY.md                      # instrucoes GitHub Pages
│   ├── QUIZ_SPEC.md                   # spec completa do Quiz pra desenvolver isolado
│   ├── index.html                     # versao demo standalone (1.65 MB)
│   └── leaklab-blank.html             # versao sem dados
├── outputs/                           # HTMLs e JSONs gerados (gitignored)
└── (data/maos_dvd, data/temp_*)       # pastas temporarias com mãos do user (gitignored)
```

## iPoker XML format — facts the parser depends on

XML estruturado: `<session>` → `<game>` → `<round no="N">` → `<action>`.

### Action types
| `type` | Significado |
|---|---|
| 0 | Fold |
| 1 | Small blind post |
| 2 | Big blind post |
| 3 | Call |
| 4 | Check |
| 5 | Bet (sem aposta anterior) |
| 7 | All-in |
| 15 | Ante |
| 23 | Raise (sobre aposta anterior) |

### Round numbers
- `0` → antes/blinds
- `1` → preflop
- `2` → flop
- `3` → turn
- `4` → river

### Hero detection
- Hero é identificado por `reg_code == sessioncode` na raiz
- Default fallback name: `Noshovepls`
- Parser auto-detecta se `--hero` não passado

### Cards
- Format: `"H10 D8"` = 10 of Hearts + 8 of Diamonds
- Suits: `H` `S` `C` `D`
- Ranks: `2-9, 10, J, Q, K, A` (note: `10`, não `T`)
- App usa `T` no display

### Position assignment
- Dealer = player com `dealer="1"` no `<player>` element
- Sentido horário do BTN: SB, BB, EP, MP, HJ, CO
- Heads-up: BTN e BB

## Data flow

```
XMLs → parser.py → hands.json (full ou slim)
                    ↓
    leaklab.html (carrega via fetch ou file picker)
    + benchmarks.json
    + ranges/*.json
                    ↓
       UI Interativa (filtros + HUD + drill-down + replay + quiz)
```

## App structure (`src/leaklab.html`)

### 6 abas principais
1. **Filtros & Mãos** — sidebar com 14+ grupos de filtros, matriz 13x13 + lista de mãos
2. **HUD** — 78 stats em 14 secoes com cor verde/amarelo/vermelho. Click stat → drill-down
3. **Torneios** — lista de torneios agrupados, view individual com curva de BB SVG
4. **Biblioteca de Ranges** — upload/view/delete, persistencia localStorage
5. **Benchmarks** — editar min/ideal/max, import/export JSON
6. **Quiz** — perguntas das bordas dos ranges, score persistente, auto-advance

### Filtros disponiveis (sidebar)
- Posicao do Hero / Vilao (PFA)
- Situacao (faced)
- Acao do Hero
- Stack BB (range)
- Mãos (Hand Strength matriz 13x13 mini)
- Hand Strength postflop (Flop/Turn/River) — 18 categorias
- Board (Flop) — 8 tags
- Hero (multi-nick)
- Dataset (vanilla/bounty_ko/mystery)
- Players até flop (range)
- Modificadores (PFA/IP/OOP/Squeeze/BvB/saw_*/SD)
- All-in na street (1-4)
- Resultado (BB)
- Buy-in
- Tablesize
- Periodo (data)

### Auto-load
Se app rodar via http(s), tenta fetch `hands.json` da mesma pasta com **streaming progress** (mostra "Baixando 45% / 152 MB" no badge). Funciona com arquivos grandes (>100 MB).

## 78 stats em 14 secoes (do benchmarks_default.json)

1. **Geral** — VPIP, PFR
2. **Pre-Flop RFI** — EP, MP, HJ, CO, BTN, SB
3. **Pre-Flop Flat** — IP por pos, OOP SB/BB
4. **Pre-Flop 3bet** — por posicao (nai)
5. **Pre-Flop 3bet/F3bet/4bet totais** — nai, ai, tot
6. **Pre-Flop Squeeze** — IP/OOP × nai/ai/tot
7. **Pre-Flop 3bet vs Open Allin**
8. **Pos-Flop IP** — Cbet IP vs BB, +bet turn/river IP, bet vs missed
9. **Pos-Flop OOP** — Cbet OOP, +bet turn/river OOP, check-raise
10. **River** — River bet, Call river
11. **BB Defense** — F2 steal, XF, XC, XR, Prob turn, BB prob river
12. **Advanced** — Aggression flop/turn/river
13. **Showdown** — Saw Flop, WWSF, WTSD, W$SD
14. **Blind War** — SB cbet flop/turn/river, BB F2 SB steal, BB 3BET BW, BB fold vs stab

### Stats que precisam revisao (pesquisa feita 2026-04-25)

**Aggression Frequency (AFq) — formula correta:**
- `(bets + raises) / (bets + raises + calls + folds) × 100`
- Atual no codigo: `aggr / (aggr + call + check)` — INCLUI checks, EXCLUI folds (ERRADO)
- Correcao: usar `aggr / (aggr + call + fold)`
- Source: Upswing, Poker Copilot, BlackRain79

**Probe bet:**
- OOP, opener checked back na street anterior, hero aposta primeiro na proxima
- Atual implementacao: parcial (cobre BB so)

**Donk bet:** OOP, hero aposta no flop ANTES do PFA agir (diferente de probe)

**BB XF/XC/XR:** BB defendeu preflop → opener cbet → BB respondeu (fold/call/raise)

**Check-raise:** times check-raised / times check-raise opportunity (hero checou + vilao apostou + hero re-agiu)

## Stats com drill-downs ✅ TODOS COMPLETOS (2026-04-25)

Todos os 12 drill-downs listados antes como incompletos foram verificados — TÊM leakHands logic com filtros corretos. Lista validada:

- ✅ agg_flop / agg_turn / agg_river — destaca passivos (call/fold) na street
- ✅ check_raise — destaca check-fold/check-call sem CR
- ✅ river_bet / call_river — destaca check perdido / fold demais
- ✅ bb_xf / bb_xc / bb_xr — destaca over-fold / over-call / chance perdida
- ✅ prob_turn / bb_prob_river — destaca check perdido como probe
- ✅ bb_fold_vs_stab — destaca over-fold

## Benchmarks (min / ideal / max)

Editavel via aba "Benchmarks". Salva em localStorage. Import/export JSON disponivel.

Cor coding na HUD:
- **Verde** (good) = ±1 do ideal
- **Amarelo** (warn) = dentro de [min, max] mas fora do ideal
- **Vermelho** (bad) = fora da faixa = LEAK
- **Cinza** (dim) = n<30 (sample insuficiente)

## Ranges GTO (data/ranges/)

8 ranges transcritos visualmente das prints do GTO Wizard que o usuario mandou:
- `btn_30bb`, `btn_50bb`, `btn_80bb` (open BTN em 3 stacks)
- `co_30bb`, `hj_30bb`, `mp_30bb`, `ep_30bb` (opens em 30bb)
- `sb_30bb` (open SB, soma raise+allin do print)

**Regra de transcricao:** se o GTO joga uma mão em qualquer frequencia >0%, marco como `raise=100` no JSON. Resultado: meu range e SEMPRE >= GTO target. Marcado com `"transcribed_from_screenshot": true`.

Pendente:
- BB defense vs raise
- 3bet pots
- 4bet pots
- Outras posicoes em 50/80bb
- BB vs SB
- Push/fold curto (sub-15bb)

## Workflows

### Gerar app standalone com dados embutidos
```bash
python src/build_app.py /pasta/dos/xmls -o leaklab.html
```

### Servir via HTTP (auto-load + dev)
```bash
# Da pasta do projeto
python -m http.server 8767
# Abre http://localhost:8767/src/leaklab.html
```

### Adicionar/regerar ranges das prints
```bash
# Edita src/gen_ranges.py com novos hands
python src/gen_ranges.py
# Saida em data/ranges/
```

### Build pra deploy (GitHub Pages)
```bash
python src/build_app.py data/samples -o docs/index.html
cp src/leaklab.html docs/leaklab-blank.html
git add docs/ && git commit -m "deploy" && git push
# Activate Pages em Settings → Pages → branch main → /docs
```

## User context

- **Davidson** speaks PT-BR (Brazilian)
- Joga MTTs no iPoker (Bounty/KO + Mystery + Vanilla)
- Stack depths 4-50bb
- Não é dev — quer UX simples, sem precisar ler codigo
- Win Python: `C:\Users\Davidson\AppData\Local\Programs\Python\Python313\python.exe`
- Tem GTO Wizard plano top, mas **não consegue achar export** — transcrevemos das prints

## Conventions

- **PT-BR no UI e na conversa**
- Sem emojis em codigo (só se user pedir)
- **Estimativas de tempo** sempre antes de comecar tarefas grandes
- App standalone single-file: NUNCA quebrar em multiplos HTMLs
- LocalStorage keys: prefixo `leaklab_*`
- Color palette: dark `#0d0d0f` background, accent `#2dd4bf` (verde-azulado), good `#5dd684`, bad `#ed6a6a`, warn `#f5c14a`
- Fonte: 'Inter', 'Segoe UI', Arial, sans-serif

## Pendencias (atualizado 2026-04-25)

### Alta prioridade
1. Bug auto-load 152MB (implementado mas nao testado pelo user)
2. Deploy GitHub Pages (user nunca subiu)
3. **Fix Aggression formula** (descoberto na pesquisa — atual implementacao errada)
4. Drill-downs incompletos (~12 stats sem leak overlay)

### Media prioridade
5. Mais ranges GTO (aguardando user mandar prints)
6. Hand Strength river: Missed Draw / Missed Overcard (precisa rastrear estado de draws)
7. Filtros postflop por sequencia de acao (estilo H2N: "Bet Fold", "Check Raise")
8. Save/Load preset filters (combos comuns)
9. Indicador de filtros ativos em todas as tabs (atualmente so Filtros)

### Baixa prioridade
10. Quiz V2 (repeticao espacada, modos cronometrados — ver QUIZ_SPEC.md)
11. Equity calculator no replay
12. PKO/Bounty math
13. Mobile responsive
14. Drag-and-drop pra carregar arquivos

### Em outros chats
- **Quiz V2** — spec completa em `docs/QUIZ_SPEC.md`. User vai desenvolver em chat separado, depois eu integro.

## Privacidade

Hand histories são propriedade do user. **Não commit `data/maos_*` nem `data/temp_*`** — gitignored. Só `data/samples/` (3 XMLs neutros) vai pro repo.
