import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, '..');
const gitHooksDir = path.join(repoRoot, '.git', 'hooks');

if (!fs.existsSync(gitHooksDir)) {
  console.warn("⚠️ Not a git repository or .git/hooks directory not found. Skipping hook setup.");
  process.exit(0);
}

const preCommitHookPath = path.join(gitHooksDir, 'pre-commit');
const hookContent = `#!/bin/sh
# PalBaker Auto-Version Git Hook
node scripts/update-version.mjs --pre-commit
`;

try {
  fs.writeFileSync(preCommitHookPath, hookContent, { mode: 0o755 });
  console.log("✅ Successfully installed PalBaker pre-commit auto-versioning hook!");
} catch (err) {
  console.error("❌ Failed to write pre-commit hook:", err);
}