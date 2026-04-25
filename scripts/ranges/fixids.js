const fs = require('fs');
const path = require('path');
const dir = path.join(__dirname, 'cash_6max_100bb');
let fixed = 0;
for (const fname of fs.readdirSync(dir)) {
  if (!fname.endsWith('.json')) continue;
  const fp = path.join(dir, fname);
  const j = JSON.parse(fs.readFileSync(fp));
  if (!j.vs && j.scenario && j.scenario !== 'open') {
    const provider = j.id.split('_').pop();
    const newId = j.scenario.toLowerCase() + '_' + j.hero_pos + '_100bb_6max_' + provider;
    if (newId !== j.id) {
      console.log(j.id, '→', newId);
      j.id = newId;
      fs.writeFileSync(fp, JSON.stringify(j, null, 2));
      fixed++;
    }
  }
}
console.log('Fixed', fixed, 'IDs');
