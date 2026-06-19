// dump-files.mjs
import fs from "fs";
import path from "path";
import { execSync } from "child_process";
import { isBinary } from "istextorbinary";

const rootDir = process.cwd();
const outFile = path.join(rootDir, "dump.txt");

function getTrackedFiles() {
  const output = execSync("git ls-files", {
    cwd: rootDir,
    encoding: "utf8",
  });

  return output
    .split("\n")
    .map(l => l.trim())
    .filter(Boolean);
}

function main() {
  const files = getTrackedFiles();

  fs.writeFileSync(outFile, "=== Dump of Git‑tracked non‑binary files ===\n\n");

  for (const rel of files) {

    // 🚫 Ignore anything inside the deps folder
    let bool = rel.split("/").map( item => ["deps", "flet_docs_dump","node_modules", "package-lock","icons","Cargo", "pnpm-lock","Assets"].includes(item.split(".")[0])).some(Boolean);
    
    if (bool) continue;
    console.log(rel)
    const full = path.join(rootDir, rel);

    // Skip anything that is not a real file (submodules, directories, etc.)
    const stat = fs.statSync(full);
    if (!stat.isFile()) continue;

    const buffer = fs.readFileSync(full);

    if (isBinary(null, buffer)) continue;

    const content = buffer.toString("utf8");

    fs.appendFileSync(outFile, rel + "\n");
    fs.appendFileSync(outFile, "```\n");
    fs.appendFileSync(outFile, content + "\n");
    fs.appendFileSync(outFile, "```\n\n");
  }

  console.log(`Dump written to ${outFile}`);
}

main();
