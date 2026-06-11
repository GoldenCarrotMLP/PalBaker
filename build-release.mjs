import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

console.log("🚀 Starting PalBaker Mono-Repo Release Build...");

// 1. Install Python dependencies
console.log("\n🐍 Installing Python dependencies...");
execSync('pip install pyinstaller', { stdio: 'inherit', cwd: path.join(__dirname, 'pythoncli') });

// 2. Build Python Backend with PyInstaller
console.log("\n📦 Compiling Python Backend...");
execSync('pyinstaller palbaker_cli.spec --noconfirm', { stdio: 'inherit', cwd: path.join(__dirname, 'pythoncli') });

// 3. Stage backend for Tauri Resources
console.log("\n🚚 Staging backend into Tauri resources...");
const tauriResourcesDir = path.join(__dirname, 'palbaker-ui', 'src-tauri', 'resources', 'backend');
if (fs.existsSync(tauriResourcesDir)) {
    fs.rmSync(tauriResourcesDir, { recursive: true, force: true });
}
fs.mkdirSync(tauriResourcesDir, { recursive: true });
fs.cpSync(path.join(__dirname, 'pythoncli', 'dist', 'palbaker_cli'), tauriResourcesDir, { recursive: true });

// 4. Build Tauri App
console.log("\n🦀 Building Tauri Desktop App...");
execSync('pnpm tauri build', { stdio: 'inherit', cwd: path.join(__dirname, 'palbaker-ui') });

// 5. Gather Artifacts
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