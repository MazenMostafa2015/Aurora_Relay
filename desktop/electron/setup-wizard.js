"use strict";

const { BrowserWindow, ipcMain } = require("electron");
const { execFile } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

function configPath() {
  const root = process.platform === "win32"
    ? process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming")
    : process.platform === "darwin"
      ? path.join(os.homedir(), "Library", "Application Support")
      : process.env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
  return path.join(root, "AuroraRelay", "config.json");
}

function commandName(command) {
  return process.platform === "win32" ? `${command}.exe` : command;
}

function runCommand(command, args = [], timeout = 7000) {
  return new Promise((resolve) => {
    execFile(commandName(command), args, { timeout, windowsHide: true }, (error, stdout, stderr) => {
      if (error) {
        resolve({ ok: false, code: error.code || "COMMAND_FAILED", message: (stderr || error.message || "Command failed").trim() });
        return;
      }
      resolve({ ok: true, output: (stdout || stderr || "").trim() });
    });
  });
}

class SetupWizard {
  constructor(parentWindow) {
    this.parentWindow = parentWindow;
    this.window = undefined;
    this.finished = false;
    this.probePromise = undefined;
  }

  isComplete() {
    try {
      return JSON.parse(fs.readFileSync(configPath(), "utf8")).setupComplete === true;
    } catch {
      return false;
    }
  }

  saveConfig(input, runtime = {}) {
    const config = {
      setupComplete: true,
      setupDate: new Date().toISOString(),
      useLocalModel: Boolean(input?.useLocalModel),
      enableCloudProviders: Boolean(input?.enableCloudProviders),
      startOnLogin: Boolean(input?.startOnLogin),
      sendAnonymousDiagnostics: Boolean(input?.sendAnonymousDiagnostics),
      runtime: {
        ollama: runtime.ollama || "unavailable",
        docker: runtime.docker || "unavailable",
        codeExecutionEnabled: runtime.docker === "ready",
        localModelEnabled: Boolean(input?.useLocalModel && runtime.ollama === "ready"),
      },
    };
    fs.mkdirSync(path.dirname(configPath()), { recursive: true });
    fs.writeFileSync(configPath(), `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
  }

  send(message) {
    if (this.window && !this.window.isDestroyed()) this.window.webContents.send("setup:progress", message);
  }

  async probeRuntime() {
    if (this.probePromise) return this.probePromise;
    this.probePromise = (async () => {
      const results = { ollama: "unavailable", docker: "unavailable" };
      this.send({ type: "phase", id: "ollama", state: "running", message: "Checking for Ollama…", percent: 25 });
      const ollama = await runCommand("ollama", ["--version"]);
      if (ollama.ok) {
        results.ollama = "ready";
        this.send({ type: "phase", id: "ollama", state: "success", message: ollama.output || "Ollama is ready.", percent: 45 });
      } else {
        this.send({ type: "phase", id: "ollama", state: "warning", code: "OLLAMA_NOT_FOUND", message: "Ollama was not detected. Local model use will stay disabled until it is installed.", detail: ollama.message, percent: 45 });
      }

      this.send({ type: "phase", id: "docker", state: "running", message: "Checking Docker Engine…", percent: 60 });
      const docker = await runCommand("docker", ["version", "--format", "{{.Server.Version}}"]);
      if (docker.ok) {
        results.docker = "ready";
        this.send({ type: "phase", id: "docker", state: "success", message: `Docker Engine ${docker.output || "is ready"}.`, percent: 80 });
      } else {
        results.docker = "unavailable";
        this.send({ type: "phase", id: "docker", state: "warning", code: "DOCKER_UNAVAILABLE", message: "Docker is unavailable. Code execution remains disabled by policy.", detail: docker.message, percent: 80 });
      }
      this.send({ type: "complete", results, percent: 88 });
      return results;
    })();
    return this.probePromise;
  }

  async show() {
    if (this.isComplete() || !this.parentWindow) return true;
    return new Promise((resolve) => {
      this.window = new BrowserWindow({
        width: 680,
        height: 780,
        parent: this.parentWindow,
        modal: true,
        show: false,
        title: "Aurora Relay setup",
        backgroundColor: "#0b1013",
        webPreferences: {
          preload: path.join(__dirname, "setup-preload.js"),
          contextIsolation: true,
          nodeIntegration: false,
          sandbox: true,
        },
      });
      const senderIsWindow = (event) => event.sender === this.window?.webContents;
      const finish = (value) => {
        if (this.finished) return;
        this.finished = true;
        if (this.window && !this.window.isDestroyed()) this.window.close();
        resolve(value);
      };
      const onProbe = async (event) => {
        if (!senderIsWindow(event)) return;
        try {
          this.probePromise = undefined;
          await this.probeRuntime();
        } catch (error) {
          this.send({ type: "fatal", code: "PROBE_FAILED", message: "Runtime checks failed unexpectedly.", detail: error.message, percent: 88 });
        }
      };
      const onComplete = (event, data) => {
        if (!senderIsWindow(event)) return;
        const runtime = data?.runtime || {};
        this.saveConfig(data, runtime);
        this.send({ type: "phase", id: "finalize", state: "success", message: "Preferences saved. Opening your workspace…", percent: 100 });
        setTimeout(() => finish(true), 250);
      };
      const onCancel = (event) => { if (senderIsWindow(event)) finish(false); };
      ipcMain.on("setup:probe", onProbe);
      ipcMain.on("setup:complete", onComplete);
      ipcMain.on("setup:cancel", onCancel);
      this.window.once("closed", () => {
        ipcMain.removeListener("setup:probe", onProbe);
        ipcMain.removeListener("setup:complete", onComplete);
        ipcMain.removeListener("setup:cancel", onCancel);
        resolve(false);
      });
      this.window.loadFile(path.join(__dirname, "setup.html"));
      this.window.once("ready-to-show", () => this.window.show());
    });
  }
}

module.exports = { SetupWizard };
