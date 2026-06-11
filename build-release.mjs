import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

console.log("🚀 Starting PalBaker Mono-Repo Release Build...");

// Helper function to recursively delete compiled python bytecode caches
function cleanPyCache(dir) {
  if (!fs.existsSync(dir)) return;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      if (file === '__pycache__') {
        fs.rmSync(fullPath, { recursive: true, force: true });
        console.log(`🧹 Cleaned bytecode cache: ${path.relative(__dirname, fullPath)}`);
      } else {
        cleanPyCache(fullPath);
      }
    }
  }
}

const pythoncliDir = path.join(__dirname, 'pythoncli');

// 0. Pre-build cache cleanup to prevent stale python bytecode packages
console.log("\n🧹 Cleaning old build caches and temporary python files...");
fs.rmSync(path.join(pythoncliDir, 'build'), { recursive: true, force: true });
fs.rmSync(path.join(pythoncliDir, 'dist'), { recursive: true, force: true });
cleanPyCache(pythoncliDir);

// 1. Synchronize version files across the workspace using current git counts
console.log("\n📌 Synchronizing version files across workspace...");
execSync('node scripts/update-version.mjs', { stdio: 'inherit' });

// 2. Install Python dependencies
console.log("\n🐍 Installing Python dependencies...");
execSync('pip install pyinstaller', { stdio: 'inherit', cwd: pythoncliDir });

// 3. Build Python Backend with PyInstaller (Using --clean to force non-stale builds!)
console.log("\n📦 Compiling Python Backend...");
execSync('pyinstaller palbaker_cli.spec --noconfirm --clean', { stdio: 'inherit', cwd: pythoncliDir });

// 4. Stage backend for Tauri Resources
console.log("\n🚚 Staging backend into Tauri resources...");
const tauriResourcesDir = path.join(__dirname, 'palbaker-ui', 'src-tauri', 'resources', 'backend');
if (fs.existsSync(tauriResourcesDir)) {
    fs.rmSync(tauriResourcesDir, { recursive: true, force: true });
}
fs.mkdirSync(tauriResourcesDir, { recursive: true });
fs.cpSync(path.join(pythoncliDir, 'dist', 'palbaker_cli'), tauriResourcesDir, { recursive: true });

// 5. Build Tauri App
console.log("\n🦀 Building Tauri Desktop App...");
execSync('pnpm tauri build', { stdio: 'inherit', cwd: path.join(__dirname, 'palbaker-ui') });

// 6. Gather Artifacts
console.log("\n📂 Gathering release artifacts...");
const releaseDir = path.join(__dirname, 'release');
if (!fs.existsSync(releaseDir)) {
    fs.mkdirSync(releaseDir, { recursive: true });
}

const nsisDir = path.join(__dirname, 'palbaker-ui', 'src-tauri', 'target', 'release', 'bundle', 'nsis');
if (fs.existsSync(nsisDir)) {
    const files = fs.readdirSync(nsisDir).filter(f => f.endsWith('.exe'));
    for (const file of files) {
        fs.copyFileSync(path.join(nsisDir, file), path.join(releaseDir, file));
        console.log(`✅ Artifact ready: release/${file}`);
    }
} else {
    console.warn("⚠️ NSIS directory not found. Did Tauri build succeed?");
}

console.log("\n🎉 Release Build Complete! Your binaries are in the /release folder.");