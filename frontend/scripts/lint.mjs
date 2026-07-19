import { readdir, readFile } from "node:fs/promises";
import { extname, join, relative } from "node:path";

const root = process.cwd();
const extensions = new Set([".ts", ".tsx", ".css", ".mjs", ".json"]);
const ignored = new Set(["node_modules", ".next", "out", "coverage"]);
const issues = [];

async function walk(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (ignored.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      await walk(path);
      continue;
    }
    if (!extensions.has(extname(entry.name))) continue;
    const source = await readFile(path, "utf8");
    const displayPath = relative(root, path).replaceAll("\\", "/");
    source.split(/\r?\n/).forEach((line, index) => {
      if (/\s+$/.test(line)) issues.push(`${displayPath}:${index + 1} trailing whitespace`);
      if (line.includes("\t")) issues.push(`${displayPath}:${index + 1} tab character`);
      if (/console\.(log|debug)\s*\(/.test(line)) issues.push(`${displayPath}:${index + 1} debug console call`);
    });
  }
}

await walk(root);

const client = await readFile(join(root, "lib", "client.ts"), "utf8");
if (!client.includes("NEXT_PUBLIC_API_BASE_URL")) issues.push("lib/client.ts: API base must remain configurable");
if (!client.includes("FORCE_OFFLINE")) issues.push("lib/client.ts: static demo requires immediate offline mode");

if (issues.length) {
  console.error(issues.join("\n"));
  process.exitCode = 1;
} else {
  console.info("Lint passed: source hygiene and client-boundary checks are clean.");
}
