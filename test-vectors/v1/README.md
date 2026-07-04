# PlainCloak v1 Test Vectors

This directory holds the canonical test vectors that conforming implementations MUST pass. They are the executable contract that complements the prose specification in `spec/v1/`.

## Layout

```
test-vectors/v1/
├── README.md                 (this file)
├── schema.json               JSON Schema for a single vector file
├── deterministic/            byte-stable inputs/outputs (encoding, hashing, canonical form)
├── verification/             keyed inputs/outputs (decrypt, signature verify)
└── fixtures/
    └── keys/                 RSA keypairs in PEM form, used as inputs by verification vectors
```

## Two kinds of vectors

### Deterministic

A deterministic vector specifies an exact input and an exact expected output. Both ends of the computation are byte-stable and a conforming implementation MUST reproduce the exact output bytes. Examples: Base62 encoding, SHA-256 of an SPKI DER, the canonical-form string for a fixed body.

Files:

| File | Purpose |
|------|---------|
| `deterministic/01-base62-encode.json` | Octet-string → Base62 encoding cases. |
| `deterministic/02-base62-decode.json` | Base62 → octet-string decoding cases. |
| `deterministic/03-brotli-roundtrip.json` | Compress-then-decompress round trip; the round trip is what matters, not specific compressed bytes. |
| `deterministic/04-canonical-form.json` | Body fields → canonical-form string cases. |
| `deterministic/05-key-hash-spki.json` | SPKI PEM → `key_hash` cases, using the keys in `fixtures/keys/`. |
| `deterministic/06-message-id-formatting.json` | UUIDv4 acceptance/rejection cases for the body's `i` field (message identifier). |

### Verification

A verification vector specifies a wire message, the keys needed to consume it, and the outcome a conforming consumer MUST produce (one of the five outcomes of `spec/v1/10-encrypt-decrypt.md` Section 10.3). Verification vectors do NOT specify exact ciphertext or signature bytes, because RSA-OAEP and RSA-PSS are randomized; the outputs of two correct producers for the same plaintext will differ. What is fixed is the consumer-side outcome.

Files:

| File | Purpose |
|------|---------|
| `verification/01-rsa2048-roundtrip.json` | Encrypt to a 2048-bit recipient and verify decryption + signature succeed. |
| `verification/02-rsa4096-roundtrip.json` | Same with a 4096-bit recipient. |
| `verification/03-tampered-payload.json` | A roundtrip whose `payload` was modified after signing; consumer MUST report `decryption-failed`. |
| `verification/04-tampered-signature.json` | A roundtrip whose `signature` was modified; consumer MUST report `signature-invalid`. |
| `verification/05-wrong-recipient.json` | Ciphertext encrypted to a key not in the consumer's keystore; consumer MUST report `wrong-recipient`. |
| `verification/06-unknown-sender.json` | Signed by a key not in the consumer's contacts; consumer MUST report `unknown-sender` and still surface plaintext. |
| `verification/07-rsa2048-hybrid-roundtrip.json` | `RSA-OAEP-AES256GCM-SHA256` roundtrip with a 2048-bit recipient. |
| `verification/08-rsa4096-hybrid-roundtrip.json` | `RSA-OAEP-AES256GCM-SHA256` roundtrip with a 4096-bit recipient. |
| `verification/09-hybrid-long-plaintext.json` | 2048-byte plaintext under the hybrid suite to a 2048-bit recipient; would have been rejected by `RSA-OAEP-SHA256` at the producer's plaintext-length check. |
| `verification/10-hybrid-tampered-wrap.json` | Hybrid wire message whose `wrapped_K` segment was modified; consumer MUST report `decryption-failed`. |
| `verification/11-hybrid-tampered-tag.json` | Hybrid wire message whose AEAD tag was modified; consumer MUST report `decryption-failed`. |
| `verification/12-hybrid-signature-invalid.json` | Hybrid wire message whose `g` (signature) was modified after signing; consumer MUST report `signature-invalid` and still surface plaintext. |

## File format

Every vector file conforms to `schema.json`. The structure is:

```json
{
  "version": "v1",
  "kind": "deterministic" | "verification",
  "category": "string short label, e.g. base62-encode",
  "description": "human-readable summary",
  "cases": [
    {
      "id": "v1-det-base62-001",
      "description": "Encode a single zero byte",
      "inputs":   { ... category-specific ... },
      "expected": { ... category-specific ... }
    }
  ]
}
```

The `inputs` and `expected` shapes vary by category. The relevant section of the spec (e.g. `spec/v1/04-encoding.md` for Base62) describes the meaning of each field.

## Conformance

A conforming `v1` implementation MUST pass:

- 100% of the cases in every `deterministic/*.json` file.
- 100% of the cases in every `verification/*.json` file.

Implementations claiming partial conformance (e.g. consumer-only) MUST document which files and which cases they pass. See `spec/v1/12-conformance.md`.

## Reproducing the vectors

The committed files were produced by a one-shot generator script kept outside this repository (it is not part of the spec deliverable, since shipping a runner would force a language choice). The fixed inputs (test plaintexts, fixed UUIDs and timestamps used as illustration) are either embedded directly in the vector files or, for cryptographic content, locked by referencing the PEM keys in `fixtures/keys/`.

If a future change to the spec requires regenerating the vectors, the generator script should be re-run and its outputs committed. The PEM keys in `fixtures/keys/` are intentionally stable across regenerations so that key-hash vectors do not churn.

## CI consistency check

CI runs `.github/scripts/check_vectors.py` on every push and pull request. It recomputes the deterministic layers (Base62, canonical form, key hashes, Brotli round-trip), decodes each verification vector's wire message without any key material, and asserts that the decoded body agrees with the vector's `expected` block, the registries, and the byte-exact worked examples in the prose. It is an internal maintenance guard against drift between prose, vectors, and registries (it performs no decryption and is NOT the reference vector driver that Section 12.6 of the spec deliberately leaves to implementations).
