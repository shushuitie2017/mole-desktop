// Mole Desktop — Electron 主进程
// 流程: 管理员守卫 → 取空闲端口 → 拉起 Flask server → 等就绪 → 开窗口
"use strict";

const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn, execFileSync } = require("child_process");
const net = require("net");
const http = require("http");
const path = require("path");
const fs = require("fs");
const os = require("os");

let serverProc = null;
let mainWindow = null;
let serverPort = null;

const STARTUP_TIMEOUT_MS = 30000;
const POLL_INTERVAL_MS = 300;

// ---------------- 文件日志 (诊断启动问题) ----------------
// 写到 %APPDATA%\Mole\mole-main.log，GUI 程序看不到控制台时靠它排查。
let _logFile = null;
function _logPath() {
    try { return path.join(app.getPath("userData"), "mole-main.log"); }
    catch (e) { return path.join(os.tmpdir(), "mole-main.log"); }
}
function log(...args) {
    const line = `[${new Date().toISOString()}] ${args.join(" ")}`;
    try { console.log(line); } catch (e) {}
    try {
        if (!_logFile) {
            _logFile = _logPath();
            fs.mkdirSync(path.dirname(_logFile), { recursive: true });  // userData 目录可能尚未创建
        }
        fs.appendFileSync(_logFile, line + "\n");
    } catch (e) {}
}
process.on("uncaughtException", (e) => log("UNCAUGHT", e && e.stack ? e.stack : String(e)));

// ---------------- 管理员守卫 ----------------
function isAdmin() {
    try {
        execFileSync("net", ["session"], { stdio: "ignore" });
        return true;
    } catch (e) {
        return false;
    }
}

// 按需提权：以管理员身份重启自身（由 UI「以管理员重启」按钮触发）。
// 注意：不在启动时强制调用——应用始终以普通权限直接打开，保证「永远能开」。
function relaunchAsAdmin() {
    log("user requested relaunch as admin");
    try {
        spawn("powershell.exe",
            ["-NoProfile", "-Command",
             `Start-Process -FilePath '${process.execPath}' -Verb RunAs`],
            { detached: true, stdio: "ignore", windowsHide: true }).unref();
        app.quit();
        return true;
    } catch (e) {
        log("relaunch as admin failed:", String(e));
        return false;
    }
}

// ---------------- 空闲端口 ----------------
function getFreePort() {
    return new Promise((resolve, reject) => {
        const srv = net.createServer();
        srv.listen(0, "127.0.0.1", () => {
            const p = srv.address().port;
            srv.close(() => resolve(p));
        });
        srv.on("error", reject);
    });
}

// ---------------- 拉起后端 ----------------
function serverExePath() {
    if (app.isPackaged) {
        return path.join(process.resourcesPath, "server", "server.exe");
    }
    return null; // dev: 用 python
}

function startServer(port) {
    const exe = serverExePath();
    const opts = { stdio: ["ignore", "pipe", "pipe"], windowsHide: true };
    if (exe) {
        log(`startServer exe=${exe} exists=${fs.existsSync(exe)} port=${port}`);
        serverProc = spawn(exe, ["--port", String(port)], opts);
    } else {
        const script = path.join(__dirname, "python", "server.py");
        const py = process.platform === "win32" ? "python" : "python3";
        log(`startServer (dev) py=${py} script=${script} port=${port}`);
        serverProc = spawn(py, [script, "--port", String(port)], opts);
    }
    serverProc.on("error", e => log("server spawn error:", String(e)));
    serverProc.stdout.on("data", d => log(`[server] ${d.toString().trim()}`));
    serverProc.stderr.on("data", d => log(`[server] ${d.toString().trim()}`));
    serverProc.on("exit", code => { log(`[server] exited ${code}`); serverProc = null; });
}

function waitForServer(port) {
    const start = Date.now();
    return new Promise((resolve, reject) => {
        const check = () => {
            if (Date.now() - start > STARTUP_TIMEOUT_MS) return reject(new Error("server startup timeout"));
            const req = http.get(`http://127.0.0.1:${port}/api/version`, res => {
                res.resume();
                if (res.statusCode === 200) resolve();
                else setTimeout(check, POLL_INTERVAL_MS);
            });
            req.on("error", () => setTimeout(check, POLL_INTERVAL_MS));
            req.setTimeout(2000, () => { req.destroy(); setTimeout(check, POLL_INTERVAL_MS); });
        };
        check();
    });
}

function killServer() {
    if (!serverProc) return;
    try {
        if (process.platform === "win32") {
            spawn("taskkill", ["/pid", String(serverProc.pid), "/f", "/t"], { windowsHide: true });
        } else {
            serverProc.kill("SIGTERM");
        }
    } catch (e) { console.error("killServer:", e); }
    serverProc = null;
}

// ---------------- 窗口 ----------------
function createMainWindow(port) {
    mainWindow = new BrowserWindow({
        width: 1400, height: 900, minWidth: 1000, minHeight: 640,
        title: "Mole",
        icon: app.isPackaged
            ? path.join(process.resourcesPath, "icon.ico")
            : path.join(__dirname, "assets", "icon.ico"),
        backgroundColor: "#0d1117",
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false,
        },
        show: false,
    });
    mainWindow.removeMenu();
    mainWindow.loadURL(`http://127.0.0.1:${port}`);
    mainWindow.once("ready-to-show", () => mainWindow.show());
    mainWindow.on("closed", () => { mainWindow = null; });
}

// ---------------- 启动序列 ----------------
async function launch() {
    try {
        serverPort = await getFreePort();
        log("got free port:", serverPort);
        startServer(serverPort);
        log("waiting for server ready...");
        await waitForServer(serverPort);
        log("server ready, creating window");
        createMainWindow(serverPort);
        log("window created");

        if (app.isPackaged) {
            try {
                const { initUpdater, checkForUpdates } = require("./updater");
                initUpdater(() => mainWindow);
                setTimeout(() => checkForUpdates(), 5000);
            } catch (e) { log("updater init failed:", e.message); }
        }
    } catch (err) {
        log("launch FAILED:", err && err.stack ? err.stack : String(err));
        // 启动失败时弹个原生错误框, 别让用户以为"点了没反应"
        try {
            const { dialog } = require("electron");
            dialog.showErrorBox("Mole 启动失败", String(err) + "\n\n日志: " + _logPath());
        } catch (e) {}
        app.quit();
    }
}

// ---------------- IPC ----------------
function setupIPC() {
    ipcMain.handle("app:version", () => app.getVersion());
    ipcMain.handle("app:isAdmin", () => isAdmin());
    ipcMain.handle("app:quit", () => app.quit());
    ipcMain.handle("app:restartAsAdmin", () => relaunchAsAdmin());
}

// ---------------- 生命周期 ----------------
// 始终以普通权限直接打开窗口（保证「永远能开」）。
// 需要管理员的操作按需提权：卸载用 ShellExecute runas；优化页提供「以管理员重启」按钮。
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
    app.quit();
} else {
    app.on("second-instance", () => {
        if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); }
    });

    app.whenReady().then(() => {
        log(`whenReady packaged=${app.isPackaged} admin=${isAdmin()}`);
        setupIPC();
        launch();
    });

    app.on("window-all-closed", () => { killServer(); if (process.platform !== "darwin") app.quit(); });
    app.on("before-quit", () => killServer());
    app.on("activate", () => { if (!mainWindow && serverPort) createMainWindow(serverPort); });
}
