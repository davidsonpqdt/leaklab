# LeakLab Quiz — Especificação Completa

Spec do sistema de Quiz GTO. Documento autocontido pra desenvolver o quiz como módulo separado e depois reintegrar ao LeakLab (`src/leaklab.html`).

---

## 1. Visão e Propósito

### Problema
Jogadores de poker MTT que estudam ranges GTO no GTO Wizard / FreeBetRange / similares **decoram a tabela mas não internalizam**. Precisa de prática repetitiva pra fixar — especialmente nas mãos da borda (mãos marginais com EV baixo).

### Solução
Quiz interativo que pega uma **biblioteca de ranges GTO** (formato JSON, ver §3) e gera perguntas tipo:

> "BTN, 30bb, unopened — o que GTO faz com **K9o**?"
>
> [▲ Open / Raise]    [✗ Fold]    [Pular]

Após responder, mostra:
- ✓/✗ verdict
- Frequência exata do GTO (ex: "GTO faz raise 100% do tempo, EV +0.59 BB")
- Próxima pergunta (manual ou auto-advance)

### Público-alvo
Jogadores intermediários de MTT que jogam stacks 10-100bb. Brasileiros (PT-BR é a língua principal).

---

## 2. Estado Atual (já implementado no LeakLab)

Localização: `src/leaklab.html` (procure por "// ===== Quiz =====").

### Funciona
- Tab "Quiz" no app principal
- Seleciona range aleatório da biblioteca (ou range fixo via dropdown)
- Pega mão aleatória do range
- 2 modos:
  - **Bordas** (default): prioriza mãos com EV positivo baixo (< 1.5 BB) entre os opens
  - **Aleatório**: qualquer mão do range
- 3 ações: Open/Raise, Fold, Pular
- Feedback instantâneo: ✓ correto + EV do GTO, ou ✗ errado + verdict
- Score `acertos/total` no header
- Auto-advance opcional (toggle, persiste em localStorage)
  - 1.0s pra acertos, 1.8s pra erros
  - Botões desabilitados durante feedback (evita clique duplo)
- Histórico das últimas 30 respostas
- Score por range (ex: "open_BTN_30bb_chipev_8max: 5/7 = 71%")
- Botões desabilitados durante o feedback
- Reset de score (com confirmação)
- Persistência total em `localStorage["leaklab_quiz_state"]`

### Limitações atuais
- Apenas pergunta binária Open vs Fold (não suporta Call, 3bet, 4bet, etc.)
- Sem timer / pressure mode
- Sem dificuldade progressiva
- Sem repetição espaçada (mãos erradas não voltam mais)
- Mostra suits genéricos (não usa as suit specifics do GTO Wizard)
- Sem timer mode / speed challenge
- Sem categorias visuais (mão "premium", "marginal", "trash")

---

## 3. Modelo de Dados — Ranges GTO

### Formato JSON (canonical)

```json
{
  "id": "open_BTN_30bb_chipev_8max",
  "format": "8max",
  "stack_bb": 30,
  "icm": "chipev",
  "scenario": "open",
  "hero_pos": "BTN",
  "vs": null,
  "raise_size": "2x",
  "actions": ["raise_2x", "fold"],
  "source": "GTO Wizard ChipEV",
  "transcribed_from_screenshot": true,
  "gto_target_pct": 48.7,
  "hands": {
    "AA":  {"raise_2x": 100, "fold": 0,   "ev": 10.61},
    "KK":  {"raise_2x": 100, "fold": 0,   "ev": 8.43},
    "K9o": {"raise_2x": 100, "fold": 0,   "ev": 0.20},
    "K8o": {"raise_2x": 0,   "fold": 100, "ev": 0},
    "...": "..."
  }
}
```

### Campos importantes
- `id` — string única (chave no localStorage e no Quiz)
- `hero_pos` — `EP | MP | HJ | CO | BTN | SB | BB`
- `scenario` — `open | defense | 3bet | 4bet | etc`
- `vs` — posição do oponente (null se unopened)
- `stack_bb` — profundidade em BB
- `actions` — lista das chaves possíveis em cada hand (ex: `["raise_2x", "fold"]` ou `["raise_3x", "call", "fold"]`)
- `hands` — dict de 169 hand labels (`AA`, `AKs`, `AKo`, etc.) → frequências por ação + ev opcional

### Hand labels (169 totais)
Pares: `AA, KK, QQ, JJ, TT, 99, 88, 77, 66, 55, 44, 33, 22` (13)
Suited: `AKs, AQs, ..., A2s, KQs, ..., 32s` (78)
Offsuit: `AKo, AQo, ..., A2o, KQo, ..., 32o` (78)

