// Mole Desktop — 自动更新 (electron-updater + GitHub Releases)
"use strict";
const { autoUpdater } = require("electron-updater");
const { ipcMain } = require("electron");

let getWin = () => null;

function send(channel, data) {
    const win = getWin();
    if (win && !win.isDestroyed()) win.webContents.send(channel, data);
}

function initUpdater(winGetter) {
    getWin = winGetter || getWin;
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on("update-available", info =>
        send("update:available", { version: info.version, notes: info.releaseNotes || "" }));
    autoUpdater.on("download-progress", p =>
        send("update:progress", { percent: p.percent }));
    autoUpdater.on("update-downloaded", info =>
        send("update:downloaded", { version: info.version }));
    autoUpdater.on("error", err => console.error("[updater]", err && err.message));

    ipcMain.handle("update:download", async () => {
        try { await autoUpdater.downloadUpdate(); return { ok: true }; }
        catch (e) { return { ok: false, error: e.message }; }
    });
    ipcMain.handle("update:install", () => autoUpdater.quitAndInstall(false, true));
}

function checkForUpdates() {
    autoUpdater.checkForUpdates().catch(e => console.log("[updater] check failed:", e.message));
}

module.exports = { initUpdater, checkForUpdates };
