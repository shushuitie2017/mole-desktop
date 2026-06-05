// Mole Desktop — Electron 主进程
// 流程: 管理员守卫 → 取空闲端口 → 拉起 Flask server → 等就绪 → 开窗口
"use strict";

const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn, execFileSync } = require("child_process");
const net = require("net");
const http = require("http");
const path = require("path");

let serverProc = null;
let mainWindow = null;
let serverPort = null;

const STARTUP_TIMEOUT_MS = 30000;
const POLL_INTERVAL_MS = 300;

// ---------------- 管理员守卫 ----------------
function isAdmin() {
    try {
        // net session 仅管理员可成功
        execFileSync("net", ["session"], { stdio: "ignore" });
        return true;
    } catch (e) {
        return false;
    }
}

// 非管理员且为打包态 → 以管理员重启自身后退出
function ensureAdminOrRelaunch() {
    if (!app.isPackaged) return true;          // dev 模式不强制提权
    if (isAdmin()) return true;
    try {
        spawn("powershell.exe",
            ["-NoProfile", "-Command",
             `Start-Process -FilePath '${process.execPath}' -Verb RunAs`],
            { detached: true, stdio: "ignore", windowsHide: true }).unref();
    } catch (e) {
        console.error("relaunch as admin failed:", e);
    }
    app.quit();
    return false;
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
        serverProc = spawn(exe, ["--port", String(port)], opts);
    } else {
        const script = path.join(__dirname, "python", "server.py");
        const py = process.platform === "win32" ? "python" : "python3";
        serverProc = spawn(py, [script, "--port", String(port)], opts);
    }
    serverProc.stdout.on("data", d => console.log(`[server] ${d.toString().trim()}`));
    serverProc.stderr.on("data", d => console.log(`[server] ${d.toString().trim()}`));
    serverProc.on("exit", code => { console.log(`[server] exited ${code}`); serverProc = null; });
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
        console.log("port:", serverPort);
        startServer(serverPort);
        await waitForServer(serverPort);
        console.log("server ready");
        createMainWindow(serverPort);

        if (app.isPackaged) {
            try {
                const { initUpdater, checkForUpdates } = require("./updater");
                initUpdater(() => mainWindow);
                setTimeout(() => checkForUpdates(), 5000);
            } catch (e) { console.error("updater init:", e.message); }
        }
    } catch (err) {
        console.error("launch failed:", err);
        app.quit();
    }
}

// ---------------- IPC ----------------
function setupIPC() {
    ipcMain.handle("app:version", () => app.getVersion());
    ipcMain.handle("app:isAdmin", () => isAdmin());
    ipcMain.handle("app:quit", () => app.quit());
}

// ---------------- 生命周期 ----------------
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
    app.quit();
} else {
    app.on("second-instance", () => {
        if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); }
    });

    app.whenReady().then(() => {
        if (!ensureAdminOrRelaunch()) return;
        setupIPC();
        launch();
    });

    app.on("window-all-closed", () => { killServer(); if (process.platform !== "darwin") app.quit(); });
    app.on("before-quit", () => killServer());
    app.on("activate", () => { if (!mainWindow && serverPort) createMainWindow(serverPort); });
}
