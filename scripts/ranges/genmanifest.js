// Gera _index.json listando todos os ranges em data/ranges/ (recursivo)
// Uso: node _genmanifest.js
const fs = require('fs');
const path = require('path');

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

const dir = require('path').resolve(__dirname, '..', '..', 'data', 'ranges');
const files = walk(dir, dir);
const manifest = { version: 1, count: files.length, files: files.sort() };
fs.writeFileSync(path.join(dir, '_index.json'), JSON.stringify(manifest, null, 2));
console.log('Manifest gerado:', files.length, 'ranges');
console.log('Primeiros 5:');
files.slice(0, 5).forEach(f => console.log('  ' + f));
