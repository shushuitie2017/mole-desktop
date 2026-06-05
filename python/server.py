# -*- coding: utf-8 -*-
"""
Mole Web UI - 后端 (Flask)

复刻 tw93/Mole (windows 分支) `mo clean` 默认清理逻辑的可视化控制台。
- 扫描: 测量每个清理类别的可回收空间 (只读, 绝不删除)
- 预览/清理: 删除选中类别 (复刻 Mole 的受保护路径 + 年龄阈值安全护栏)

仅覆盖 `mo clean` 无参数时的默认集合 (用户/浏览器/GPU/应用/开发者/应用残留缓存)。
不含 --system / --game-media / 孤立残留 / 需要管理员的项 (回收站, Prefetch, Windows Update 等)。

端口: 5005
"""
import io
import os
import re
import sys
import json
import time
import glob
import shutil
import ctypes
import fnmatch
import threading
import subprocess
from concurrent.futures import ThreadPoolExecutor

try:
    import psutil
except ImportError:
    psutil = None

try:
    import winreg
except ImportError:
    winreg = None

from flask import Flask, render_template, request, Response, jsonify

# 强制 UTF-8 输出 (Windows)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass

# PyInstaller 打包后 templates/static 解压到 sys._MEIPASS；开发时用脚本同目录
_BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__,
            template_folder=os.path.join(_BASE, "templates"),
            static_folder=os.path.join(_BASE, "static"))

APP_VERSION = "1.0.3"
PORT = 5005

# ============================================================================
# 安全护栏 (复刻 Mole lib/core/base.ps1 的 ProtectedPaths + Test-ProtectedPath)
# ============================================================================

def _norm(p):
    try:
        return os.path.normcase(os.path.abspath(p)).rstrip("\\")
    except Exception:
        return ""

