"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const SERVICE_NAME = "Aurora Relay Connector Vault";
const ACCOUNT_NAME = "backend-fernet-v1";

function fernetKey() {
  return crypto.randomBytes(32).toString("base64").replace(/\+/g, "-").replace(/\//g, "_");
}

function validFernetKey(value) {
  if (typeof value !== "string" || value.length < 43 || value.length > 48) return false;
  try {
    return Buffer.from(value, "base64").length === 32;
  } catch {
    return false;
  }
}

function platformProvider(platform) {
  if (platform === "win32") return "windows-credential-vault";
  if (platform === "darwin") return "macos-keychain";
  return "linux-secret-service";
}

function status(state, backend, fallback, reason = null, migrated = false) {
  return { state, backend, fallback, reason, migrated };
}

class DesktopCredentialVault {
  constructor({ userData, safeStorage, keytarModule, platform = process.platform, legacyKeyPaths = [] }) {
    this.userData = userData;
    this.safeStorage = safeStorage;
    this.keytar = keytarModule;
    this.platform = platform;
    this.legacyKeyPaths = legacyKeyPaths;
    this.currentStatus = status("locked", "initializing", false, "Credential protection is initializing.");
  }

  static withElectron({ userData, legacyKeyPaths = [] }) {
    const { safeStorage } = require("electron");
    let keytarModule;
    try {
      keytarModule = require("@github/keytar");
    } catch {
      keytarModule = null;
    }
    return new DesktopCredentialVault({ userData, safeStorage, keytarModule, legacyKeyPaths });
  }

  getStatus() {
    return this.currentStatus;
  }

  _legacyPaths() {
    const configured = process.env.AURORA_CONNECTOR_VAULT_PATH;
    return [...new Set([
      ...(configured ? [configured] : []),
      ...this.legacyKeyPaths,
      path.join(this.userData, "connector-vault.key"),
      path.join(os.homedir(), ".aurora-relay", "connector-vault.key"),
    ])];
  }

  _readLegacyKey() {
    for (const candidate of this._legacyPaths()) {
      try {
        if (!fs.existsSync(candidate)) continue;
        const value = fs.readFileSync(candidate, "utf8").trim();
        if (validFernetKey(value)) return value;
      } catch {
        // A malformed or unreadable legacy key must not prevent attempting an
        // OS-backed key. The original file is left untouched for recovery.
      }
    }
    return null;
  }

  _fallbackFile() {
    return path.join(this.userData, "connector-vault.safe-storage");
  }

  _writeEncryptedFallback(value) {
    const encrypted = this.safeStorage.encryptString(value);
    fs.mkdirSync(this.userData, { recursive: true });
    const file = this._fallbackFile();
    const temporary = `${file}.${process.pid}.tmp`;
    fs.writeFileSync(temporary, encrypted, { mode: 0o600 });
    fs.renameSync(temporary, file);
  }

  async _provisionFallback(nativeFailure) {
    const backend = "electron-safe-storage";
    try {
      if (!this.safeStorage || !(await this.safeStorage.isAsyncEncryptionAvailable())) {
        throw new Error("OS-backed encryption is unavailable");
      }
      if (this.platform === "linux" && this.safeStorage.getSelectedStorageBackend?.() === "basic_text") {
        throw new Error("Linux Secret Service is unavailable; basic_text storage is not accepted");
      }

      const file = this._fallbackFile();
      if (fs.existsSync(file)) {
        const decrypted = await this.safeStorage.decryptStringAsync(fs.readFileSync(file));
        if (!validFernetKey(decrypted.result)) throw new Error("Encrypted fallback key is invalid");
        if (decrypted.shouldReEncrypt) this._writeEncryptedFallback(decrypted.result);
        this.currentStatus = status("ready", backend, true, null, false);
        return { key: decrypted.result, status: this.currentStatus };
      }

      const migrated = this._readLegacyKey();
      const key = migrated || fernetKey();
      this._writeEncryptedFallback(key);
      this.currentStatus = status("ready", backend, true, null, Boolean(migrated));
      return { key, status: this.currentStatus };
    } catch {
      this.currentStatus = status(
        "locked",
        nativeFailure ? platformProvider(this.platform) : backend,
        true,
        "OS credential protection is unavailable. Connector credentials remain locked.",
      );
      return { key: null, status: this.currentStatus };
    }
  }

  async provisionBackendKey() {
    const provider = platformProvider(this.platform);
    if (!this.keytar) return this._provisionFallback(true);
    try {
      const existing = await this.keytar.getPassword(SERVICE_NAME, ACCOUNT_NAME);
      if (existing && validFernetKey(existing)) {
        this.currentStatus = status("ready", provider, false);
        return { key: existing, status: this.currentStatus };
      }
      const migrated = this._readLegacyKey();
      const key = migrated || fernetKey();
      await this.keytar.setPassword(SERVICE_NAME, ACCOUNT_NAME, key);
      this.currentStatus = status("ready", provider, false, null, Boolean(migrated));
      return { key, status: this.currentStatus };
    } catch {
      return this._provisionFallback(true);
    }
  }
}

module.exports = { DesktopCredentialVault, validFernetKey };
