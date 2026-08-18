"use strict";

const { app, BrowserWindow, dialog, ipcMain, Menu, net, Tray, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const netModule = require("node:net");
const path = require("node:path");
const { AppUpdater } = require("./updater");
const { SetupWizard } = require("./setup-wizard");
const { DesktopCredentialVault } = require("./vault");

let mainWindow;
let tray;
let backendProcess;
let backendPort;
let updater;
let isQuitting = false;
let vaultStatus = { state: "locked", backend: "initializing", fallback: false, reason: "Credential protection is initializing." };

async function provisionConnectorVault() {
  const userData = app.getPath("userData");
  const legacyPath = process.env.AURORA_CONNECTOR_VAULT_PATH;
  const vault = DesktopCredentialVault.withElectron({ userData, legacyKeyPaths: legacyPath ? [legacyPath] : [] });
  const provisioned = await vault.provisionBackendKey();
  vaultStatus = provisioned.status;
  process.env.AURORA_CONNECTOR_VAULT_BACKEND = vaultStatus.backend;
  process.env.AURORA_CONNECTOR_VAULT_FALLBACK = vaultStatus.fallback ? "1" : "0";
  if (provisioned.key) {
    process.env.AURORA_CONNECTOR_VAULT_KEY = provisioned.key;
    delete process.env.AURORA_CONNECTOR_VAULT_LOCKED;
    delete process.env.AURORA_CONNECTOR_VAULT_LOCK_REASON;
  } else {
    delete process.env.AURORA_CONNECTOR_VAULT_KEY;
    process.env.AURORA_CONNECTOR_VAULT_LOCKED = "1";
    process.env.AURORA_CONNECTOR_VAULT_LOCK_REASON = vaultStatus.reason || "Credential protection is unavailable.";
  }
}

function appendBackendStartupLog(stream, data) {
  try {
    const logDirectory = path.join(app.getPath("userData"), "logs");
    fs.mkdirSync(logDirectory, { recursive: true });
    const message = Buffer.isBuffer(data) ? data.toString("utf8") : String(data);
    fs.appendFileSync(path.join(logDirectory, "backend-startup.log"), `[${new Date().toISOString()}] ${stream}: ${message}`);
  } catch {
    // Startup diagnostics must never block the local backend lifecycle.
  }
}

function backendExecutable() {
  if (!app.isPackaged) return process.env.AURORA_PYTHON || "python3";
  const binary = process.platform === "win32" ? "aurora-backend.exe" : "aurora-backend";
  return path.join(process.resourcesPath, "backend", binary);
}

function backendArgs() {
  return app.isPackaged ? [] : [path.join(__dirname, "..", "..", "backend", "run.py")];
}

function choosePort() {
  return new Promise((resolve, reject) => {
    const server = netModule.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

function spawnBackend() {
  if (backendProcess) return;
  const executable = backendExecutable();
  const env = {
    ...process.env,
    AURORA_PORT: String(backendPort),
    AURORA_BIND_HOST: "127.0.0.1",
    AURORA_APP_DATA_DIR: app.getPath("userData"),
    AURORA_FRONTEND_DIR: app.isPackaged ? path.join(process.resourcesPath, "frontend") : path.join(__dirname, "..", "..", "frontend-dist"),
    PYTHONUNBUFFERED: "1",
  };
  backendProcess = spawn(executable, backendArgs(), {
    cwd: app.isPackaged ? process.resourcesPath : path.join(__dirname, "..", ".."),
    env,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
  backendProcess.stdout?.on("data", (data) => {
    appendBackendStartupLog("stdout", data);
    console.log(`[backend] ${data}`.toString().trimEnd());
  });
  backendProcess.stderr?.on("data", (data) => {
    appendBackendStartupLog("stderr", data);
    console.error(`[backend] ${data}`.toString().trimEnd());
  });
  backendProcess.once("error", (error) => {
    appendBackendStartupLog("spawn-error", `${error.name}: ${error.message}\n`);
    console.error("Backend process error", error);
    dialog.showErrorBox("Aurora Relay backend unavailable", `The local service could not start: ${error.message}`);
  });
  backendProcess.once("exit", (code, signal) => {
    appendBackendStartupLog("exit", `code=${code ?? "none"} signal=${signal ?? "none"}\n`);
    console.log(`Backend exited code=${code ?? "none"} signal=${signal ?? "none"}`);
    backendProcess = undefined;
  });
}

function stopBackend() {
  if (!backendProcess) return;
  backendProcess.kill();
  backendProcess = undefined;
}

async function backendReady(timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await net.fetch(`http://127.0.0.1:${backendPort}/health`);
      if (response.ok) return true;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  return false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 900,
    minHeight: 640,
    backgroundColor: "#0b1013",
    show: false,
    title: "Aurora Relay",
    icon: path.join(__dirname, "resources", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: true,
    },
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("close", (event) => {
    if (!isQuitting && process.platform !== "darwin") {
      event.preventDefault();
      mainWindow.hide();
    }
  });
  mainWindow.on("closed", () => { mainWindow = undefined; });
}

function createTray() {
  const icon = path.join(__dirname, "resources", "tray-icon.png");
  if (!fs.existsSync(icon)) return;
  tray = new Tray(icon);
  tray.setToolTip("Aurora Relay");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open Aurora Relay", click: () => mainWindow?.show() },
    { type: "separator" },
    { label: "Quit", click: () => { isQuitting = true; app.quit(); } },
  ]));
  tray.on("click", () => mainWindow?.show());
}

async function boot() {
  await provisionConnectorVault();
  backendPort = await choosePort();
  spawnBackend();
  createWindow();
  const ready = await backendReady();
  if (!ready) {
    await dialog.showMessageBox(mainWindow, { type: "error", title: "Local service unavailable", message: "Aurora Relay could not start its local API.", detail: "Check the application logs and verify that the packaged backend is present." });
    app.quit();
    return;
  }
  await mainWindow.loadURL(`http://127.0.0.1:${backendPort}`);
  createTray();
  updater = new AppUpdater(mainWindow);
  updater.checkForUpdates();
  await new SetupWizard(mainWindow).show();
}

app.whenReady().then(boot).catch((error) => {
  console.error(error);
  dialog.showErrorBox("Aurora Relay failed to start", error.stack || String(error));
  app.quit();
});

app.on("before-quit", () => { isQuitting = true; stopBackend(); });
app.on("window-all-closed", () => { if (process.platform === "darwin") app.quit(); });
app.on("activate", () => { if (!mainWindow) createWindow(); else mainWindow.show(); });

ipcMain.handle("app:get-status", () => ({ backendPort, backendRunning: Boolean(backendProcess), version: app.getVersion(), vault: vaultStatus }));
ipcMain.handle("vault:get-status", () => vaultStatus);
ipcMain.handle("app:minimize-to-tray", () => mainWindow?.hide());
ipcMain.handle("app:quit", () => { isQuitting = true; app.quit(); });
ipcMain.handle("app:open-external", (_event, url) => {
  if (typeof url === "string" && /^https?:\/\//i.test(url)) return shell.openExternal(url);
  return false;
});