_PROTECTED_ROOTS = [
    _norm(os.environ.get("WINDIR", r"C:\Windows")),
    _norm(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32")),
    _norm(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64")),
    _norm(os.environ.get("ProgramFiles", r"C:\Program Files")),
    _norm(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    _norm(os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                       "Microsoft", "Windows Defender")),
]

# 额外护栏: 用户主目录下绝不整体删除的文件夹 (默认 clean 也不碰它们)
_USERPROFILE = _norm(os.environ.get("USERPROFILE", ""))
_NEVER_WHOLE = set()
for _name in ("Documents", "Desktop", "Pictures", "Videos", "Music", "Downloads",
              "OneDrive", "AppData", "Saved Games", "Contacts", "Favorites"):
    if _USERPROFILE:
        _NEVER_WHOLE.add(_norm(os.path.join(_USERPROFILE, _name)))


def is_safe(path):
    """是否允许操作该路径 (复刻 Test-SafePath 的核心: 受保护路径检查 + 深度护栏)。"""
    if not path:
        return False
    full = _norm(path)
    if not full:
        return False
    # 不能是盘符根 (如 C:)
    parts = full.split("\\")
    if len(parts) < 3:  # 例: C:\X 至少要 3 段才算够深 (盘, 一级, 二级)
        return False
    # 受保护根目录 (等于或位于其下)
    for prot in _PROTECTED_ROOTS:
        if not prot:
            continue
        if full == prot or full.startswith(prot + "\\"):
            return False
    # 用户主目录根本身
    if _USERPROFILE and full == _USERPROFILE:
        return False
    # 绝不整体删除的用户文件夹本身 (其下的具体缓存子目录仍可删)
    if full in _NEVER_WHOLE:
        return False
    return True


# ============================================================================
# 体积测量
# ============================================================================

def dir_size(path):
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += dir_size(entry.path)
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        pass
    return total


def path_size(path):
    if not os.path.exists(path):
        return 0
    if os.path.isdir(path):
        return dir_size(path)
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


# ============================================================================
# 目标解析: 把一个 target 规格展开成一批具体待删路径
# 每个 target: {path, mode, days?, filter?, subs?}
#   mode = dir       -> 整个文件/目录 (path 可含通配符)
#   mode = contents  -> 目录下所有子项 (保留目录本身)
#   mode = old_files -> 目录内顶层、匹配 filter、且早于 days 天的文件
#   mode = glob      -> path 通配符匹配到的每个文件/目录
#   mode = profile_sub -> base 通配符下每个匹配目录里的 subs 子目录
# 返回 [(concrete_path, kind)]  kind in {"whole","file"}
# ============================================================================

def expand_target(t):
    mode = t.get("mode", "dir")
    raw = os.path.expandvars(t["path"])
    out = []

    if mode == "dir":
        for m in (glob.glob(raw) if ("*" in raw or "?" in raw) else [raw]):
            if os.path.exists(m):
                out.append((m, "whole"))

    elif mode == "contents":
        for base in (glob.glob(raw) if ("*" in raw or "?" in raw) else [raw]):
            if os.path.isdir(base):
                try:
                    for name in os.listdir(base):
                        out.append((os.path.join(base, name), "whole"))
                except OSError:
                    pass

    elif mode == "old_files":
        days = t.get("days", 7)
        flt = t.get("filter", "*")
        cutoff = time.time() - days * 86400
        for base in (glob.glob(raw) if ("*" in raw or "?" in raw) else [raw]):
            if os.path.isdir(base):
                try:
                    for name in os.listdir(base):
                        fp = os.path.join(base, name)
                        if os.path.isfile(fp) and fnmatch.fnmatch(name.lower(), flt.lower()):
                            try:
                                if os.path.getmtime(fp) < cutoff:
                                    out.append((fp, "file"))
                            except OSError:
                                pass
                except OSError:
                    pass

    elif mode == "glob":
        for m in glob.glob(raw):
            out.append((m, "whole"))

    elif mode == "profile_sub":
        subs = t.get("subs", [])
        for base in glob.glob(raw):
            if os.path.isdir(base):
                for sub in subs:
                    sp = os.path.join(base, sub)
                    if os.path.exists(sp):
                        out.append((sp, "whole"))

    # 安全过滤
    return [(p, k) for (p, k) in out if is_safe(p)]


def item_paths(item):
    paths = []
    for t in item["targets"]:
        paths.extend(expand_target(t))
    return paths


def measure_item(item):
    total = 0
    count = 0
    for p, _kind in item_paths(item):
        s = path_size(p)
        if s > 0:
            total += s
        count += 1
    return total, count


def clean_item(item, dry_run=True):
    freed = 0
    removed = 0
    failed = 0
    for p, _kind in item_paths(item):
        s = path_size(p)
        if dry_run:
            freed += s
            removed += 1
            continue
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p, ignore_errors=False)
            else:
                os.remove(p)
            freed += s
            removed += 1
        except Exception:
            failed += 1
    return freed, removed, failed


# ============================================================================
# 清理类别注册表 (复刻 mo clean 默认集合)
# label/desc: {en, zh, ja}
# ============================================================================

def L(en, zh, ja):
    return {"en": en, "zh": zh, "ja": ja}


CATEGORIES = [
    # ---------------- 用户基础 ----------------
    {"group": "user", "group_label": L("User Essentials", "用户基础", "ユーザー基本"), "items": [
        {"id": "user_temp", "label": L("User temp files", "用户临时文件", "ユーザー一時ファイル"),
         "desc": L("%TEMP% files older than 7 days", "%TEMP% 中超过 7 天的文件", "%TEMP% の7日以上前のファイル"),
         "targets": [{"path": r"%TEMP%", "mode": "old_files", "days": 7, "filter": "*"}]},
        {"id": "thumbnails", "label": L("Thumbnail / icon cache", "缩略图/图标缓存", "サムネイル/アイコンキャッシュ"),
         "desc": L("Explorer thumbcache & IconCache.db", "资源管理器缩略图与图标缓存", "エクスプローラーのサムネイル"),
         "targets": [
             {"path": r"%LOCALAPPDATA%\Microsoft\Windows\Explorer\thumbcache_*.db", "mode": "glob"},
             {"path": r"%LOCALAPPDATA%\IconCache.db", "mode": "dir"},
         ]},
        {"id": "recent", "label": L("Recent files / jump lists", "最近文件/跳转列表", "最近使ったファイル"),
         "desc": L("Recent shortcuts older than 30 days", "超过 30 天的最近快捷方式", "30日以上前のショートカット"),
         "targets": [
             {"path": r"%APPDATA%\Microsoft\Windows\Recent", "mode": "old_files", "days": 30, "filter": "*.lnk"},
             {"path": r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations", "mode": "old_files", "days": 30, "filter": "*"},
         ]},
        {"id": "wer", "label": L("Error reports & crash dumps", "错误报告与崩溃转储", "エラーレポート/クラッシュダンプ"),
         "desc": L("WER & CrashDumps contents", "WER 与 CrashDumps 目录内容", "WER と CrashDumps の中身"),
         "targets": [
             {"path": r"%LOCALAPPDATA%\Microsoft\Windows\WER", "mode": "contents"},
             {"path": r"%LOCALAPPDATA%\CrashDumps", "mode": "contents"},
         ]},
        {"id": "user_logs", "label": L("User log files", "用户日志文件", "ユーザーログ"),
         "desc": L("*.log older than 7 days", "超过 7 天的 *.log", "7日以上前の *.log"),
         "targets": [
             {"path": r"%LOCALAPPDATA%\Temp", "mode": "old_files", "days": 7, "filter": "*.log"},
             {"path": r"%APPDATA%", "mode": "old_files", "days": 7, "filter": "*.log"},
             {"path": r"%USERPROFILE%", "mode": "old_files", "days": 7, "filter": "*.log"},
         ]},
    ]},

    # ---------------- 浏览器缓存 ----------------
    {"group": "browser", "group_label": L("Browser Caches", "浏览器缓存", "ブラウザキャッシュ"), "items": [
        {"id": "chrome", "label": L("Google Chrome", "Google Chrome", "Google Chrome"),
         "desc": L("Cache, Code Cache, GPUCache, shaders", "缓存/代码缓存/GPU/着色器", "キャッシュ各種"),
         "targets": [{"path": r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Code Cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\GPUCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Service Worker\CacheStorage", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Google\Chrome\User Data\ShaderCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Google\Chrome\User Data\GrShaderCache", "mode": "dir"}]},
        {"id": "edge", "label": L("Microsoft Edge", "Microsoft Edge", "Microsoft Edge"),
         "desc": L("Cache, Code Cache, GPUCache, shaders", "缓存/代码缓存/GPU/着色器", "キャッシュ各種"),
         "targets": [{"path": r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\GPUCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Service Worker\CacheStorage", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Edge\User Data\ShaderCache", "mode": "dir"}]},
        {"id": "firefox", "label": L("Mozilla Firefox", "Mozilla Firefox", "Mozilla Firefox"),
         "desc": L("cache2, startupCache, shader-cache", "各配置文件缓存", "各プロファイルキャッシュ"),
         "targets": [{"path": r"%APPDATA%\Mozilla\Firefox\Profiles\*", "mode": "profile_sub",
                      "subs": ["cache2", "startupCache", "shader-cache"]}]},
        {"id": "brave", "label": L("Brave", "Brave", "Brave"),
         "desc": L("Default cache", "默认缓存", "既定キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\Cache", "mode": "dir"}]},
        {"id": "opera", "label": L("Opera", "Opera", "Opera"),
         "desc": L("Stable cache", "稳定版缓存", "安定版キャッシュ"),
         "targets": [{"path": r"%APPDATA%\Opera Software\Opera Stable\Cache", "mode": "dir"}]},
    ]},

    # ---------------- GPU 着色器缓存 ----------------
    {"group": "gpu", "group_label": L("GPU Shader Caches", "GPU 着色器缓存", "GPUシェーダーキャッシュ"), "items": [
        {"id": "nvidia", "label": L("NVIDIA", "NVIDIA", "NVIDIA"),
         "desc": L("DXCache, GLCache, NV_Cache", "DX/GL/NV 缓存", "DX/GL/NV キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\NVIDIA\DXCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\NVIDIA\GLCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\NVIDIA Corporation\NV_Cache", "mode": "dir"},
                     {"path": r"%TEMP%\NVIDIA Corporation\NV_Cache", "mode": "dir"}]},
        {"id": "amd", "label": L("AMD", "AMD", "AMD"),
         "desc": L("DXCache, GLCache, VkCache", "DX/GL/Vk 缓存", "DX/GL/Vk キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\AMD\DXCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\AMD\GLCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\AMD\VkCache", "mode": "dir"}]},
        {"id": "intel", "label": L("Intel", "Intel", "Intel"),
         "desc": L("ShaderCache", "着色器缓存", "シェーダーキャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Intel\ShaderCache", "mode": "dir"},
                     {"path": r"%APPDATA%\Intel\ShaderCache", "mode": "dir"}]},
        {"id": "directx", "label": L("DirectX", "DirectX", "DirectX"),
         "desc": L("D3DSCache, DirectX Shader Cache", "DX 着色器缓存", "DXシェーダーキャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\D3DSCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\DirectX Shader Cache", "mode": "dir"}]},
        {"id": "vulkan", "label": L("Vulkan", "Vulkan", "Vulkan"),
         "desc": L("Pipeline cache", "管线缓存", "パイプラインキャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\VulkanCache", "mode": "dir"}]},
    ]},

    # ---------------- 应用缓存 ----------------
    {"group": "appcache", "group_label": L("App Caches", "应用缓存", "アプリキャッシュ"), "items": [
        {"id": "spotify", "label": L("Spotify", "Spotify", "Spotify"), "desc": L("Data, Storage", "数据/存储", "Data/Storage"),
         "targets": [{"path": r"%LOCALAPPDATA%\Spotify\Data", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Spotify\Storage", "mode": "dir"}]},
        {"id": "discord", "label": L("Discord", "Discord", "Discord"), "desc": L("Cache, Code Cache, GPUCache", "缓存", "キャッシュ"),
         "targets": [{"path": r"%APPDATA%\discord\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\discord\Code Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\discord\GPUCache", "mode": "dir"}]},
        {"id": "slack", "label": L("Slack", "Slack", "Slack"), "desc": L("Cache, Code Cache, GPUCache", "缓存", "キャッシュ"),
         "targets": [{"path": r"%APPDATA%\Slack\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Slack\Code Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Slack\GPUCache", "mode": "dir"},
                     {"path": r"%APPDATA%\Slack\Service Worker\CacheStorage", "mode": "dir"}]},
        {"id": "teams", "label": L("Microsoft Teams", "Microsoft Teams", "Microsoft Teams"), "desc": L("Cache, blob, GPUCache, tmp", "缓存等", "キャッシュ等"),
         "targets": [{"path": r"%APPDATA%\Microsoft\Teams\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Microsoft\Teams\blob_storage", "mode": "dir"},
                     {"path": r"%APPDATA%\Microsoft\Teams\GPUCache", "mode": "dir"},
                     {"path": r"%APPDATA%\Microsoft\Teams\tmp", "mode": "dir"}]},
        {"id": "zoom", "label": L("Zoom", "Zoom", "Zoom"), "desc": L("data", "数据", "data"),
         "targets": [{"path": r"%APPDATA%\Zoom\data", "mode": "dir"}]},
        {"id": "adobe", "label": L("Adobe Creative Cloud", "Adobe 全家桶", "Adobe Creative Cloud"),
         "desc": L("Media Cache, Peak Files, app caches", "媒体缓存/峰值文件/应用缓存", "メディアキャッシュ等"),
         "targets": [{"path": r"%LOCALAPPDATA%\Adobe\*\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Adobe\Common\Media Cache Files", "mode": "dir"},
                     {"path": r"%APPDATA%\Adobe\Common\Peak Files", "mode": "dir"}]},
    ]},

    # ---------------- 开发者工具缓存 ----------------
    {"group": "dev", "group_label": L("Developer Caches", "开发者工具缓存", "開発ツールキャッシュ"), "items": [
        {"id": "npm", "label": L("npm cache", "npm 缓存", "npm キャッシュ"), "desc": L("%APPDATA%\\npm-cache", "%APPDATA%\\npm-cache", "%APPDATA%\\npm-cache"),
         "targets": [{"path": r"%APPDATA%\npm-cache", "mode": "dir"}]},
        {"id": "pnpm", "label": L("pnpm store", "pnpm store", "pnpm store"), "desc": L("pnpm content store", "pnpm 内容存储", "pnpm ストア"),
         "targets": [{"path": r"%LOCALAPPDATA%\pnpm\store", "mode": "dir"}]},
        {"id": "yarn", "label": L("Yarn cache", "Yarn 缓存", "Yarn キャッシュ"), "desc": L("Yarn\\Cache, .yarn\\cache", "Yarn 缓存", "Yarn キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Yarn\Cache", "mode": "dir"},
                     {"path": r"%USERPROFILE%\.yarn\cache", "mode": "dir"}]},
        {"id": "bun", "label": L("Bun cache", "Bun 缓存", "Bun キャッシュ"), "desc": L(".bun\\install\\cache", ".bun\\install\\cache", ".bun\\install\\cache"),
         "targets": [{"path": r"%USERPROFILE%\.bun\install\cache", "mode": "dir"}]},
        {"id": "node_build", "label": L("Node build caches", "Node 构建缓存", "Node ビルドキャッシュ"), "desc": L("node-gyp, electron, TypeScript", "node-gyp/electron/TS", "node-gyp/electron/TS"),
         "targets": [{"path": r"%LOCALAPPDATA%\node-gyp\Cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\electron\Cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\TypeScript", "mode": "dir"}]},
        {"id": "pip", "label": L("pip cache", "pip 缓存", "pip キャッシュ"), "desc": L("%LOCALAPPDATA%\\pip\\Cache", "pip 缓存", "pip キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\pip\Cache", "mode": "dir"}]},
        {"id": "poetry", "label": L("Poetry cache", "Poetry 缓存", "Poetry キャッシュ"), "desc": L("pypoetry\\Cache", "Poetry 缓存", "Poetry キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\pypoetry\Cache", "mode": "dir"}]},
        {"id": "jupyter", "label": L("Jupyter runtime", "Jupyter 运行时", "Jupyter ランタイム"), "desc": L("jupyter\\runtime", "Jupyter 运行时", "Jupyter ランタイム"),
         "targets": [{"path": r"%APPDATA%\jupyter\runtime", "mode": "dir"}]},
        {"id": "pytest", "label": L("pytest cache", "pytest 缓存", "pytest キャッシュ"), "desc": L(".pytest_cache", ".pytest_cache", ".pytest_cache"),
         "targets": [{"path": r"%USERPROFILE%\.pytest_cache", "mode": "dir"}]},
        {"id": "nuget", "label": L("NuGet cache", "NuGet 缓存", "NuGet キャッシュ"), "desc": L("v3-cache, plugins-cache", "v3/插件缓存", "v3/プラグイン"),
         "targets": [{"path": r"%LOCALAPPDATA%\NuGet\v3-cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\NuGet\plugins-cache", "mode": "dir"}]},
        {"id": "go_mod", "label": L("Go module cache", "Go 模块缓存", "Go モジュールキャッシュ"), "desc": L("go\\pkg\\mod\\cache", "Go 模块下载缓存", "Go モジュールキャッシュ"),
         "targets": [{"path": r"%USERPROFILE%\go\pkg\mod\cache", "mode": "dir"}]},
        {"id": "cargo", "label": L("Rust / Cargo", "Rust / Cargo", "Rust / Cargo"), "desc": L("registry cache, git, rustup downloads", "注册表/git/下载", "registry/git/downloads"),
         "targets": [{"path": r"%USERPROFILE%\.cargo\registry\cache", "mode": "dir"},
                     {"path": r"%USERPROFILE%\.cargo\git\checkouts", "mode": "dir"},
                     {"path": r"%USERPROFILE%\.rustup\downloads", "mode": "dir"}]},
        {"id": "gradle", "label": L("Gradle caches", "Gradle 缓存", "Gradle キャッシュ"), "desc": L("daemon, wrapper dists", "守护进程/wrapper", "daemon/wrapper"),
         "targets": [{"path": r"%USERPROFILE%\.gradle\daemon", "mode": "dir"},
                     {"path": r"%USERPROFILE%\.gradle\wrapper\dists", "mode": "dir"}]},
        {"id": "jetbrains", "label": L("JetBrains IDEs", "JetBrains 系列", "JetBrains IDE"), "desc": L("caches, index, tmp", "缓存/索引/临时", "キャッシュ/索引/tmp"),
         "targets": [{"path": r"%LOCALAPPDATA%\JetBrains\*", "mode": "profile_sub", "subs": ["caches", "index", "tmp"]},
                     {"path": r"%APPDATA%\JetBrains\*", "mode": "profile_sub", "subs": ["caches", "index", "tmp"]}]},
        {"id": "vscode", "label": L("VS Code", "VS Code", "VS Code"), "desc": L("Cache, CachedData, GPUCache", "缓存类", "キャッシュ類"),
         "targets": [{"path": r"%APPDATA%\Code\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Code\CachedData", "mode": "dir"},
                     {"path": r"%APPDATA%\Code\CachedExtensionVSIXs", "mode": "dir"},
                     {"path": r"%APPDATA%\Code\Code Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Code\GPUCache", "mode": "dir"}]},
        {"id": "zed", "label": L("Zed editor", "Zed 编辑器", "Zed エディタ"), "desc": L("cache", "缓存", "キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Zed\cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Zed\cache", "mode": "dir"}]},
    ]},

    # ---------------- 应用残留缓存 ----------------
    {"group": "apps", "group_label": L("Application Leftovers", "应用残留缓存", "アプリ残留キャッシュ"), "items": [
        {"id": "office", "label": L("Microsoft Office", "Microsoft Office", "Microsoft Office"),
         "desc": L("OfficeFileCache, Outlook RoamCache", "Office/Outlook 缓存", "Office/Outlook キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Microsoft\Office\16.0\OfficeFileCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Office\16.0\Wef", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Outlook\RoamCache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Microsoft\Outlook\Offline Address Books", "mode": "dir"}]},
        {"id": "onedrive", "label": L("OneDrive logs", "OneDrive 日志", "OneDrive ログ"),
         "desc": L("logs older than 7 days", "超过 7 天的日志", "7日以上前のログ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Microsoft\OneDrive\logs", "mode": "old_files", "days": 7, "filter": "*"}]},
        {"id": "gdrive", "label": L("Google Drive", "Google Drive", "Google Drive"),
         "desc": L("DriveFS logs & tmp", "DriveFS 日志/临时", "DriveFS ログ/tmp"),
         "targets": [{"path": r"%LOCALAPPDATA%\Google\DriveFS\Logs", "mode": "old_files", "days": 7, "filter": "*"},
                     {"path": r"%LOCALAPPDATA%\Google\DriveFS", "mode": "old_files", "days": 0, "filter": "*.tmp"}]},
        {"id": "autodesk", "label": L("Autodesk", "Autodesk", "Autodesk"), "desc": L("app caches", "应用缓存", "アプリキャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Autodesk\*\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Autodesk\*\cache", "mode": "dir"}]},
        {"id": "epic", "label": L("Epic Games Launcher", "Epic 启动器", "Epic ランチャー"), "desc": L("webcache, logs", "网络缓存/日志", "webcache/ログ"),
         "targets": [{"path": r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\webcache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\EpicGamesLauncher\Saved\Logs", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\EpicGamesLauncher\Launcher\Saved\webcache", "mode": "dir"}]},
        {"id": "ea", "label": L("EA App / Origin", "EA / Origin", "EA / Origin"), "desc": L("cache", "缓存", "キャッシュ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Electronic Arts\EA Desktop\cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Origin\*\cache", "mode": "dir"}]},
        {"id": "gog", "label": L("GOG Galaxy", "GOG Galaxy", "GOG Galaxy"), "desc": L("webcache", "网络缓存", "webcache"),
         "targets": [{"path": r"%LOCALAPPDATA%\GOG.com\Galaxy\webcache", "mode": "dir"}]},
        {"id": "ubisoft", "label": L("Ubisoft Connect", "Ubisoft Connect", "Ubisoft Connect"), "desc": L("cache, logs", "缓存/日志", "キャッシュ/ログ"),
         "targets": [{"path": r"%LOCALAPPDATA%\Ubisoft Game Launcher\cache", "mode": "dir"},
                     {"path": r"%LOCALAPPDATA%\Ubisoft Game Launcher\logs", "mode": "dir"}]},
        {"id": "battlenet", "label": L("Battle.net", "战网 Battle.net", "Battle.net"), "desc": L("Cache, Logs", "缓存/日志", "キャッシュ/ログ"),
         "targets": [{"path": r"%APPDATA%\Battle.net\Cache", "mode": "dir"},
                     {"path": r"%APPDATA%\Battle.net\Logs", "mode": "dir"}]},
    ]},
]

