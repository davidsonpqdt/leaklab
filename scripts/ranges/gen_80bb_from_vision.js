// Gera os 7 ranges 80bb a partir da minha leitura dos prints high-res
// em "C:\Users\Davidson\Documents\Ranges GTO\chipev 80bbs\".
//
// Convenções:
//   - sizing: raise_2x (per "USA COMO SIZE 2X MESMO")
//   - ev: capturado quando legível no print
//   - mixed: true quando célula tem split visual no print (frequência aproximada)
//   - extraction_method: "claude_vision_high_res"
//
// Cada range é definido como lista de {h, ev?, mixed?} pra mãos que ABREM.
// Mãos não listadas = fold (0/100).

const fs = require('fs');
const path = require('path');

const OUT_DIR = path.resolve(__dirname, '..', '..', 'data', 'ranges');

// === Helpers ===
const ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2'];
const ALL_HANDS = [];
for (let i = 0; i < 13; i++) {
  for (let j = 0; j < 13; j++) {
    if (i === j) ALL_HANDS.push(ranks[i] + ranks[j]);
    else if (i < j) ALL_HANDS.push(ranks[i] + ranks[j] + 's');
    else ALL_HANDS.push(ranks[j] + ranks[i] + 'o');
  }
}

const combos = (h) => h.length === 2 ? 6 : (h.endsWith('s') ? 4 : 12);

function buildHands(raises) {
  // raises: lista de objetos { h, ev?, mix? }
  // Se mix: marca como 50/50 raise/fold + flag mixed
  const out = {};
  const raiseMap = new Map(raises.map(r => [r.h, r]));
  for (const h of ALL_HANDS) {
    const r = raiseMap.get(h);
    if (!r) {
      out[h] = { raise_2x: 0, fold: 100 };
    } else if (r.mix) {
      out[h] = { raise_2x: 50, fold: 50, mixed: true };
      if (r.ev !== undefined) out[h].ev = r.ev;
    } else {
      out[h] = { raise_2x: 100, fold: 0 };
      if (r.ev !== undefined) out[h].ev = r.ev;
    }
  }
  return out;
}

function calcPct(handsObj) {
  let total = 0;
  for (const [h, freq] of Object.entries(handsObj)) {
    const aggro = (freq.raise_2x || 0) + (freq.allin || 0);
    total += combos(h) * (aggro / 100);
  }
  return total / 1326 * 100;
}

function writeRange(filename, meta, raises) {
  const hands = buildHands(raises);
  const json = {
    id: meta.id,
    format: '8max',
    stack_bb: 80,
    icm: 'chipev',
    scenario: 'open',
    hero_pos: meta.pos,
    vs: null,
    source: `GTO Wizard ChipEV (${meta.print}) — extraido por Claude Vision high-res`,
    raise_size: '2x',
    actions: ['raise_2x', 'fold'],
    transcribed_from_screenshot: true,
    extraction_method: 'claude_vision_high_res',
    extracted_pct: +calcPct(hands).toFixed(2),
    hands
  };
  fs.writeFileSync(path.join(OUT_DIR, filename), JSON.stringify(json, null, 2));
  console.log(`  ✓ ${filename}  ${json.extracted_pct}%  (${raises.length} hands raise)`);
}

