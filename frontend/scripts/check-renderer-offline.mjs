import { readdir, readFile } from "node:fs/promises";
import { resolve, relative } from "node:path";

const root = resolve(import.meta.dirname, "..");
const scanRoots = [resolve(root, "client"), resolve(root, "dist")];
const forbiddenPatterns = [
  { label: "Manus storage URL", pattern: /\/manus-storage\//i },
  { label: "hosted Forge endpoint", pattern: /forge\.butterfly-effect\.dev/i },
  { label: "Umami analytics endpoint", pattern: /umami(?:\.is|\.aurora-relay)/i },
  { label: "remote analytics loader", pattern: /analytics[^\w-]*(?:script|loader|url)/i },
];

async function filesIn(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return filesIn(path);
    return entry.name.endsWith(".map") ? [] : [path];
  }));
  return files.flat();
}

const violations = [];
for (const scanRoot of scanRoots) {
  for (const file of await filesIn(scanRoot)) {
    const text = await readFile(file, "utf8").catch(() => "");
    for (const { label, pattern } of forbiddenPatterns) {
      if (pattern.test(text)) violations.push(`${relative(root, file)}: ${label}`);
    }
  }
}

if (violations.length > 0) {
  console.error("Offline renderer guard failed:\n" + violations.map((item) => `- ${item}`).join("\n"));
  process.exit(1);
}

console.log("Offline renderer guard passed: no prohibited remote asset or analytics references found.");