# id -> item 索引
ITEM_INDEX = {}
for _g in CATEGORIES:
    for _it in _g["items"]:
        ITEM_INDEX[_it["id"]] = _it


# ============================================================================
# 路由
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info")
def api_info():
    drive = os.environ.get("SystemDrive", "C:") + "\\"
    try:
        usage = shutil.disk_usage(drive)
        total, used, free = usage.total, usage.used, usage.free
    except Exception:
        total = used = free = 0
    try:
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        is_admin = False
    # 仅返回结构 (不含体积)
    groups = []
    for g in CATEGORIES:
        groups.append({
            "group": g["group"],
            "group_label": g["group_label"],
            "items": [{"id": it["id"], "label": it["label"], "desc": it["desc"]} for it in g["items"]],
        })
    return jsonify({
        "drive": drive, "total": total, "used": used, "free": free,
        "is_admin": is_admin,
        "windows": os.environ.get("OS", "Windows"),
        "groups": groups,
    })


def _sse(data):
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


@app.route("/api/scan")
def api_scan():
    def gen():
        grand_size = 0
        grand_count = 0
        for g in CATEGORIES:
            for it in g["items"]:
                size, count = measure_item(it)
                grand_size += size
                grand_count += count
                yield _sse({"type": "item", "id": it["id"], "group": g["group"],
                            "size": size, "count": count})
        yield _sse({"type": "done", "total_size": grand_size, "total_count": grand_count})
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/clean")
def api_clean():
    ids_raw = request.args.get("ids", "")
    dry = request.args.get("dry", "1") != "0"
    ids = [i for i in ids_raw.split(",") if i in ITEM_INDEX]

    def gen():
        total_freed = 0
        total_removed = 0
        total_failed = 0
        for iid in ids:
            it = ITEM_INDEX[iid]
            freed, removed, failed = clean_item(it, dry_run=dry)
            total_freed += freed
            total_removed += removed
            total_failed += failed
            yield _sse({"type": "item", "id": iid, "freed": freed,
                        "removed": removed, "failed": failed, "dry": dry})
        # 重新读取剩余空间
        drive = os.environ.get("SystemDrive", "C:") + "\\"
        try:
            free = shutil.disk_usage(drive).free
        except Exception:
            free = 0
        yield _sse({"type": "done", "total_freed": total_freed,
                    "total_removed": total_removed, "total_failed": total_failed,
                    "dry": dry, "free": free})
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ============================================================================
# STATUS — 实时系统监控 (复刻 cmd/status, 用 psutil)
# ============================================================================

