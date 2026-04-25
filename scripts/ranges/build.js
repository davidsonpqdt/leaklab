// Build de ranges: regenera _index.json e fixa IDs.
// Uso:
//   node build.js          # one-shot
//   node build.js --watch  # watch mode (regenera quando arquivo muda)
//
// Requer: Node 14+ (uses fs.watch). Sem dependências externas.

const fs = require('fs');
const path = require('path');

const RANGES_DIR = path.resolve(__dirname, '..', '..', 'data', 'ranges');
const INDEX_PATH = path.join(RANGES_DIR, '_index.json');

// === walk recursivo (ignora _* arquivos) ===
function walk(dir, base) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    const rel = path.relative(base, full).split(path.sep).join('/');
    if (e.isDirectory()) {
      out.push(...walk(full, base));
    } else if (e.name.endsWith('.json') && !e.name.startsWith('_')) {
      out.push(rel);
    }
  }
  return out;
}

// === Fixa IDs de ISO (não-open) que estão como "open_..." ===
function fixIds() {
  let fixed = 0;
  function visit(dir) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) { visit(full); continue; }
      if (!e.name.endsWith('.json') || e.name.startsWith('_')) continue;
      try {
        const j = JSON.parse(fs.readFileSync(full, 'utf-8'));
        if (!j.vs && j.scenario && j.scenario !== 'open' && j.id && j.id.startsWith('open_')) {
          const provider = j.id.split('_').pop();
          const newId = j.scenario.toLowerCase() + '_' + j.hero_pos + '_' + (j.stack_bb || 'X') + 'bb_' +
                        (j.format ? j.format.replace('_cash','') : 'unknown') + '_' + provider;
          if (newId !== j.id) {
            j.id = newId;
            fs.writeFileSync(full, JSON.stringify(j, null, 2));
            fixed++;
          }
        }
      } catch (e) { /* skip invalid JSON */ }
    }
  }
  visit(RANGES_DIR);
  return fixed;
}

// === Gera manifest ===
function genManifest() {
  const files = walk(RANGES_DIR, RANGES_DIR);
  const manifest = { version: 1, count: files.length, files: files.sort(), generatedAt: new Date().toISOString() };
  fs.writeFileSync(INDEX_PATH, JSON.stringify(manifest, null, 2));
  return files.length;
}

function build() {
  const t0 = Date.now();
  const fixed = fixIds();
  const count = genManifest();
  const dt = Date.now() - t0;
  console.log(`[build] ${count} ranges, ${fixed} IDs fixed (${dt}ms)`);
  return count;
}

function watch() {
  build();
  console.log(`[watch] vigiando ${RANGES_DIR} (Ctrl+C pra sair)`);
  let pending = null;
  const debounceRebuild = () => {
    if (pending) clearTimeout(pending);
    pending = setTimeout(() => { pending = null; build(); }, 300);
  };
  fs.watch(RANGES_DIR, { recursive: true }, (event, filename) => {
    if (!filename) return;
    // Ignora _index.json e _*.js (auto-gerados/scripts)
    if (filename.endsWith('_index.json') || path.basename(filename).startsWith('_')) return;
    if (!filename.endsWith('.json')) return;
    debounceRebuild();
  });
}

if (process.argv.includes('--watch')) {
  watch();
} else {
  build();
}