// =================================================================
// UTG 80bb — print "UTG 80BBS.PNG" — ~18.1%
// =================================================================
const utg = [
  // Pares 33+ (22 fold)
  {h:'AA', ev:12.04}, {h:'KK', ev:7.24}, {h:'QQ', ev:3.75}, {h:'JJ', ev:2.09}, {h:'TT', ev:1.28},
  {h:'99', ev:0.83}, {h:'88', ev:0.62}, {h:'77', ev:0.48}, {h:'66', ev:0.35}, {h:'55', ev:0.22},
  {h:'44', ev:0.09}, {h:'33', ev:0.09},
  // Suited As (todos)
  {h:'AKs', ev:2.53}, {h:'AQs', ev:1.27}, {h:'AJs', ev:0.77}, {h:'ATs', ev:0.52},
  {h:'A9s', ev:0.28}, {h:'A8s', ev:0.20}, {h:'A7s', ev:0.16}, {h:'A6s', ev:0.11},
  {h:'A5s', ev:0.22}, {h:'A4s', ev:0.14}, {h:'A3s', ev:0.06}, {h:'A2s', ev:0.01},
  // Offsuit As (ATo fold)
  {h:'AKo', ev:1.52}, {h:'AQo', ev:0.29}, {h:'AJo', ev:0.08},
  // Suited Ks (K7s+)
  {h:'KQs', ev:0.75}, {h:'KJs', ev:0.52}, {h:'KTs', ev:0.39},
  {h:'K9s', ev:0.13}, {h:'K8s', ev:0.04}, {h:'K7s', ev:0.02},
  // Offsuit Ks (apenas KQo)
  {h:'KQo', ev:0.12},
  // Suited Qs
  {h:'QJs', ev:0.36}, {h:'QTs', ev:0.30}, {h:'Q9s', ev:0.09},
  // Suited Js
  {h:'JTs', ev:0.35}, {h:'J9s', ev:0.09},
  // Suited Ts
  {h:'T9s', ev:0.16}, {h:'T8s', ev:0.04},
  // Connectors suited
  {h:'98s', ev:0.02},
  {h:'87s', mix:true}, {h:'76s', mix:true}, {h:'65s', mix:true}, {h:'54s', mix:true},
];

// =================================================================
// UTG+1 80bb — print "UTG+1 80BBS.PNG" — ~21% (mais loose que UTG)
// User chama de "EP" no naming antigo, mantém ep_*
// =================================================================
const ep = [
  // Pares (todos, incl. 22)
  {h:'AA'}, {h:'KK'}, {h:'QQ'}, {h:'JJ'}, {h:'TT'}, {h:'99'}, {h:'88'},
  {h:'77'}, {h:'66'}, {h:'55'}, {h:'44'}, {h:'33'}, {h:'22', mix:true},
  // Suited As (todos)
  {h:'AKs'}, {h:'AQs'}, {h:'AJs'}, {h:'ATs'}, {h:'A9s'}, {h:'A8s'}, {h:'A7s'},
  {h:'A6s'}, {h:'A5s'}, {h:'A4s'}, {h:'A3s'}, {h:'A2s'},
  // Offsuit As (ATo agora entra)
  {h:'AKo'}, {h:'AQo'}, {h:'AJo'}, {h:'ATo', mix:true},
  // Suited Ks (todos K2s-KQs em UTG+1)
  {h:'KQs'}, {h:'KJs'}, {h:'KTs'}, {h:'K9s'}, {h:'K8s'}, {h:'K7s'},
  {h:'K6s', mix:true}, {h:'K5s', mix:true}, {h:'K4s', mix:true}, {h:'K3s', mix:true}, {h:'K2s', mix:true},
  // Offsuit Ks
  {h:'KQo'}, {h:'KJo', mix:true},
  // Suited Qs
  {h:'QJs'}, {h:'QTs'}, {h:'Q9s'}, {h:'Q8s', mix:true},
  // Offsuit Qs
  {h:'QJo', mix:true},
  // Suited Js
  {h:'JTs'}, {h:'J9s'}, {h:'J8s', mix:true},
  // Suited Ts
  {h:'T9s'}, {h:'T8s'},
  // Connectors
  {h:'98s'}, {h:'97s', mix:true},
  {h:'87s'}, {h:'86s', mix:true},
  {h:'76s'}, {h:'75s', mix:true},
  {h:'65s'}, {h:'64s', mix:true},
  {h:'54s'}, {h:'53s', mix:true},
];

