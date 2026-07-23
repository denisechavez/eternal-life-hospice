import fs from 'fs';
import path from 'path';

const source = path.resolve('../../website/elh-preview/assets/img/elh-logo-h2-cream.png');
const targetDir = path.resolve('public/images');
const target = path.join(targetDir, 'logo.png');

if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

if (fs.existsSync(source)) {
  fs.copyFileSync(source, target);
  console.log(`Copied logo from ${source} to ${target}`);
} else {
  console.error(`Source logo not found at ${source}`);
}
