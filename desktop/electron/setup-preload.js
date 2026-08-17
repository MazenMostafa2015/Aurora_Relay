"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("auroraSetup", {
  start: () => ipcRenderer.send("setup:probe"),
  complete: (config) => ipcRenderer.send("setup:complete", config),
  cancel: () => ipcRenderer.send("setup:cancel"),
  openExternal: (url) => ipcRenderer.invoke("app:open-external", url),
  onProgress: (callback) => {
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("setup:progress", listener);
    return () => ipcRenderer.removeListener("setup:progress", listener);
  },
});