// =================================================================
// LJ 80bb — print "LJ 80BBS.PNG" — ~25% (user chama de "MP")
// =================================================================
const mp = [
  // Pares (todos)
  {h:'AA'}, {h:'KK'}, {h:'QQ'}, {h:'JJ'}, {h:'TT'}, {h:'99'}, {h:'88'},
  {h:'77'}, {h:'66'}, {h:'55'}, {h:'44'}, {h:'33'}, {h:'22'},
  // Suited As (todos)
  {h:'AKs'}, {h:'AQs'}, {h:'AJs'}, {h:'ATs'}, {h:'A9s'}, {h:'A8s'}, {h:'A7s'},
  {h:'A6s'}, {h:'A5s'}, {h:'A4s'}, {h:'A3s'}, {h:'A2s'},
  // Offsuit As
  {h:'AKo'}, {h:'AQo'}, {h:'AJo'}, {h:'ATo'},
  // Suited Ks (todos)
  {h:'KQs'}, {h:'KJs'}, {h:'KTs'}, {h:'K9s'}, {h:'K8s'}, {h:'K7s'},
  {h:'K6s'}, {h:'K5s'}, {h:'K4s'}, {h:'K3s', mix:true}, {h:'K2s', mix:true},
  // Offsuit Ks
  {h:'KQo'}, {h:'KJo'}, {h:'KTo', mix:true},
  // Suited Qs
  {h:'QJs'}, {h:'QTs'}, {h:'Q9s'}, {h:'Q8s'}, {h:'Q7s', mix:true},
  // Offsuit Qs
  {h:'QJo'}, {h:'QTo', mix:true},
  // Suited Js
  {h:'JTs'}, {h:'J9s'}, {h:'J8s'}, {h:'J7s', mix:true},
  // Offsuit Js
  {h:'JTo', mix:true},
  // Suited Ts
  {h:'T9s'}, {h:'T8s'}, {h:'T7s', mix:true},
  // Connectors + gappers
  {h:'98s'}, {h:'97s'},
  {h:'87s'}, {h:'86s'},
  {h:'76s'}, {h:'75s'},
  {h:'65s'}, {h:'64s', mix:true},
  {h:'54s'}, {h:'53s', mix:true},
];

// =================================================================
// HJ 80bb — print "HJ 80BBS.PNG" — ~28%
// =================================================================
const hj = [
  // Pares (todos)
  {h:'AA'}, {h:'KK'}, {h:'QQ'}, {h:'JJ'}, {h:'TT'}, {h:'99'}, {h:'88'},
  {h:'77'}, {h:'66'}, {h:'55'}, {h:'44'}, {h:'33'}, {h:'22'},
  // Suited As (todos)
  {h:'AKs'}, {h:'AQs'}, {h:'AJs'}, {h:'ATs'}, {h:'A9s'}, {h:'A8s'}, {h:'A7s'},
  {h:'A6s'}, {h:'A5s'}, {h:'A4s'}, {h:'A3s'}, {h:'A2s'},
  // Offsuit As
  {h:'AKo'}, {h:'AQo'}, {h:'AJo'}, {h:'ATo'}, {h:'A9o', mix:true},
  // Suited Ks (todos)
  {h:'KQs'}, {h:'KJs'}, {h:'KTs'}, {h:'K9s'}, {h:'K8s'}, {h:'K7s'},
  {h:'K6s'}, {h:'K5s'}, {h:'K4s'}, {h:'K3s'}, {h:'K2s'},
  // Offsuit Ks
  {h:'KQo'}, {h:'KJo'}, {h:'KTo'}, {h:'K9o', mix:true},
  // Suited Qs (todos exceto Q2s)
  {h:'QJs'}, {h:'QTs'}, {h:'Q9s'}, {h:'Q8s'}, {h:'Q7s'}, {h:'Q6s', mix:true}, {h:'Q5s', mix:true},
  // Offsuit Qs
  {h:'QJo'}, {h:'QTo'}, {h:'Q9o', mix:true},
  // Suited Js
  {h:'JTs'}, {h:'J9s'}, {h:'J8s'}, {h:'J7s'},
  // Offsuit Js
  {h:'JTo'}, {h:'J9o', mix:true},
  // Suited Ts
  {h:'T9s'}, {h:'T8s'}, {h:'T7s'},
  // Suited 9s
  {h:'98s'}, {h:'97s'}, {h:'96s', mix:true},
  // 8s
  {h:'87s'}, {h:'86s'},
  // 7s
  {h:'76s'}, {h:'75s'}, {h:'74s', mix:true},
  // 6s
  {h:'65s'}, {h:'64s'},
  // 5s
  {h:'54s'}, {h:'53s'},
  // 4s
  {h:'43s', mix:true},
];

