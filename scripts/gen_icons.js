// Gera ícones PNG simples pro PWA usando canvas em Node + sharp se disponível.
// Fallback: gera SVG e instrui user a converter.
const fs = require('fs');
const path = require('path');

const ICONS_DIR = path.resolve(__dirname, '..', 'icons');
fs.mkdirSync(ICONS_DIR, { recursive: true });

// SVG inline com logo "🎯 LL" — clean e didático
const svgIcon = (size) => `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d0d0f"/>
      <stop offset="100%" stop-color="#1a2a30"/>
    </linearGradient>
  </defs>
  <rect width="${size}" height="${size}" rx="${size * 0.18}" fill="url(#bg)"/>
  <circle cx="${size/2}" cy="${size/2}" r="${size*0.32}" fill="none" stroke="#2dd4bf" stroke-width="${size*0.04}"/>
  <circle cx="${size/2}" cy="${size/2}" r="${size*0.18}" fill="none" stroke="#f0c419" stroke-width="${size*0.03}"/>
  <circle cx="${size/2}" cy="${size/2}" r="${size*0.06}" fill="#ed6a6a"/>
  <text x="${size/2}" y="${size*0.92}" text-anchor="middle" font-family="Arial Black, sans-serif" font-size="${size*0.18}" font-weight="900" fill="#2dd4bf">LeakLab</text>
</svg>`;

// Salva SVG (universal e válido como ícone PWA em browsers modernos)
fs.writeFileSync(path.join(ICONS_DIR, 'icon.svg'), svgIcon(512));

// Também salva 192 e 512 como SVG (renomeados — browsers modernos aceitam)
fs.writeFileSync(path.join(ICONS_DIR, 'icon-192.svg'), svgIcon(192));
fs.writeFileSync(path.join(ICONS_DIR, 'icon-512.svg'), svgIcon(512));

console.log('✓ Ícones SVG gerados em', ICONS_DIR);
console.log('  Pra PNG real: abre cada SVG no browser, screenshot, ou usa um conversor online');
console.log('  PWA instala sem PNG (browser usa SVG ou ícone default)');
