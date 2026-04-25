const fs = require('fs');
const path = require('path');
const file = path.resolve(__dirname, '..', 'src', 'leaklab.html');
const html = fs.readFileSync(file, 'utf-8');
// Extrai TODOS os <script>...</script> blocks
const re = /<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g;
let blocks = [];
let m;
while ((m = re.exec(html)) !== null) blocks.push(m[1]);
console.log('Found ' + blocks.length + ' script blocks');
for (let i = 0; i < blocks.length; i++) {
  try {
    new Function(blocks[i]);
    console.log('  block ' + i + ': OK (' + blocks[i].length + ' chars)');
  } catch (e) {
    console.log('  block ' + i + ': SYNTAX ERROR - ' + e.message);
    const lineMatch = e.stack.match(/<anonymous>:(\d+)/);
    if (lineMatch) {
      const ln = parseInt(lineMatch[1]);
      const lines = blocks[i].split('\n');
      console.log('  Line ' + ln + ':');
      for (let j = Math.max(0, ln - 3); j < Math.min(lines.length, ln + 2); j++) {
        console.log('    ' + (j + 1) + ': ' + lines[j]);
      }
    }
  }
}
