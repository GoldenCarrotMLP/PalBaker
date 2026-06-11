import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, '..');

// 1. Retrieve the active Git commit count
let commitCount = 2400;
try {
  const countStr = execSync('git rev-list --count HEAD', { encoding: 'utf8', cwd: repoRoot }).trim();
  commitCount = parseInt(countStr, 10);
} catch (e) {
  console.warn("⚠️ Failed to read git commit count. Defaulting to 2400.");
}

// If running inside the pre-commit hook, we increment by 1 because the upcoming commit hasn't landed yet
const isPreCommit = process.argv.includes('--pre-commit');
const targetCount = isPreCommit ? commitCount + 1 : commitCount;

// Apply your exact mathematical semver formatting
const major = Math.floor(targetCount / 1000);
const minor = Math.floor((targetCount % 1000) / 100);
const patch = targetCount % 100;
const versionStr = `${major}.${minor}.${patch}`;

console.log(`📌 Target Commit Count: ${targetCount} -> Unified Version: ${versionStr}`);

const filesToUpdate = [
  { path: path.join(repoRoot, 'package.json'), type: 'json' },
  { path: path.join(repoRoot, 'palbaker-ui', 'package.json'), type: 'json' },
  { path: path.join(repoRoot, 'palbaker-ui', 'src-tauri', 'tauri.conf.json'), type: 'json' }
];

for (const file of filesToUpdate) {
  if (fs.existsSync(file.path)) {
    try {
      const raw = fs.readFileSync(file.path, 'utf8');
      const data = JSON.parse(raw);
      
      data.version = versionStr;
      
      fs.writeFileSync(file.path, JSON.stringify(data, null, 2) + '\n', 'utf8');
      console.log(`✅ Updated version in: ${path.relative(repoRoot, file.path)}`);

      // If inside pre-commit, automatically stage the modified files
      if (isPreCommit) {
        execSync(`git add "${file.path}"`, { cwd: repoRoot });
      }
    } catch (err) {
      console.error(`❌ Failed to update ${file.path}:`, err);
    }
  } else {
    console.warn(`⚠️ File not found: ${file.path}`);
  }
}