_net_prev = {"t": 0.0, "sent": 0, "recv": 0}


def _fmt_uptime(seconds):
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    out = []
    if d:
        out.append(f"{d}d")
    if h or d:
        out.append(f"{h}h")
    out.append(f"{m}m")
    return " ".join(out)


def _health_score(cpu, mem_pct, disks, swap_pct):
    score = 100
    issues = []
    if cpu > 90:
        score -= 30; issues.append("High CPU")
    elif cpu > 70:
        score -= 15; issues.append("Elevated CPU")
    if mem_pct > 90:
        score -= 25; issues.append("High Memory")
    elif mem_pct > 80:
        score -= 12; issues.append("Elevated Memory")
    for d in disks:
        if d["pct"] > 95:
            score -= 20; issues.append(f"Disk {d['device']}: Critical")
        elif d["pct"] > 85:
            score -= 10; issues.append(f"Disk {d['device']}: Low")
    if swap_pct > 80:
        score -= 10; issues.append("High Swap")
    score = max(0, score)
    if score >= 90:
        msg = "Excellent"
    elif score >= 70:
        msg = "Good"
    elif score >= 50:
        msg = "Fair"
    else:
        msg = "Poor"
    return score, msg, issues


@app.route("/api/status")
def api_status():
    if psutil is None:
        return jsonify({"error": "psutil not installed"}), 500

    cpu_total = psutil.cpu_percent(interval=0.4)
    cpu_cores = psutil.cpu_percent(interval=0.0, percpu=True)
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()

    disks = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
            disks.append({"device": part.device.rstrip("\\"),
                          "used": u.used, "total": u.total, "pct": u.percent})
        except (PermissionError, OSError):
            continue

    # 网络速率 (基于上次采样差值)
    now = time.time()
    nio = psutil.net_io_counters()
    up_rate = down_rate = 0
    if _net_prev["t"]:
        dt = now - _net_prev["t"]
        if dt > 0:
            up_rate = max(0, (nio.bytes_sent - _net_prev["sent"]) / dt)
            down_rate = max(0, (nio.bytes_recv - _net_prev["recv"]) / dt)
    _net_prev.update({"t": now, "sent": nio.bytes_sent, "recv": nio.bytes_recv})

    # Top 进程
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            procs.append({"pid": info["pid"], "name": info["name"] or "?",
                          "cpu": info["cpu_percent"] or 0.0,
                          "mem": info["memory_percent"] or 0.0})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    top = [p for p in procs if p["cpu"] > 0.1 or p["mem"] > 0.1][:6]

    swap_pct = sm.percent if sm.total > 0 else 0
    health, hmsg, issues = _health_score(cpu_total, vm.percent, disks, swap_pct)

    try:
        boot = psutil.boot_time()
        uptime = time.time() - boot
    except Exception:
        uptime = 0
    try:
        host = os.environ.get("COMPUTERNAME", "PC")
    except Exception:
        host = "PC"

    return jsonify({
        "health": health, "health_msg": hmsg, "issues": issues,
        "host": host, "uptime": _fmt_uptime(uptime),
        "cpu_total": cpu_total, "cpu_cores": cpu_cores, "cpu_count": len(cpu_cores),
        "mem": {"used": vm.used, "total": vm.total, "pct": vm.percent},
        "swap": {"used": sm.used, "total": sm.total, "pct": swap_pct},
        "disks": disks,
        "net": {"up": up_rate, "down": down_rate,
                "sent_total": nio.bytes_sent, "recv_total": nio.bytes_recv},
        "procs": top,
    })