// =================================================================
// CO 80bb — print "CO 80BBS.PNG" — ~32-35%
// =================================================================
const co = [
  // Pares (todos)
  {h:'AA'}, {h:'KK'}, {h:'QQ'}, {h:'JJ'}, {h:'TT'}, {h:'99'}, {h:'88'},
  {h:'77'}, {h:'66'}, {h:'55'}, {h:'44'}, {h:'33'}, {h:'22'},
  // Suited As (todos)
  {h:'AKs'}, {h:'AQs'}, {h:'AJs'}, {h:'ATs'}, {h:'A9s'}, {h:'A8s'}, {h:'A7s'},
  {h:'A6s'}, {h:'A5s'}, {h:'A4s'}, {h:'A3s'}, {h:'A2s'},
  // Offsuit As (todos exceto A2o-A4o)
  {h:'AKo'}, {h:'AQo'}, {h:'AJo'}, {h:'ATo'}, {h:'A9o'}, {h:'A8o'}, {h:'A7o', mix:true}, {h:'A5o', mix:true},
  // Suited Ks (todos)
  {h:'KQs'}, {h:'KJs'}, {h:'KTs'}, {h:'K9s'}, {h:'K8s'}, {h:'K7s'},
  {h:'K6s'}, {h:'K5s'}, {h:'K4s'}, {h:'K3s'}, {h:'K2s'},
  // Offsuit Ks
  {h:'KQo'}, {h:'KJo'}, {h:'KTo'}, {h:'K9o'}, {h:'K8o', mix:true},
  // Suited Qs (todos)
  {h:'QJs'}, {h:'QTs'}, {h:'Q9s'}, {h:'Q8s'}, {h:'Q7s'}, {h:'Q6s'}, {h:'Q5s'}, {h:'Q4s', mix:true}, {h:'Q3s', mix:true},
  // Offsuit Qs
  {h:'QJo'}, {h:'QTo'}, {h:'Q9o'}, {h:'Q8o', mix:true},
  // Suited Js
  {h:'JTs'}, {h:'J9s'}, {h:'J8s'}, {h:'J7s'}, {h:'J6s', mix:true}, {h:'J5s', mix:true},
  // Offsuit Js
  {h:'JTo'}, {h:'J9o'}, {h:'J8o', mix:true},
  // Suited Ts
  {h:'T9s'}, {h:'T8s'}, {h:'T7s'}, {h:'T6s', mix:true},
  // Offsuit Ts
  {h:'T9o', mix:true},
  // 9s
  {h:'98s'}, {h:'97s'}, {h:'96s'},
  // 8s
  {h:'87s'}, {h:'86s'}, {h:'85s', mix:true},
  // 7s
  {h:'76s'}, {h:'75s'}, {h:'74s'},
  // 6s
  {h:'65s'}, {h:'64s'},
  // 5s
  {h:'54s'}, {h:'53s'},
  // 4s
  {h:'43s'},
  // 3s
  {h:'32s', mix:true},
];

