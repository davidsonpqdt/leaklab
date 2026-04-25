// Converte greenline.ts e pekarstas.ts (formato AHTOOOXA/poker-charts)
// pro JSON canônico do LeakLab.
// Uso: node convert.js

const fs = require('fs');
const path = require('path');

const dir = __dirname;
const outDir = path.join(dir, '..', 'ranges', 'cash_6max_100bb');
fs.mkdirSync(outDir, { recursive: true });

// Gera lista de 169 mãos no formato "AKo", "AKs", "AA"
const ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2'];
const ALL_HANDS = [];
for (let i = 0; i < 13; i++) {
  for (let j = 0; j < 13; j++) {
    if (i === j) ALL_HANDS.push(ranks[i] + ranks[j]);
    else if (i < j) ALL_HANDS.push(ranks[i] + ranks[j] + 's');
    else ALL_HANDS.push(ranks[j] + ranks[i] + 'o');
  }
}

// Parse TS file removendo TS-isms e fazendo eval
function parseChartFile(filename) {
  let content = fs.readFileSync(path.join(dir, filename), 'utf-8');
  // Remove imports e exports TS
  content = content.replace(/^import.*?$/gm, '');
  content = content.replace(/export const charts:[^=]*=/, 'const charts =');
  // Remove comentarios single-line
  content = content.replace(/^\s*\/\/.*$/gm, '');
  // Wrap em IIFE pra eval
  return (new Function(content + '\nreturn charts;'))();
}

// Converte ação do formato pekarstas/greenline pro formato canônico
// 'raise', 'fold', 'call', 'allin', ou ['raise','fold'] (mixed)
function actionToFreq(action) {
  // Default fold pra mãos não listadas
  if (!action) return { raise_2x: 0, fold: 100 };

  if (Array.isArray(action)) {
    // Mixed: divide igualmente entre as ações
    const freq = 100 / action.length;
    const result = { raise_2x: 0, call: 0, allin: 0, fold: 0 };
    for (const a of action) {
      if (a === 'raise') result.raise_2x += freq;
      else if (a === 'fold') result.fold += freq;
      else if (a === 'call') result.call += freq;
      else if (a === 'allin') result.allin += freq;
    }
    return result;
  }

  // Action única
  if (action === 'raise') return { raise_2x: 100, fold: 0 };
  if (action === 'fold')  return { raise_2x: 0, fold: 100 };
  if (action === 'call')  return { raise_2x: 0, call: 100, fold: 0 };
  if (action === 'allin') return { raise_2x: 0, allin: 100, fold: 0 };
  return { raise_2x: 0, fold: 100 };
}

// Determina actions array baseado no que aparece no chart
function deriveActions(chart) {
  const actions = new Set(['fold']);
  for (const a of Object.values(chart)) {
    if (Array.isArray(a)) a.forEach(x => actions.add(x === 'raise' ? 'raise_2x' : x));
    else if (a === 'raise') actions.add('raise_2x');
    else actions.add(a);
  }
  return Array.from(actions);
}

// Calcula % do range (combos com raise+allin / 1326)
function calcPct(handsObj) {
  const combos = (h) => h.length === 2 ? 6 : (h.endsWith('s') ? 4 : 12);
  let total = 0;
  for (const [h, freq] of Object.entries(handsObj)) {
    const aggro = (freq.raise_2x || 0) + (freq.allin || 0);
    total += combos(h) * (aggro / 100);
  }
  return total / 1326 * 100;
}

// Converte um chart inteiro pro JSON canônico
function convertChart(chart, key, providerName, scenarioMeta) {
  // key examples: 'UTG-RFI', 'BB-vs-open-BTN', 'CO-vs-3bet-BTN'
  const parts = key.split('-');
  const heroPos = parts[0];
  let scenario, vs = null;
  if (parts[1] === 'RFI') {
    scenario = 'open';
  } else if (parts[1] === 'vs') {
    scenario = parts[2]; // 'open', '3bet', '4bet'
    vs = parts[3] || null;
  } else {
    scenario = parts[1];
  }

  const hands = {};
  for (const hand of ALL_HANDS) {
    hands[hand] = actionToFreq(chart[hand]);
  }

  const id = vs
    ? `${scenario}_${heroPos}_vs_${vs}_${providerName}_100bb_6max`
    : `${scenario.toLowerCase()}_${heroPos}_100bb_6max_${providerName}`;

  return {
    id,
    format: '6max_cash',
    stack_bb: 100,
    icm: 'chipev',
    scenario,
    hero_pos: heroPos,
    vs,
    source: scenarioMeta.source,
    license: 'MIT (AHTOOOXA/poker-charts)',
    sizing_note: scenarioMeta.sizingNote || null,
    actions: deriveActions(chart).filter(a => a !== 'fold').concat(['fold']),
    extracted_pct: +calcPct(hands).toFixed(2),
    hands
  };
}

// === EXECUTA ===
const providers = [
  {
    name: 'greenline',
    file: 'greenline.ts',
    source: 'GreenCharts2024_01.pdf (Greenline Poker) via github.com/AHTOOOXA/poker-charts',
    sizingNote: 'UTG 3bb / MP 3bb / CO 2.5bb / BTN 2.5bb / SB 3bb (cash 100bb 6-max)'
  },
  {
    name: 'pekarstas',
    file: 'pekarstas.ts',
    source: 'Pekár Stas charts via github.com/AHTOOOXA/poker-charts',
    sizingNote: 'cash 100bb 6-max'
  }
];

let totalConverted = 0;
const summary = [];

for (const p of providers) {
  let charts;
  try {
    charts = parseChartFile(p.file);
  } catch (e) {
    console.error(`Failed to parse ${p.file}: ${e.message}`);
    continue;
  }

  for (const [key, chart] of Object.entries(charts)) {
    try {
      const json = convertChart(chart, key, p.name, p);
      const fileName = `${p.name}_${key.toLowerCase().replace(/-/g, '_')}.json`;
      fs.writeFileSync(path.join(outDir, fileName), JSON.stringify(json, null, 2));
      summary.push({ provider: p.name, key, pct: json.extracted_pct, file: fileName });
      totalConverted++;
    } catch (e) {
      console.error(`Failed ${p.name}/${key}: ${e.message}`);
    }
  }
}

console.log(`\n✓ Convertidos: ${totalConverted} ranges`);
console.log(`✓ Salvos em: ${outDir}\n`);
console.log('Resumo:');
const byProvider = {};
for (const s of summary) {
  if (!byProvider[s.provider]) byProvider[s.provider] = [];
  byProvider[s.provider].push(s);
}
for (const [prov, items] of Object.entries(byProvider)) {
  console.log(`\n  ${prov} (${items.length}):`);
  for (const it of items.slice(0, 20)) {
    console.log(`    ${it.key.padEnd(28)}  ${String(it.pct).padStart(6)}%`);
  }
  if (items.length > 20) console.log(`    ... +${items.length - 20} more`);
}
