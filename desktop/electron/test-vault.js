"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { DesktopCredentialVault } = require("./vault");

function keytarMemory() {
  const records = new Map();
  return {
    getPassword: async (service, account) => records.get(`${service}/${account}`) || null,
    setPassword: async (service, account, value) => { records.set(`${service}/${account}`, value); },
  };
}

async function run() {
  const userData = fs.mkdtempSync(path.join(os.tmpdir(), "aurora-vault-"));
  const nativeStore = keytarMemory();
  const first = new DesktopCredentialVault({ userData, keytarModule: nativeStore, safeStorage: null, platform: "win32" });
  const initial = await first.provisionBackendKey();
  assert.equal(initial.status.state, "ready");
  assert.equal(initial.status.backend, "windows-credential-vault");
  assert.ok(initial.key);

  const second = new DesktopCredentialVault({ userData, keytarModule: nativeStore, safeStorage: null, platform: "win32" });
  const restored = await second.provisionBackendKey();
  assert.equal(restored.key, initial.key);

  const locked = new DesktopCredentialVault({
    userData,
    keytarModule: null,
    safeStorage: { isAsyncEncryptionAvailable: async () => false },
    platform: "linux",
  });
  const unavailable = await locked.provisionBackendKey();
  assert.equal(unavailable.key, null);
  assert.equal(unavailable.status.state, "locked");
  assert.doesNotMatch(JSON.stringify(unavailable.status), /connector-vault|ghp_/i);
  fs.rmSync(userData, { recursive: true, force: true });
}

run().then(() => console.log("desktop vault checks passed")).catch((error) => { console.error(error); process.exitCode = 1; });