# ============================================================================
# PURGE — 项目构建产物清理 (复刻 bin/purge.ps1)
# ============================================================================

PURGE_ARTIFACTS = ["node_modules", "vendor", ".venv", "venv", "__pycache__",
                   ".pytest_cache", "target", "build", "dist", ".next", ".nuxt",
                   ".turbo", ".parcel-cache", "obj", ".gradle"]
PURGE_MARKERS = ["package.json", "composer.json", "Cargo.toml", "go.mod", "pom.xml",
                 "build.gradle", "requirements.txt", "pyproject.toml"]
PURGE_CONFIG = os.path.join(os.environ.get("USERPROFILE", ""), ".config", "mole", "purge_paths.txt")
PURGE_DEFAULT_ROOTS = [r"%USERPROFILE%\Documents", r"%USERPROFILE%\Projects",
                       r"%USERPROFILE%\Code", r"%USERPROFILE%\Development",
                       r"%USERPROFILE%\workspace", r"%USERPROFILE%\Desktop",
                       r"D:\Projects", r"D:\Code", r"D:\Development"]


def purge_roots():
    roots = []
    if os.path.isfile(PURGE_CONFIG):
        try:
            with open(PURGE_CONFIG, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        roots.append(os.path.expandvars(line))
        except OSError:
            pass
    if not roots:
        roots = [os.path.expandvars(r) for r in PURGE_DEFAULT_ROOTS]
    return [r for r in roots if os.path.isdir(r)]


def find_projects(root, max_depth=4):
    """在 root 下递归(限深)找含 marker 的项目目录, 跳过产物/.git 内部。"""
    found = []

    def walk(path, depth):
        if depth > max_depth:
            return
        try:
            entries = list(os.scandir(path))
        except (OSError, PermissionError):
            return
        names = {e.name for e in entries}
        is_project = any(m in names for m in PURGE_MARKERS)
        if is_project:
            found.append(path)
            # 项目内只收集产物, 不再深入其子目录找新项目
            return
        for e in entries:
            if not e.is_dir(follow_symlinks=False):
                continue
            if e.name in PURGE_ARTIFACTS or e.name == ".git":
                continue
            walk(e.path, depth + 1)

    walk(root, 0)
    return found


@app.route("/api/purge/scan")
def api_purge_scan():
    def gen():
        roots = purge_roots()
        yield _sse({"type": "roots", "roots": roots})
        seen = set()
        total = 0
        cutoff = time.time() - 7 * 86400
        for root in roots:
            for proj in find_projects(root):
                if proj in seen:
                    continue
                seen.add(proj)
                artifacts = []
                psize = 0
                try:
                    for name in os.listdir(proj):
                        if name in PURGE_ARTIFACTS:
                            ap = os.path.join(proj, name)
                            if os.path.isdir(ap) and is_safe(ap):
                                s = dir_size(ap)
                                artifacts.append({"name": name, "path": ap, "size": s})
                                psize += s
                except OSError:
                    pass
                if not artifacts:
                    continue
                try:
                    recent = os.path.getmtime(proj) > cutoff
                except OSError:
                    recent = False
                total += psize
                yield _sse({"type": "project", "name": os.path.basename(proj),
                            "path": proj, "size": psize, "recent": recent,
                            "artifacts": artifacts})
        yield _sse({"type": "done", "total_size": total})
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/purge/clean", methods=["POST"])
def api_purge_clean():
    body = request.get_json(force=True, silent=True) or {}
    paths = body.get("paths", [])
    dry = bool(body.get("dry", True))

    def gen():
        total_freed = 0
        removed = 0
        failed = 0
        for p in paths:
            if not is_safe(p) or os.path.basename(p) not in PURGE_ARTIFACTS:
                yield _sse({"type": "item", "path": p, "freed": 0, "ok": False})
                failed += 1
                continue
            s = path_size(p)
            if dry:
                total_freed += s
                removed += 1
                yield _sse({"type": "item", "path": p, "freed": s, "ok": True, "dry": True})
                continue
            try:
                shutil.rmtree(p, ignore_errors=False)
                total_freed += s
                removed += 1
                yield _sse({"type": "item", "path": p, "freed": s, "ok": True})
            except Exception:
                failed += 1
                yield _sse({"type": "item", "path": p, "freed": 0, "ok": False})
        yield _sse({"type": "done", "total_freed": total_freed,
                    "removed": removed, "failed": failed, "dry": dry})
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ============================================================================
# ANALYZE — 磁盘空间浏览器 (复刻 cmd/analyze)
# ============================================================================

ANALYZE_CLEANABLE = set(PURGE_ARTIFACTS) | {".idea", ".vs", "bin"}
ANALYZE_SKIP = {"$Recycle.Bin", "System Volume Information", "Windows",
                "Program Files", "Program Files (x86)", "ProgramData",
                "Recovery", "Config.Msi"}


@app.route("/api/analyze")
def api_analyze():
    path = request.args.get("path") or os.environ.get("USERPROFILE", "C:\\")
    path = os.path.abspath(os.path.expandvars(path))
    if not os.path.isdir(path):
        return jsonify({"error": "not a directory", "path": path}), 400

    children = []
    try:
        entries = list(os.scandir(path))
    except (OSError, PermissionError) as e:
        return jsonify({"error": str(e), "path": path}), 403

    dir_entries = [e for e in entries if e.is_dir(follow_symlinks=False) and e.name not in ANALYZE_SKIP]
    file_entries = [e for e in entries if e.is_file(follow_symlinks=False)]

    # 并行计算各子目录大小
    def measure(e):
        try:
            return e.name, e.path, dir_size(e.path), True
        except Exception:
            return e.name, e.path, 0, True

    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as ex:
        for name, p, size, isdir in ex.map(measure, dir_entries):
            children.append({"name": name, "path": p, "size": size, "is_dir": True,
                             "cleanable": name in ANALYZE_CLEANABLE})

    for e in file_entries:
        try:
            children.append({"name": e.name, "path": e.path,
                             "size": e.stat(follow_symlinks=False).st_size,
                             "is_dir": False, "cleanable": False})
        except OSError:
            continue

    children.sort(key=lambda x: x["size"], reverse=True)
    total = sum(c["size"] for c in children)
    parent = os.path.dirname(path.rstrip("\\")) if len(path.rstrip("\\").split("\\")) > 1 else None
    if parent == path:
        parent = None
    return jsonify({"path": path, "parent": parent, "total": total, "entries": children})


@app.route("/api/analyze/delete", methods=["POST"])
def api_analyze_delete():
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("path", "")
    if not is_safe(target) or not os.path.exists(target):
        return jsonify({"ok": False, "error": "protected or missing"}), 400
    size = path_size(target)
    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        return jsonify({"ok": True, "freed": size})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/analyze/open", methods=["POST"])
def api_analyze_open():
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("path", "")
    if os.path.exists(target):
        try:
            subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(target)])
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)})
    return jsonify({"ok": False, "error": "missing"}), 404


