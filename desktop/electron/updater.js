"use strict";

const { autoUpdater } = require("electron-updater");
const { dialog } = require("electron");

class AppUpdater {
  constructor(window) {
    this.window = window;
    this.enabled = Boolean(process.env.AURORA_UPDATE_FEED);
    this.updateAvailable = false;
    this.downloaded = false;
    if (!this.enabled || !window) return;
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;
    autoUpdater.on("update-available", async () => {
      this.updateAvailable = true;
      const result = await dialog.showMessageBox(window, {
        type: "info",
        title: "Update available",
        message: "A signed Aurora Relay update is ready to download.",
        buttons: ["Download", "Later"],
        defaultId: 0,
      });
      if (result.response === 0) await autoUpdater.downloadUpdate();
    });
    autoUpdater.on("update-downloaded", async () => {
      this.downloaded = true;
      const result = await dialog.showMessageBox(window, {
        type: "info",
        title: "Update ready",
        message: "The update has been verified and is ready to install.",
        buttons: ["Install and restart", "Later"],
        defaultId: 0,
      });
      if (result.response === 0) autoUpdater.quitAndInstall();
    });
    autoUpdater.on("error", (error) => {
      console.error("Updater error", error);
      window.webContents.send("desktop:update-status", { status: "error", message: error.message });
    });
  }

  checkForUpdates() {
    if (this.enabled && process.platform !== "linux") return autoUpdater.checkForUpdates();
    return Promise.resolve(null);
  }

  getStatus() {
    return { enabled: this.enabled, updateAvailable: this.updateAvailable, downloaded: this.downloaded };
  }
}

module.exports = { AppUpdater };
