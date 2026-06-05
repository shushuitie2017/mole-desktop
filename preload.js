// Mole Desktop — preload: 通过 contextBridge 暴露安全 API
"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
    platform: process.platform,
    getVersion: () => ipcRenderer.invoke("app:version"),
    isAdmin: () => ipcRenderer.invoke("app:isAdmin"),
    quit: () => ipcRenderer.invoke("app:quit"),
    restartAsAdmin: () => ipcRenderer.invoke("app:restartAsAdmin"),
    // 自动更新
    checkForUpdate: () => ipcRenderer.invoke("update:check"),
    downloadUpdate: () => ipcRenderer.invoke("update:download"),
    installUpdate: () => ipcRenderer.invoke("update:install"),
    onUpdateAvailable: (cb) => ipcRenderer.on("update:available", (_, d) => cb(d)),
    onUpdateNone: (cb) => ipcRenderer.on("update:none", (_, d) => cb(d)),
    onUpdateProgress: (cb) => ipcRenderer.on("update:progress", (_, d) => cb(d)),
    onUpdateDownloaded: (cb) => ipcRenderer.on("update:downloaded", (_, d) => cb(d)),
    onUpdateError: (cb) => ipcRenderer.on("update:error", (_, d) => cb(d)),
});