# ============================================================================
# OPTIMIZE — 系统优化 (复刻 bin/optimize.ps1)
# ============================================================================

OPTIMIZE_ACTIONS = [
    {"id": "dns", "label": L("Flush DNS cache", "刷新 DNS 缓存", "DNSキャッシュ更新"),
     "admin": False, "kind": "tweak", "cmd": ["ipconfig", "/flushdns"]},
    {"id": "iconcache", "label": L("Rebuild icon/thumbnail cache", "重建图标/缩略图缓存", "アイコンキャッシュ再構築"),
     "admin": False, "kind": "repair", "special": "iconcache"},
    {"id": "storecache", "label": L("Reset Windows Store cache", "重置应用商店缓存", "ストアキャッシュ初期化"),
     "admin": False, "kind": "repair", "cmd": ["wsreset.exe"]},
    {"id": "winsock", "label": L("Reset Winsock catalog", "重置 Winsock", "Winsock リセット"),
     "admin": True, "kind": "tweak", "cmd": ["netsh", "winsock", "reset"]},
    {"id": "arp", "label": L("Clear ARP cache", "清除 ARP 缓存", "ARPキャッシュ消去"),
     "admin": True, "kind": "tweak", "cmd": ["netsh", "interface", "ip", "delete", "arpcache"]},
    {"id": "startup", "label": L("Check startup programs", "检查启动项", "スタートアップ確認"),
     "admin": False, "kind": "check", "special": "startup"},
    {"id": "diskhealth", "label": L("Check disk health", "检查磁盘健康", "ディスク健康確認"),
     "admin": False, "kind": "check", "special": "diskhealth"},
    {"id": "sfc", "label": L("System File Checker (sfc /scannow)", "系统文件检查 (sfc)", "システムファイルチェック"),
     "admin": True, "kind": "repair", "cmd": ["sfc", "/scannow"], "slow": True},
]
OPT_INDEX = {a["id"]: a for a in OPTIMIZE_ACTIONS}


