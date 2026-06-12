import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

console.log("🚀 Starting PalBaker Mono-Repo Release Build...");

// 0a. Safely load .env variables into process.env before executing tasks
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
    console.log("📝 Loading signing credentials from .env file...");
    const envContent = fs.readFileSync(envPath, 'utf8');
    for (const line of envContent.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#')) {
            const index = trimmed.indexOf('=');
            if (index !== -1) {
                const key = trimmed.substring(0, index).trim();
                let value = trimmed.substring(index + 1).trim();
                
                // Clean surrounding quotes if present
                if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.substring(1, value.length - 1);
                }
                
                // Self-Healing Check: If they set the PATH variable to the base64 key content directly,
                // automatically map it to the correct variable in memory so the build succeeds!
                if (key === 'TAURI_SIGNING_PRIVATE_KEY_PATH' && value.startsWith('dW50cnVzdGVk')) {
                    process.env['TAURI_SIGNING_PRIVATE_KEY'] = value;
                    console.log("🩹 Auto-healed private key variable mapping.");
                } else {
                    process.env[key] = value;
                }
            }
        }
    }

    // Dual-Lookup Helper: If they configured a path, read the file and inject the key content!
    if (process.env.TAURI_SIGNING_PRIVATE_KEY_PATH && !process.env.TAURI_SIGNING_PRIVATE_KEY) {
        const keyPath = process.env.TAURI_SIGNING_PRIVATE_KEY_PATH;
        if (fs.existsSync(keyPath)) {
            process.env.TAURI_SIGNING_PRIVATE_KEY = fs.readFileSync(keyPath, 'utf8').trim();
            console.log("🔑 Successfully loaded private key content from configured path.");
        }
    }
}

// Helper function to recursively delete compiled python bytecode caches
function cleanPyCache(dir) {
  if (!fs.existsSync(dir)) return;
  const files = fs.readdirSync(dir);
  for (const file of files) {
    if (['venv', '.venv', 'env', '.env', 'build', 'dist', '.git', 'node_modules'].includes(file)) {
      continue;
    }

    const fullPath = path.join(dir, file);
    try {
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        if (file === '__pycache__') {
          fs.rmSync(fullPath, { recursive: true, force: true });
          console.log(`🧹 Cleaned bytecode cache: ${path.relative(__dirname, fullPath)}`);
        } else {
          cleanPyCache(fullPath);
        }
      }
    } catch (err) {
      console.warn(`⚠️ Warning: Skipping stat check for ${file} due to lock: ${err.message}`);
    }
  }
}

const pythoncliDir = path.join(__dirname, 'pythoncli');

// 0b. Pre-build cache cleanup to prevent stale python bytecode packages
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

// 6. Gather Artifacts & Generate Updater Manifest
console.log("\n📂 Gathering release artifacts and building update.json...");
const releaseDir = path.join(__dirname, 'release');
if (!fs.existsSync(releaseDir)) {
    fs.mkdirSync(releaseDir, { recursive: true });
}

const nsisDir = path.join(__dirname, 'palbaker-ui', 'src-tauri', 'target', 'release', 'bundle', 'nsis');
let signature = "";
let updateArtifactName = "";

const packageJson = JSON.parse(fs.readFileSync(path.join(__dirname, 'package.json'), 'utf8'));
const currentVersion = packageJson.version;

const currentExeName = `PalBaker_${currentVersion}_x64-setup.exe`;
const currentSigName = `${currentExeName}.sig`;

const currentZipName = `PalBaker_${currentVersion}_x64-setup.nsis.zip`;
const currentZipSigName = `${currentZipName}.sig`;

if (fs.existsSync(nsisDir)) {
    const files = fs.readdirSync(nsisDir);
    for (const file of files) {
        if (file.endsWith('.exe') || file.endsWith('.zip') || file.endsWith('.sig')) {
            fs.copyFileSync(path.join(nsisDir, file), path.join(releaseDir, file));
            console.log(`✅ Artifact ready: release/${file}`);
        }
    }
    
    // Resolve signature from either Tauri v2 (.exe.sig) or Tauri v1 (.zip.sig)
    if (fs.existsSync(path.join(nsisDir, currentSigName))) {
        signature = fs.readFileSync(path.join(nsisDir, currentSigName), 'utf8').trim();
        updateArtifactName = currentExeName;
        console.log("🔑 Found and loaded NSIS installer signature (.exe.sig)");
    } else if (fs.existsSync(path.join(nsisDir, currentZipSigName))) {
        signature = fs.readFileSync(path.join(nsisDir, currentZipSigName), 'utf8').trim();
        updateArtifactName = currentZipName;
        console.log("🔑 Found and loaded compressed ZIP package signature (.zip.sig)");
    }
} else {
    console.warn("⚠️ NSIS directory not found. Did Tauri build succeed?");
}

// 7. Auto-Generate update.json both inside /release/ and palbaker-ui/src-tauri/
if (signature && updateArtifactName) {
    const updaterJson = {
        version: currentVersion,
        notes: "Automated seamless update applied via PalBaker! ;3",
        pub_date: new Date().toISOString(),
        platforms: {
            "windows-x86_64": {
                signature: signature,
                url: `https://github.com/GoldenCarrotMLP/PalBaker/releases/latest/download/${updateArtifactName}`
            }
        }
    };
    
    // Save to the staging release directory
    fs.writeFileSync(path.join(releaseDir, 'update.json'), JSON.stringify(updaterJson, null, 2));
    
    // Overwrite the file inside palbaker-ui/src-tauri/
    const tauriUpdatePath = path.join(__dirname, 'palbaker-ui', 'src-tauri', 'update.json');
    fs.writeFileSync(tauriUpdatePath, JSON.stringify(updaterJson, null, 2));
    
    console.log(`✅ Generated and updated: ${path.relative(__dirname, tauriUpdatePath)}`);
} else {
    console.warn("\n⚠️  Warning: Tauri skipped generating the update files.");
    console.warn("   This happens when the private signing key environment variables are missing.");
    console.warn("   Verify that your .env file in the root directory contains valid paths.");
}

console.log("\n🎉 Release Build Complete! Upload setup files to GitHub Releases, then commit and push your update.json.");