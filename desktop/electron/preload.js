"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("auroraDesktop", {
  getStatus: () => ipcRenderer.invoke("app:get-status"),
  minimizeToTray: () => ipcRenderer.invoke("app:minimize-to-tray"),
  quit: () => ipcRenderer.invoke("app:quit"),
  openExternal: (url) => ipcRenderer.invoke("app:open-external", url),
});