### Como detectar "in range" em qualquer ação raise
```js
function isOpenHand(handInfo) {
  return Object.entries(handInfo).some(([k, v]) =>
    (k.startsWith("raise") || ["open", "allin", "shove", "all-in"].includes(k))
    && typeof v === "number" && v > 0
  );
}
```

### Ranges existentes
Já temos 8 ranges em `data/ranges/`:
- `btn_30bb_unopened_chipev.json` (BTN open 30bb)
- `btn_50bb_unopened_chipev.json` (BTN open 50bb)
- `btn_80bb_unopened_chipev.json` (BTN open 80bb)
- `co_30bb_unopened_chipev.json`
- `hj_30bb_unopened_chipev.json`
- `mp_30bb_unopened_chipev.json`
- `ep_30bb_unopened_chipev.json`
- `sb_30bb_unopened_chipev.json`

---

## 4. UI / UX Detalhada

### Layout

```
┌──────────────────────────────────────────────┐
│ Quiz GTO                    Acertos 12 / 15 │
│ Aprenda os ranges da biblioteca              │
├──────────────────────────────────────────────┤
│ Range: [Aleatório ▼]  Modo: [Bordas ▼]      │
│ ☑ Auto-avançar      [Resetar score]         │
├──────────────────────────────────────────────┤
│                                              │
│           BTN OPEN · 30BB · CHIPEV          │
│           open_BTN_30bb_chipev_8max          │
│                                              │
│              ┌──────┐  ┌──────┐              │
│              │ K ♠  │  │ 9 ♦  │              │
│              └──────┘  └──────┘              │
│                                              │
│                   K9o                        │
│                                              │
│         O que GTO faz com essa mão?          │
│                                              │
│   [▲ Open/Raise]  [✗ Fold]  [Pular →]       │
│                                              │
│   ┌────────────────────────────────────┐    │
│   │ ✓ Correto!                          │    │
│   │ GTO faz open/raise com K9o.        │    │
│   │ EV: +0.59 BB                        │    │
│   │ Próxima em 1.0s...                  │    │
│   └────────────────────────────────────┘    │
│                                              │
├──────────────────────────────────────────────┤
│ ACERTOS POR RANGE                            │
│ open_BTN_30bb_chipev_8max     12/15  (80%)  │
│ open_CO_30bb_chipev_8max       3/4   (75%)  │
├──────────────────────────────────────────────┤
│ HISTÓRICO RECENTE                            │
│ K9o   raise   open_BTN_30bb       ✓ open    │
│ T8o   fold    open_HJ_30bb        ✓ fold    │
│ A5s   fold    open_BTN_30bb       ✗ open    │
└──────────────────────────────────────────────┘
```

### Estilo visual (LeakLab dark theme)
- Background: `#0d0d0f` / `#16161a` (cards)
- Texto: `#e6e6e8` / `#888` (dim)
- Accent: `#2dd4bf` (verde-azulado)
- Verde (correto): `#5dd684`
- Vermelho (erro): `#ed6a6a`
- Amarelo (warning/score): `#f0c419`
- Fonte: `'Inter', -apple-system, 'Segoe UI', Arial, sans-serif`

### Cartas visuais
- Width 80px, height 110px, border-radius 10px
- Fundo branco padrão; copas/ouros vermelho ou azul; paus verde; espadas preto
- Sombra `0 4px 12px rgba(0,0,0,0.6)`
- Naipes via símbolos Unicode: ♥ ♦ ♣ ♠
- 10 vira "T" no display

### Comportamento das ações
- Click "Open/Raise" → marca resposta como "raise"
- Click "Fold" → marca como "fold"
- Click "Pular" → não conta no score, próxima pergunta
- Após responder:
  - Botões disabled (`disabled` attribute) imediatamente
  - Feedback aparece com cor (verde/vermelho)
  - Score header atualiza
  - Histórico adiciona entrada
  - Per-range stats atualiza
  - Se auto-advance ON: timer de 1.0s (correto) ou 1.8s (errado) → próxima
  - Se auto-advance OFF: botão "Próxima pergunta →" no feedback

### Filtros / Configuração
- **Range dropdown**: "Aleatório (todos)" + lista de IDs disponíveis
- **Modo dropdown**: "Bordas (mais difícil)" | "Aleatório"
- **Auto-avançar checkbox**: persiste em `localStorage.leaklab_quiz_auto`
- **Reset score**: com `confirm()` antes

---

## 5. Lógica do Quiz

### Pseudocódigo principal