def _is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


@app.route("/api/optimize/actions")
def api_optimize_actions():
    admin = _is_admin()
    out = []
    for a in OPTIMIZE_ACTIONS:
        out.append({"id": a["id"], "label": a["label"], "admin": a["admin"],
                    "kind": a["kind"], "slow": a.get("slow", False),
                    "available": (not a["admin"]) or admin})
    return jsonify({"is_admin": admin, "actions": out})


def _run_optimize(action, dry):
    label = action["label"]["en"]
    if action["admin"] and not _is_admin():
        return {"ok": False, "msg": "requires admin (skipped)"}
    if dry:
        return {"ok": True, "msg": "would run", "dry": True}

    special = action.get("special")
    try:
        if special == "startup":
            count = 0
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
                count = winreg.QueryInfoKey(k)[1]
                winreg.CloseKey(k)
            except Exception:
                pass
            return {"ok": True, "msg": f"{count} startup entries (HKCU)"}
        if special == "diskhealth":
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "(Get-PhysicalDisk).HealthStatus -join ','"],
                               capture_output=True, text=True, timeout=30)
            return {"ok": True, "msg": (r.stdout or "").strip() or "Healthy"}
        if special == "iconcache":
            base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Explorer")
            n = 0
            for pat in ("iconcache_*.db", "thumbcache_*.db"):
                for f in glob.glob(os.path.join(base, pat)):
                    try:
                        os.remove(f); n += 1
                    except OSError:
                        pass
            ic = os.path.expandvars(r"%LOCALAPPDATA%\IconCache.db")
            if os.path.exists(ic):
                try:
                    os.remove(ic); n += 1
                except OSError:
                    pass
            return {"ok": True, "msg": f"cleared {n} cache files (restart Explorer to rebuild)"}
        # 普通命令
        cmd = action["cmd"]
        timeout = 600 if action.get("slow") else 60
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        ok = r.returncode == 0
        out = (r.stdout or r.stderr or "").strip().splitlines()
        return {"ok": ok, "msg": (out[-1] if out else f"exit {r.returncode}")}
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": "timeout"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


