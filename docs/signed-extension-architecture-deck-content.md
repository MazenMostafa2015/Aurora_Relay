# Signed Extension Verification Architecture — Slide Content

## Cover

**Signed Extensions, Local Trust**

Aurora Relay verification architecture and key security boundaries

## Slide 1

**Unsigned files are not a trust boundary**

- Current loose manifest and entrypoint discovery can prove neither publisher nor payload integrity.
- The new `.aurx` model accepts only a trusted signer and exact, declared package bytes.
- Security remains local-first: no package feed, key server, revocation lookup, or telemetry.

## Slide 2

**Three identities stay separate**

- **Publisher key:** Ed25519 private seed, held in the native vault on an operator signing machine.
- **Runtime trust:** signed local public-key keyring, read by the backend verifier.
- **Release delivery:** existing desktop installer signing protects the bootstrap root and recovery path.

## Slide 3

**The package binds code to intent**

- `.aurx` contains `manifest.json`, `manifest.json.sig`, and indexed payload files.
- RFC 8785 canonical JSON gives the manifest one signing representation.
- The manifest indexes every payload by normalized path, SHA-256 digest, and size.

## Slide 4

**Verification is repeated at every gate**

- **Catalogue:** defensive ZIP inspection, manifest validation, trusted signer, and payload digests.
- **Install and enable:** re-verify current bytes and compare persisted package identity.
- **Execute:** verify from one open archive, stage only verified bytes, then invoke Docker.
- Any failure blocks the package before container startup; host execution is never a fallback.

## Slide 5

**Rotation preserves offline control**

- A planned rotation generates a new local key and applies a generation-incremented keyring signed by the incumbent key.
- Retired keys may verify historical packages but cannot sign newly accepted packages after cutoff.
- Revocation disables affected extensions on their next verification.
- Emergency bootstrap recovery requires a protected desktop update, not a potentially compromised signer.

## Slide 6

**Fail closed is an operational design**

- Reject unsigned, unknown-key, revoked, tampered, malformed, oversized, and trust-unavailable packages.
- Persist safe evidence: status, signer ID, digests, verification time, and bounded reason code.
- Show Trust independently from Lifecycle: `Verified / Disabled` differs from `Tampered / Blocked`.
- Do not expose private keys, raw trust data, signature bytes, stack traces, or generic vault APIs.

## Slide 7

**Implementation proceeds as a security slice**

- **Core:** strict archive reader, canonical manifest, Ed25519 verifier, and trusted keyring.
- **Enforcement:** verified registry values, lifecycle re-checks, migration, API contracts, and audit events.
- **Operations:** isolated vault records, operator signing CLI, planned rotation, revocation, and recovery.
- **Release:** sign built-ins, run negative tests and UI checks, enforce CI package verification, then collect evidence.

## Slide 8

**The resulting execution contract**

Aurora Relay runs only extension bytes that are signed by an active local trust root, match their declared payload identity, are explicitly enabled by an authorized user, and enter the existing Docker-only sandbox.

No valid package, no activation. No valid trust, no execution.