// =================================================================
// BTN 80bb — print "BTN 80BBS.PNG" — ~50%
// SUBSTITUI o existente (manual transcription mais antiga)
// =================================================================
const btn = [
  // Pares (todos)
  {h:'AA'}, {h:'KK'}, {h:'QQ'}, {h:'JJ'}, {h:'TT'}, {h:'99'}, {h:'88'},
  {h:'77'}, {h:'66'}, {h:'55'}, {h:'44'}, {h:'33'}, {h:'22'},
  // Suited As (todos)
  {h:'AKs'}, {h:'AQs'}, {h:'AJs'}, {h:'ATs'}, {h:'A9s'}, {h:'A8s'}, {h:'A7s'},
  {h:'A6s'}, {h:'A5s'}, {h:'A4s'}, {h:'A3s'}, {h:'A2s'},
  // Offsuit As (todos)
  {h:'AKo'}, {h:'AQo'}, {h:'AJo'}, {h:'ATo'}, {h:'A9o'}, {h:'A8o'}, {h:'A7o'},
  {h:'A6o'}, {h:'A5o'}, {h:'A4o'}, {h:'A3o', mix:true}, {h:'A2o', mix:true},
  // Suited Ks (todos)
  {h:'KQs'}, {h:'KJs'}, {h:'KTs'}, {h:'K9s'}, {h:'K8s'}, {h:'K7s'},
  {h:'K6s'}, {h:'K5s'}, {h:'K4s'}, {h:'K3s'}, {h:'K2s'},
  // Offsuit Ks
  {h:'KQo'}, {h:'KJo'}, {h:'KTo'}, {h:'K9o'}, {h:'K8o'}, {h:'K7o', mix:true}, {h:'K6o', mix:true},
  // Suited Qs (todos)
  {h:'QJs'}, {h:'QTs'}, {h:'Q9s'}, {h:'Q8s'}, {h:'Q7s'}, {h:'Q6s'}, {h:'Q5s'}, {h:'Q4s'}, {h:'Q3s'}, {h:'Q2s', mix:true},
  // Offsuit Qs
  {h:'QJo'}, {h:'QTo'}, {h:'Q9o'}, {h:'Q8o'}, {h:'Q7o', mix:true},
  // Suited Js (todos)
  {h:'JTs'}, {h:'J9s'}, {h:'J8s'}, {h:'J7s'}, {h:'J6s'}, {h:'J5s'}, {h:'J4s', mix:true}, {h:'J3s', mix:true},
  // Offsuit Js
  {h:'JTo'}, {h:'J9o'}, {h:'J8o'}, {h:'J7o', mix:true},
  // Suited Ts
  {h:'T9s'}, {h:'T8s'}, {h:'T7s'}, {h:'T6s'}, {h:'T5s', mix:true},
  // Offsuit Ts
  {h:'T9o'}, {h:'T8o'}, {h:'T7o', mix:true},
  // 9s
  {h:'98s'}, {h:'97s'}, {h:'96s'}, {h:'95s', mix:true},
  // Offsuit 9s
  {h:'98o', mix:true},
  // 8s
  {h:'87s'}, {h:'86s'}, {h:'85s'},
  // 7s
  {h:'76s'}, {h:'75s'}, {h:'74s'},
  // 6s
  {h:'65s'}, {h:'64s'}, {h:'63s', mix:true},
  // 5s
  {h:'54s'}, {h:'53s'},
  // 4s
  {h:'43s'}, {h:'42s', mix:true},
];

// === Escreve todos ===
console.log('Gerando ranges 80bb (sizing 2x):\n');

writeRange('utg_80bb_unopened_chipev.json', { id: 'open_UTG_80bb_chipev_8max', pos: 'UTG', print: 'UTG 80BBS.PNG' }, utg);
writeRange('ep_80bb_unopened_chipev.json',  { id: 'open_EP_80bb_chipev_8max',  pos: 'EP',  print: 'UTG+1 80BBS.PNG (UTG+1 = EP no naming antigo)' }, ep);
writeRange('mp_80bb_unopened_chipev.json',  { id: 'open_MP_80bb_chipev_8max',  pos: 'MP',  print: 'LJ 80BBS.PNG (LJ = MP no naming antigo)' }, mp);
writeRange('hj_80bb_unopened_chipev.json',  { id: 'open_HJ_80bb_chipev_8max',  pos: 'HJ',  print: 'HJ 80BBS.PNG' }, hj);
writeRange('co_80bb_unopened_chipev.json',  { id: 'open_CO_80bb_chipev_8max',  pos: 'CO',  print: 'CO 80BBS.PNG' }, co);
writeRange('btn_80bb_unopened_chipev.json', { id: 'open_BTN_80bb_chipev_8max', pos: 'BTN', print: 'BTN 80BBS.PNG' }, btn);

