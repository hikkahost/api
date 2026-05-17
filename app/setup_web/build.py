import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = API_ROOT / "web"
DIST_DIR = Path(__file__).resolve().parent / "static" / "dist"
LOTTIE_DIR = WEB_DIR / "public" / "lottie"


def _compile_tgs() -> None:
    """Expand .tgs stickers under public/lottie/ to .json for the web player."""
    if not LOTTIE_DIR.is_dir():
        return
    for tgs in LOTTIE_DIR.glob("*.tgs"):
        out = tgs.with_suffix(".json")
        if out.is_file() and out.stat().st_mtime >= tgs.stat().st_mtime:
            continue
        with gzip.open(tgs, "rb") as src:
            payload = json.load(src)
        out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _needs_rebuild() -> bool:
    index = DIST_DIR / "index.html"
    if not index.exists():
        return True
    pkg = WEB_DIR / "package.json"
    if not pkg.exists():
        return False
    dist_mtime = index.stat().st_mtime
    for path in WEB_DIR.rglob("*"):
        if path.is_file() and path.stat().st_mtime > dist_mtime:
            return True
    return False


def ensure_web_build() -> None:
    if os.environ.get("SETUP_WEB_SKIP_BUILD", "").lower() in ("1", "true", "yes"):
        return
    if not WEB_DIR.exists():
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        _write_fallback_index()
        return
    if not _needs_rebuild():
        return
    npm = shutil.which("npm")
    if not npm:
        if (DIST_DIR / "index.html").exists():
            return
        raise RuntimeError(
            "Node.js/npm not found and setup_web static dist is missing. "
            "Install Node.js or set SETUP_WEB_SKIP_BUILD=1 with a prebuilt dist."
        )
    print("[setup_web] Building frontend...", flush=True)
    _compile_tgs()
    lock = WEB_DIR / "package-lock.json"
    install_cmd = [npm, "ci"] if lock.exists() else [npm, "install"]
    subprocess.run(install_cmd, cwd=WEB_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=WEB_DIR, check=True)
    if not (DIST_DIR / "index.html").exists():
        raise RuntimeError("Frontend build did not produce index.html")
    print("[setup_web] Frontend build complete.", flush=True)


def _write_fallback_index() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "index.html").write_text(
        "<!DOCTYPE html><html><head><meta charset=utf-8>"
        "<title>HikkaHost Setup</title></head>"
        "<body style='background:#0a0a0a;color:#e4e4e7;font-family:system-ui'>"
        "<h1>Setup Web</h1><p>Add <code>api/web</code> sources to build UI.</p>"
        "</body></html>"
    )