@app.route("/api/optimize/run")
def api_optimize_run():
    ids = [i for i in request.args.get("ids", "").split(",") if i in OPT_INDEX]
    dry = request.args.get("dry", "1") != "0"

    def gen():
        ok_n = fail_n = 0
        for iid in ids:
            res = _run_optimize(OPT_INDEX[iid], dry)
            if res.get("ok"):
                ok_n += 1
            else:
                fail_n += 1
            yield _sse({"type": "item", "id": iid, "ok": res.get("ok"),
                        "msg": res.get("msg", ""), "dry": dry})
        yield _sse({"type": "done", "ok": ok_n, "fail": fail_n, "dry": dry})
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ============================================================================
# UNINSTALL — 应用清单 + 卸载 (复刻 bin/uninstall.ps1)
# ============================================================================

UNINSTALL_PROTECTED = [
    "microsoft windows", "windows feature experience", "microsoft edge",
    "microsoft edge webview2", "windows security", "microsoft visual c++",
    "microsoft .net", ".net desktop runtime", "microsoft update health",
    "nvidia graphics driver", "amd software", "intel",
]


def _is_protected_app(name):
    n = (name or "").lower()
    return any(p in n for p in UNINSTALL_PROTECTED)


def _enum_uninstall_key(root, subkey, view):
    apps = []
    try:
        base = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | view)
    except OSError:
        return apps
    n = winreg.QueryInfoKey(base)[0]
    for i in range(n):
        try:
            sk = winreg.EnumKey(base, i)
            k = winreg.OpenKey(base, sk)
        except OSError:
            continue

        def g(name):
            try:
                return winreg.QueryValueEx(k, name)[0]
            except OSError:
                return None
        name = g("DisplayName")
        unstr = g("UninstallString")
        if not name or not unstr:
            winreg.CloseKey(k); continue
        if g("SystemComponent") == 1:
            winreg.CloseKey(k); continue
        if _is_protected_app(name):
            winreg.CloseKey(k); continue
        size_kb = g("EstimatedSize") or 0
        try:
            size = int(size_kb) * 1024
        except (ValueError, TypeError):
            size = 0
        apps.append({
            "name": str(name), "uninstall": str(unstr),
            "size": size, "publisher": str(g("Publisher") or ""),
            "version": str(g("DisplayVersion") or ""),
            "date": str(g("InstallDate") or ""),
            "location": str(g("InstallLocation") or ""),
            "source": "registry",
        })
        winreg.CloseKey(k)
    winreg.CloseKey(base)
    return apps


@app.route("/api/uninstall/list")
def api_uninstall_list():
    if winreg is None:
        return jsonify({"error": "winreg unavailable"}), 500
    apps = []
    apps += _enum_uninstall_key(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                                winreg.KEY_WOW64_64KEY)
    apps += _enum_uninstall_key(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                                winreg.KEY_WOW64_32KEY)
    apps += _enum_uninstall_key(winreg.HKEY_CURRENT_USER,
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0)
    # 去重 (按名称+版本)
    dedup = {}
    for a in apps:
        key = (a["name"].lower(), a["version"])
        if key not in dedup:
            dedup[key] = a
    out = sorted(dedup.values(), key=lambda x: x["size"], reverse=True)
    return jsonify({"is_admin": _is_admin(), "count": len(out), "apps": out})


def _split_cmdline(unstr):
    """把卸载命令拆成 (可执行文件, 参数)。"""
    s = unstr.strip()
    if s.startswith('"'):
        end = s.find('"', 1)
        if end != -1:
            return s[1:end], s[end + 1:].strip()
    low = s.lower()
    i = low.find(".exe")
    if i != -1:
        return s[:i + 4], s[i + 4:].strip()
    parts = s.split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


@app.route("/api/uninstall/run", methods=["POST"])
def api_uninstall_run():
    """通过 ShellExecute(runas) 启动卸载程序, 触发 UAC 提权, 由用户在原生界面确认。"""
    body = request.get_json(force=True, silent=True) or {}
    unstr = body.get("uninstall", "")
    if not unstr:
        return jsonify({"ok": False, "error": "no uninstall string"}), 400

    m = re.search(r"\{[0-9A-Fa-f\-]+\}", unstr)
    if "msiexec" in unstr.lower() and m:
        exe, params = "msiexec.exe", "/x " + m.group(0)
    else:
        exe, params = _split_cmdline(unstr)

    try:
        # nShowCmd=1 (SW_SHOWNORMAL); "runas" 触发 UAC 提权
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params or None, None, 1)
        if int(ret) > 32:
            return jsonify({"ok": True})
        # 常见错误码: 1223=用户取消 UAC, 5=拒绝访问, 2=文件未找到
        msgs = {1223: "用户取消了提权 / UAC cancelled", 5: "访问被拒绝 / access denied",
                2: "卸载程序未找到 / uninstaller not found", 31: "无关联程序"}
        return jsonify({"ok": False, "error": msgs.get(int(ret), f"ShellExecute 返回 {ret}")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================================
# 版本信息
# ============================================================================

@app.route("/api/version")
def api_version():
    # 兼作 Electron 启动健康检查端点 (轻量、快)
    return jsonify({"version": APP_VERSION, "is_admin": _is_admin()})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mole Desktop backend")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    print(f" * Mole backend  ->  http://127.0.0.1:{args.port}", flush=True)
    app.run(host="127.0.0.1", port=args.port, threaded=True, debug=False)