// =================================================================
// SB 80bb — print "SB 80BBS.PNG" — multi-action: limp/raise/fold
// (separado pois usa actions diferentes — limp predomina, raise minoria, fold só lixo)
// =================================================================
function writeSBMultiAction() {
  const limps = [
    // Verde (call/limp) é maioria — pares pequenos, suited fracos, offsuit médios
    'AA','KK','QQ','JJ','TT','99','88','77','66','55','44','33','22',
    'AKs','AQs','AJs','ATs','A9s','A8s','A7s','A6s','A5s','A4s','A3s','A2s',
    'KQs','KJs','KTs','K9s','K8s','K7s','K6s','K5s','K4s','K3s','K2s',
    'QJs','QTs','Q9s','Q8s','Q7s','Q6s','Q5s','Q4s','Q3s','Q2s',
    'JTs','J9s','J8s','J7s','J6s','J5s','J4s','J3s','J2s',
    'T9s','T8s','T7s','T6s','T5s','T4s','T3s','T2s',
    '98s','97s','96s','95s','94s','93s','92s',
    '87s','86s','85s','84s','83s','82s',
    '76s','75s','74s','73s','72s',
    '65s','64s','63s','62s',
    '54s','53s','52s',
    '43s','42s',
    '32s',
    'AKo','AQo','AJo','ATo','A9o','A8o','A7o','A6o','A5o','A4o','A3o','A2o',
    'KQo','KJo','KTo','K9o','K8o','K7o','K6o','K5o','K4o',
    'QJo','QTo','Q9o','Q8o','Q7o','Q6o','Q5o',
    'JTo','J9o','J8o','J7o','J6o',
    'T9o','T8o','T7o',
    '98o','97o',
    '87o','86o',
    '76o','75o',
    '65o',
    '54o',
  ];
  // Mãos com raise (orange) — minoria; principalmente premium + alguns spots
  const raises = ['AKs','AKo','KK','AA','AQs','QQ','JJ'];

  const hands = {};
  for (const h of ALL_HANDS) {
    hands[h] = { raise_2x: 0, limp: 0, fold: 100 };
  }
  for (const h of limps) {
    hands[h] = { raise_2x: 0, limp: 100, fold: 0 };
  }
  // Sobrescreve os raise (são também limp em parte; pra simplicidade marca como raise)
  for (const h of raises) {
    hands[h] = { raise_2x: 100, limp: 0, fold: 0 };
  }

  let totalRaise = 0, totalLimp = 0;
  for (const [h, f] of Object.entries(hands)) {
    totalRaise += combos(h) * (f.raise_2x || 0) / 100;
    totalLimp += combos(h) * (f.limp || 0) / 100;
  }

  const json = {
    id: 'open_SB_80bb_chipev_8max',
    format: '8max',
    stack_bb: 80,
    icm: 'chipev',
    scenario: 'open',
    hero_pos: 'SB',
    vs: null,
    source: 'GTO Wizard ChipEV (SB 80BBS.PNG) — extraido por Claude Vision high-res',
    raise_size: '2x',
    actions: ['raise_2x', 'limp', 'fold'],
    transcribed_from_screenshot: true,
    extraction_method: 'claude_vision_high_res',
    note: 'SB unopened = scenario com BB. Verde no print = limp (call BB), laranja = raise, azul = fold. Frequencias aproximadas — limp predomina em ~70% do range. Raise minoria com premium.',
    extracted_pct_raise: +(totalRaise / 1326 * 100).toFixed(2),
    extracted_pct_limp: +(totalLimp / 1326 * 100).toFixed(2),
    hands
  };
  fs.writeFileSync(path.join(OUT_DIR, 'sb_80bb_unopened_chipev.json'), JSON.stringify(json, null, 2));
  console.log(`  ✓ sb_80bb_unopened_chipev.json  raise=${json.extracted_pct_raise}% limp=${json.extracted_pct_limp}% (multi-action)`);
}

writeSBMultiAction();

console.log('\nDone. 7 ranges 80bb gerados em data/ranges/');
