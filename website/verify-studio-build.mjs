import { readFileSync, statSync } from "node:fs";
import { dirname, resolve, relative, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";

export function verifyStudioBuild(directory) {
  const base = resolve(directory);
  const requireFile = (name) => {
    const target = resolve(base, name);
    const inside = relative(base, target);
    if (inside.startsWith("..") || isAbsolute(inside) || !statSync(target).isFile()) {
      throw new Error(`Invalid Studio build asset: ${name}`);
    }
    return target;
  };
  const html = readFileSync(requireFile("index.html"), "utf8");
  const manifest = JSON.parse(readFileSync(requireFile(".vite/manifest.json"), "utf8"));
  const entry = manifest["index.html"];
  if (!entry?.isEntry || !entry.file || !html.includes(`/studio/${entry.file}`)) {
    throw new Error("Studio login entry or /studio/ asset base is missing");
  }
  for (const [name, record] of Object.entries(manifest)) {
    if (!record.file) throw new Error(`Studio manifest entry has no file: ${name}`);
    for (const asset of [record.file, ...(record.css || []), ...(record.assets || [])]) {
      requireFile(asset);
    }
    for (const dependency of [...(record.imports || []), ...(record.dynamicImports || [])]) {
      if (!manifest[dependency]) {
        throw new Error(`Studio manifest dependency is missing: ${dependency}`);
      }
    }
  }
  return Object.keys(manifest).length;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const base = process.argv[2] || resolve(dirname(fileURLToPath(import.meta.url)), "studio-build");
  console.log(`Studio build verified: ${verifyStudioBuild(base)} manifest entries`);
}