```js
function nextQuizQuestion() {
  const range = pickRandomRange();        // escolhe range
  const [label, info] = pickQuestionHand(range);  // escolhe mão
  const isOpen = isOpenHand(info);
  QUIZ.current = { range, label, info, isOpen, ev: info.ev };
  renderQuestion();
}

function pickRandomRange() {
  if (QUIZ.selectedRangeId) return RANGES[QUIZ.selectedRangeId];
  const ids = Object.keys(RANGES);
  return RANGES[ids[Math.floor(Math.random() * ids.length)]];
}

function pickQuestionHand(range) {
  const entries = Object.entries(range.hands);
  if (QUIZ.mode === "border") {
    // Mãos com EV baixo entre as opens
    const opensLowEv = entries.filter(([_, info]) => {
      const isOpen = isOpenHand(info);
      const ev = info.ev || 0;
      return isOpen && ev > 0 && ev < 1.5;
    });
    if (opensLowEv.length > 0) {
      return opensLowEv[Math.floor(Math.random() * opensLowEv.length)];
    }
  }
  return entries[Math.floor(Math.random() * entries.length)];
}

function isOpenHand(info) {
  return Object.entries(info).some(([k, v]) =>
    (k.startsWith("raise") || ["open","allin","shove","all-in"].includes(k))
    && typeof v === "number" && v > 0
  );
}

function answerQuiz(action) {
  const { isOpen, ev } = QUIZ.current;
  const correct = (action === "raise" && isOpen) || (action === "fold" && !isOpen);
  QUIZ.total++;
  if (correct) QUIZ.score++;
  // ... atualiza perRange, history, salva state, mostra feedback
}
```

### Geração de suits (visual apenas, nada importante)
```js
function suitsForLabel(label) {
  if (label.length === 2) return ["s", "c"];        // par: espadas + paus
  if (label.endsWith("s")) return ["h", "h"];       // suited: ambos copas
  if (label.endsWith("o")) return ["s", "d"];       // off-suit: espadas + ouros
  return ["s", "c"];
}

function ranksForLabel(label) {
  return [label[0], label[1]];   // primeira e segunda letra
}
```

---

## 6. Estado e Persistência

### Estrutura
```js
const QUIZ = {
  selectedRangeId: null,        // ID do range fixo (null = aleatório)
  current: null,                 // { range, label, info, isOpen, ev }
  score: 0,                      // total acertos sessão
  total: 0,                      // total perguntas
  history: [],                   // últimas 30 respostas
  perRange: {},                  // { rangeId: { score, total } }
  mode: "border",                // "border" | "random"
  autoAdvance: false,            // bool
  autoAdvanceTimer: null,        // setTimeout id
};
```

### Histórico item
```js
{
  label: "K9o",
  action: "raise",                  // o que usuário clicou
  isOpen: true,                     // o que GTO faz
  correct: true,
  range: "open_BTN_30bb_chipev_8max",
  ev: 0.59
}
```

### Per-range
```js
{ "open_BTN_30bb_chipev_8max": { score: 12, total: 15 } }
```

### LocalStorage keys
- `leaklab_quiz_state` (JSON com score, total, perRange, history)
- `leaklab_quiz_auto` ("0" ou "1")

### Save/load
```js
function saveQuizState() {
  localStorage.setItem("leaklab_quiz_state", JSON.stringify({
    score: QUIZ.score, total: QUIZ.total,
    perRange: QUIZ.perRange, history: QUIZ.history.slice(0, 30)
  }));
}

function loadQuizState() {
  try { return JSON.parse(localStorage.getItem("leaklab_quiz_state") || "{}"); }
  catch { return {}; }
}
```

---

## 7. Funcionalidades Futuras (Roadmap)

Em ordem de impacto:

### A. Repetição espaçada (mais impacto)
Quando errar uma mão, ela tem **maior probabilidade** de aparecer de novo nas próximas 5-10 perguntas. Após acertar 2x seguidas, sai da fila.

```js
// pseudocódigo
const wrongQueue = []; // mãos erradas pendentes
function pickQuestionHand(range) {
  if (wrongQueue.length > 0 && Math.random() < 0.4) {
    return wrongQueue.shift();
  }
  // senão fluxo normal...
}
```

### B. Modos de pergunta expandidos
Suporte a:
- **3bet vs raise**: "BTN abriu, você está na BB com X. O que GTO faz?" → Call / 3bet / Fold (3 ações)
- **Call all-in**: "Vilão deu shove de 15bb. Hero pode call. O que GTO faz?" → Call / Fold
- **Bet sizing**: "GTO aposta no flop. Que tamanho?" → 1/3 pot / 2/3 pot / Pot / Allin

Para isso, ranges precisam ter mais de 2 actions:
```json
"K9s": {"raise_3x": 60, "call": 30, "fold": 10}
```

A pergunta seria: "qual a ação MAIS frequente do GTO com K9s aqui?" → Resposta correta = "raise_3x" (60%)

### C. Modo cronometrado
Timer de N segundos por pergunta. Se passar, conta como errado. Útil pra simular pressão real.

