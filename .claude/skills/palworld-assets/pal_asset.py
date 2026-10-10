"""Find, extract and decompile vanilla Palworld assets from Pal-Windows.pak.

Usage (run from anywhere):
  python pal_asset.py find <substring|regex> [--limit N]
  python pal_asset.py extract <pak path or wildcard> [--fmt json|raw] [--out DIR]
  python pal_asset.py uagui <pak path> [--out DIR]       # raw extract + UAssetGUI tojson
  python pal_asset.py tojson <file.uasset> [out.json]    # UAssetGUI on a local file (e.g. a cooked mod asset)

Pak paths look like: Pal/Content/Pal/Animation/Character/Monster/FireKirin/AM_FireKirin_Tossin_Loop
(no extension, exactly as listed in palbaker-cli/palworld_files_dir.txt).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CLI = os.path.join(REPO, "palbaker-cli")
DEPS = os.path.join(CLI, "deps")
CUE4PARSE = os.path.join(DEPS, "cue4parse.exe")
UAGUI = os.path.join(DEPS, "UAssetGUI.exe")
USMAP = os.path.join(DEPS, "Mappings.usmap")
INDEX = os.path.join(CLI, "palworld_files_dir.txt")
DEFAULT_OUT = os.path.join(tempfile.gettempdir(), "claude", "pal_assets")


def pak_path():
    with open(os.path.join(CLI, "manager_settings.json"), encoding="utf-8") as f:
        exe = json.load(f)["palworld_exe"]
    return os.path.join(os.path.dirname(exe), "Pal", "Content", "Paks", "Pal-Windows.pak")


def find(pattern, limit):
    rx = re.compile(pattern, re.IGNORECASE)
    hits = 0
    with open(INDEX, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if rx.search(line):
                print(line)
                hits += 1
                if hits >= limit:
                    print(f"... (limit {limit} reached)")
                    break
    if not hits:
        print("No matches.")


def cue4parse(patterns, fmt, out):
    os.makedirs(out, exist_ok=True)
    cmd = [CUE4PARSE, "--pak", pak_path(), "-o", out, "-m", USMAP,
           "-g", "GAME_UE5_1", "-f", fmt, "-y"]
    for p in patterns:
        cmd += ["-p", p]
    res = subprocess.run(cmd, capture_output=True, text=True)
    tail = (res.stdout or res.stderr).strip().splitlines()[-1:] or [""]
    if res.returncode != 0 or "No matches" in (res.stdout or ""):
        sys.exit(f"cue4parse failed: {tail[0]}")


def patterns_for(path, fmt):
    path = path.replace("\\", "/")
    if "*" in path or os.path.splitext(path)[1]:
        return [path]
    # raw needs both halves of the package; json wants the .uasset
    return [path + ".*"] if fmt == "raw" else [path + ".uasset"]


def tojson(uasset, out_json):
    res = subprocess.run([UAGUI, "tojson", uasset, out_json, "VER_UE5_1", USMAP],
                         capture_output=True, text=True)
    if res.returncode != 0 or not os.path.exists(out_json):
        sys.exit(f"UAssetGUI tojson failed: {res.stderr or res.stdout}")
    return out_json


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find"); f.add_argument("pattern"); f.add_argument("--limit", type=int, default=200)
    e = sub.add_parser("extract"); e.add_argument("path"); e.add_argument("--fmt", default="json", choices=["json", "raw"]); e.add_argument("--out", default=DEFAULT_OUT)
    u = sub.add_parser("uagui"); u.add_argument("path"); u.add_argument("--out", default=DEFAULT_OUT)
    t = sub.add_parser("tojson"); t.add_argument("uasset"); t.add_argument("out", nargs="?")
    a = ap.parse_args()

    if a.cmd == "find":
        find(a.pattern, a.limit)
    elif a.cmd == "extract":
        cue4parse(patterns_for(a.path, a.fmt), a.fmt, a.out)
        base = os.path.join(a.out, *a.path.replace("\\", "/").split("/"))
        print(base + (".json" if a.fmt == "json" else ".uasset"))
    elif a.cmd == "uagui":
        raw_out = os.path.join(a.out, "raw")
        cue4parse(patterns_for(a.path, "raw"), "raw", raw_out)
        base = os.path.join(raw_out, *a.path.replace("\\", "/").split("/"))
        print(tojson(base + ".uasset", base + ".uagui.json"))
    elif a.cmd == "tojson":
        out = a.out or os.path.splitext(a.uasset)[0] + ".uagui.json"
        print(tojson(a.uasset, out))


if __name__ == "__main__":
    main()
