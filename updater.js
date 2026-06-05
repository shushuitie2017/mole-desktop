// Mole Desktop — 自动更新 (electron-updater + GitHub Releases)
"use strict";
const { autoUpdater } = require("electron-updater");
const { app, ipcMain } = require("electron");

let getWin = () => null;
let wired = false;

function send(channel, data) {
    const win = getWin();
    if (win && !win.isDestroyed()) win.webContents.send(channel, data);
}

// 注册渲染进程可调用的 IPC（始终调用，dev 下也可用，只是返回 dev 标记）
function setupUpdateIpc(winGetter) {
    if (winGetter) getWin = winGetter;
    if (wired) return;
    wired = true;

    ipcMain.handle("update:check", async () => {
        if (!app.isPackaged) return { ok: false, dev: true };
        try {
            const r = await autoUpdater.checkForUpdates();
            return { ok: true, version: r && r.updateInfo ? r.updateInfo.version : null };
        } catch (e) {
            send("update:error", { msg: String(e && e.message || e) });
            return { ok: false, error: String(e && e.message || e) };
        }
    });
    ipcMain.handle("update:download", async () => {
        try { await autoUpdater.downloadUpdate(); return { ok: true }; }
        catch (e) { return { ok: false, error: String(e && e.message || e) }; }
    });
    ipcMain.handle("update:install", () => autoUpdater.quitAndInstall(false, true));
}

// 配置 feed + 事件（仅打包态）
function initUpdater(winGetter) {
    if (winGetter) getWin = winGetter;
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on("update-available", info =>
        send("update:available", { version: info.version, notes: info.releaseNotes || "" }));
    autoUpdater.on("update-not-available", info =>
        send("update:none", { version: info && info.version }));
    autoUpdater.on("download-progress", p =>
        send("update:progress", { percent: p.percent }));
    autoUpdater.on("update-downloaded", info =>
        send("update:downloaded", { version: info.version }));
    autoUpdater.on("error", err =>
        send("update:error", { msg: String(err && err.message || err) }));
}

function checkForUpdates() {
    if (!app.isPackaged) return;
    autoUpdater.checkForUpdates().catch(e => console.log("[updater] check failed:", e.message));
}

module.exports = { initUpdater, setupUpdateIpc, checkForUpdates };
