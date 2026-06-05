# -*- coding: utf-8 -*-
"""
Mole Desktop — 后端构建脚本
PyInstaller --onedir 打包 Flask server，产出 python/dist/server/ 供 electron-builder。

用法: python scripts/build.py
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_DIR = ROOT / "python"
DIST = PY_DIR / "dist"
BUILD = PY_DIR / "build"
OUT_DIR = DIST / "server"          # PyInstaller --onedir 输出目录
OUT_EXE = OUT_DIR / "server.exe"
ICON = ROOT / "assets" / "icon.ico"


def step(msg):
    print("\n" + "=" * 56 + f"\n  {msg}\n" + "=" * 56)


def clean():
    step("1/3 清理旧产物")
    for d in (DIST, BUILD):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            print("  删除", d)
    for spec in PY_DIR.glob("*.spec"):
        spec.unlink()
        print("  删除", spec)


def build():
    step("2/3 PyInstaller --onedir 构建")
    sep = ";" if os.name == "nt" else ":"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir", "--name", "server", "--noconfirm", "--clean",
        "--add-data", f"templates{sep}templates",
        "--add-data", f"static{sep}static",
        "--hidden-import", "psutil",
        "--hidden-import", "winreg",
    ]
    if ICON.exists():
        cmd += ["--icon", str(ICON)]
    cmd.append("server.py")
    print("  " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(PY_DIR))
    if r.returncode != 0:
        print("  ❌ PyInstaller 失败")
        sys.exit(1)


def verify():
    step("3/3 验证产物")
    if not OUT_EXE.exists():
        print("  ❌ 找不到", OUT_EXE)
        sys.exit(1)
    total = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file())
    print(f"  ✓ {OUT_EXE}")
    print(f"  目录总大小: {total / 1024 / 1024:.1f} MB")
    print("\n  下一步: npm run dist  (出 NSIS 安装包)")


if __name__ == "__main__":
    print("Mole Desktop backend build")
    clean()
    build()
    verify()
