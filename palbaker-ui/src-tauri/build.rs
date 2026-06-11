use std::process::Command;

fn main() {
    let output = Command::new("git")
        .args(&["rev-list", "--count", "HEAD"])
        .output();
        
    let count = match output {
        Ok(out) if out.status.success() => {
            String::from_utf8_lossy(&out.stdout).trim().to_string()
        }
        _ => "2400".to_string(),
    };

    println!("cargo:rustc-env=PALBAKER_COMMIT_COUNT={}", count);
    tauri_build::build()
}
