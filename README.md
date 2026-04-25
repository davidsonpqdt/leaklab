# 🎯 LeakLab — Quiz GTO de Pôquer MTT

Treine ranges GTO de pôquer torneio (MTT) em quiz interativo. **Sem cadastro, sem dados, sem instalação** — abre no navegador e começa.

🌐 **Demo online:** *[link aparece após deploy GitHub Pages — ver `docs/DEPLOY.md`]*

## ✨ O que faz

### Quiz GTO (foco principal)
- **Mesa visual** mostrando posições, hero highlighted, dealer button, suas cartas
- **101 ranges GTO** prontos (MTT 8-max + Cash 6-max)
- **3 modos**: Bordas (mãos didáticas), Aleatório, Repetir Erros (spaced repetition)
- **Drill 30s** com pontuação +1/-1 e ranking
- **Estudo focado** de 10 perguntas por posição com relatório
- **Heatmap de erros** + gráfico de tendência rolling
- **Atalhos teclado** (R/F/N), som opcional, mobile responsive
- **Export CSV/JSON** do histórico
- **Share URL** com config (`?stack=80&pos=UTG&mode=border`)

### Análise pessoal (opcional)
- **Parser** de hand histories (iPoker, PokerStars, GG, 888)
- **HUD com 78 estatísticas** (VPIP, PFR, 3bet, C-bet, BB Defense, etc.) com color-coded leaks
- **Drill-down em qualquer stat** → matriz de mãos do leak em vermelho
- **Replay animado** de mãos individuais
- **View de torneio** com curva de BB

## 🚀 Como usar

### 1. Online (recomendado)
Abre o link da [demo](#) e clica em **▶ Começar Quiz**. Nada mais.

### 2. PWA install (mobile)
No celular: abre o site → menu do navegador → **"Adicionar à tela inicial"**. Roda offline depois.

### 3. Local (sem internet)
```bash
git clone https://github.com/SEU-USUARIO/leaklab.git
cd leaklab
python -m http.server 8767 --directory docs
# Abre http://localhost:8767/
```
Ou simplesmente abre `docs/index.html` direto no navegador.

## ⌨️ Atalhos

| Tecla | Ação |
|---|---|
| `R` | Open / Raise |
| `F` | Fold |
| `N` ou `Espaço` | Próxima / Pular |
| `Esc` | Fechar modal |

## 📁 Estrutura

```
leaklab/
├── docs/                     # Versão pública (GitHub Pages)
│   ├── index.html            # App standalone com 7 sample hands (3 MB)
│   ├── leaklab-blank.html    # Versão sem dados
│   ├── manifest.json         # PWA
│   └── icons/                # SVG icons
├── src/                      # Código fonte
│   └── leaklab.html          # App template (~290k chars)
├── data/
│   ├── ranges/               # 101 ranges GTO em JSON
│   └── benchmarks_default.json
└── scripts/
    ├── ranges/               # build, fixids, genmanifest
    └── check_syntax.js
```

## 🛠️ Ranges GTO incluídos

| Tipo | Quantidade | Fonte |
|---|---|---|
| MTT 8-max ChipEV 80bb | 6 (UTG/EP/MP/HJ/CO/BTN) | GTO Wizard, vision-extracted |
| MTT 8-max ChipEV 30bb | 7 (todas posições) | Transcrição manual |
| MTT 8-max ChipEV 50bb | 1 (BTN) | Transcrição manual |
| Cash 6-max 100bb | 88 ranges | [AHTOOOXA/poker-charts](https://github.com/AHTOOOXA/poker-charts) (MIT) |

## 🧰 Análise pessoal (opcional, requer Python)

Se você joga MTT no iPoker, PokerStars, GG ou 888:

```bash
# 1) Gera JSON com suas mãos (parser detecta hero automaticamente)
python src/parser.py /pasta/com/xml-files -o hands.json

# 2) Carrega hands.json no app via "📊 Carregar Mãos"
```

App computa **78 estatísticas** com cores indicando leaks. Click em qualquer stat → drill-down com mãos exatas do leak em vermelho.

## 🤝 Contribuir

- **Mais ranges**: prints high-res do GTO Wizard com EVs visíveis. Manda issue ou PR com print + posição/stack.
- **Bugs/UX**: abre issue. Foco em UX pra jogadores não-devs.
- **Cenários expandidos**: 3bet pots, BB defense, squeeze ainda faltam.

## 📜 Licença

MIT. Ranges externos da AHTOOOXA também MIT.

## 🙏 Créditos

- Ranges cash: [AHTOOOXA/poker-charts](https://github.com/AHTOOOXA/poker-charts) (Anton Safonov, MIT)
- Ranges MTT: GTO Wizard ChipEV solver
- Web Audio API pro feedback sonoro
- Public domain: poker terminology

---

**Feedback?** Abre uma [issue](../../issues) ou compartilha com 5 amigos jogadores 🎴