### D. Filtro por situação
Permite quizar só sobre, ex.: "BTN unopened entre 20-40bb" — pega vários ranges que casam com filtro.

### E. Modo flashcard reverso
"Eu mostro a ação (ex: 'fold') — você responde com quais mãos GTO foldaria do BTN?" Exibe matriz e usuário marca células.

### F. Streaks e badges
- "🔥 3 acertos seguidos!"
- "Mestre do BTN" (90%+ no BTN range)

### G. Relatório de fraquezas
Após N respostas: "Você está errando muito offsuits ofensivos do EP. Foque em A8o-AJo."

### H. Quiz diário
1 mão escolhida pelo dia. Tracking de "streak" ao longo dos dias.

### I. Multi-jogador
Compartilhar score com amigos via URL.

---

## 8. Interface de Integração com LeakLab

Pra reintegrar ao LeakLab depois, expor uma API simples:

### Como módulo standalone
Arquivo único `quiz.js` que define:

```js
const LeakLabQuiz = {
  init(container, config) {
    // Inicializa quiz dentro de um <div>
    // config = { ranges, onAnswer, autoAdvance, mode }
  },

  loadRanges(ranges) {
    // Carrega array de range JSONs
  },

  getState() {
    // Retorna { score, total, perRange, history }
  },

  setState(state) {
    // Restaura state (útil se LeakLab quer salvar centralizadamente)
  },

  next() {
    // Força próxima pergunta
  },

  destroy() {
    // Limpa timers, listeners
  }
};
```

### Estilo CSS
Toda a estilização **no escopo `.leaklab-quiz`** (prefixo) pra não vazar:

```css
.leaklab-quiz { font-family: ...; color: ...; }
.leaklab-quiz .quiz-card { ... }
.leaklab-quiz .quiz-actions button { ... }
```

### Exemplo de uso embedded
```html
<div id="quiz-host"></div>
<script src="quiz.js"></script>
<script>
  fetch("ranges/btn_30bb.json").then(r => r.json()).then(range => {
    LeakLabQuiz.init(document.getElementById("quiz-host"), {
      ranges: [range],
      autoAdvance: true,
      mode: "border"
    });
  });
</script>
```

---

## 9. Checklist de implementação

Pra desenvolver o quiz isolado em outro chat:

### MVP (1-2h)
- [ ] HTML estático com layout (header, config, card, feedback, history)
- [ ] CSS dark theme (cores listadas em §4)
- [ ] Carregar ranges via fetch ou file input
- [ ] Função `pickQuestionHand` com modo border/random
- [ ] Renderizar pergunta (cartas + label + scenario)
- [ ] 3 botões de ação + handlers
- [ ] Feedback visual com EV
- [ ] Score persistente em localStorage

### V2 (2-3h)
- [ ] Auto-advance toggle com timer
- [ ] Histórico de 30 respostas
- [ ] Per-range leaderboard
- [ ] Botão Reset com confirmação
- [ ] Repetição espaçada (mãos erradas voltam)
- [ ] Modo cronometrado opcional
- [ ] Estatísticas: % acerto por categoria (premium / marginal / trash)

### V3 (3-5h, futuro)
- [ ] Suporte a 3+ ações (3bet pots, etc.)
- [ ] Filtro por situação (multi-range matching)
- [ ] Modo flashcard reverso
- [ ] Quiz diário com streak
- [ ] Export/import de score

### Integração final no LeakLab
- [ ] Refatorar pra módulo `LeakLabQuiz` com API descrita em §8
- [ ] Substituir o código atual em `src/leaklab.html` (procure "// ===== Quiz =====")
- [ ] Manter o estado existente do localStorage (chave `leaklab_quiz_state`)
- [ ] Testar com os 8 ranges existentes em `data/ranges/`

---

## 10. Notas finais

### Tom da comunicação
- Tudo em **PT-BR**
- Direto e prático ("o que GTO faz", "✓ Correto!", "Pular →")
- Sem jargão técnico desnecessário ("EV +0.59 BB" sim, "expected value de 0.59 big blinds" não)

### Qualidade dos ranges
Os ranges existentes foram **transcritos manualmente de prints do GTO Wizard**. Estão marcados com `"transcribed_from_screenshot": true` — podem ter pequenos erros de borda. Quando o usuário tiver export do GTO Wizard real, substitua os JSONs e o quiz vai usar automaticamente.

### Privacidade
Tudo client-side, sem backend. Score e histórico em localStorage do navegador. Nada vai pro servidor.

### Performance
Mesmo com 50+ ranges carregados (cada ~7 KB), o quiz é instantâneo. JSON parse é trivial.

---

**Fim da spec.** Use esse documento em outro chat pra construir o quiz separadamente, depois traga de volta pra integrar no `src/leaklab.html`.
