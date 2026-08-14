/* Minimal build: minify HTML/CSS/JS into dist/, copy binary assets as-is. */
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, 'src');
const OUT = path.join(__dirname, 'dist');

function rmrf(p) { fs.rmSync(p, { recursive: true, force: true }); }
function mkdir(p) { fs.mkdirSync(p, { recursive: true }); }

function minifyCSS(css) {
  return css
    .replace(/\/\*[\s\S]*?\*\//g, '')          // comments
    .replace(/\s*([{}:;,>~+])\s*/g, '$1')      // space round operators
    .replace(/;}/g, '}')
    .replace(/\s+/g, ' ')
    .replace(/\s*\n\s*/g, '')
    .trim();
}

function minifyJS(js) {
  return js
    .split('\n')
    .map(l => l.replace(/(^|[^:'"])\/\/(?![^'"]*['"]\s*[,)]).*$/, (m, p1) =>
      // only strip a trailing line comment when it is not inside a string/url
      (l.includes('http://') || l.includes('https://')) ? m : p1))
    .join('\n')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n').map(l => l.trim()).filter(Boolean).join('\n');
}

function minifyHTML(html) {
  return html
    .replace(/<!--(?!\[if)[\s\S]*?-->/g, '')   // comments (keep conditional)
    .replace(/>\s*\n\s*</g, '><')
    .replace(/\n\s+/g, '\n')
    .replace(/\n+/g, '\n')
    .trim();
}

rmrf(OUT); mkdir(OUT);

function walk(dir, rel = '') {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const from = path.join(dir, entry.name);
    const relPath = path.join(rel, entry.name);
    const to = path.join(OUT, relPath);
    if (entry.isDirectory()) { mkdir(to); walk(from, relPath); continue; }

    const ext = path.extname(entry.name).toLowerCase();
    if (ext === '.css') fs.writeFileSync(to, minifyCSS(fs.readFileSync(from, 'utf8')));
    else if (ext === '.js') fs.writeFileSync(to, minifyJS(fs.readFileSync(from, 'utf8')));
    else if (ext === '.html') fs.writeFileSync(to, minifyHTML(fs.readFileSync(from, 'utf8')));
    else fs.copyFileSync(from, to);
  }
}
walk(SRC);

// stray working file from the font fetch — never ship it
rmrf(path.join(OUT, 'mont.css'));

let total = 0;
(function size(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) size(p); else total += fs.statSync(p).size;
  }
})(OUT);
console.log('dist built —', (total / 1024).toFixed(0) + ' KB total');
