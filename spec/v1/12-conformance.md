# 12. Conformance

This section defines what it means for an implementation to claim PlainCloak `v1` conformance, the test vectors that any such claim MUST be substantiated by, and how an implementation declares which registry entries it supports.

## 12.1 Conformance tiers

A `v1` implementation MAY claim conformance at one of three tiers. Tiers are not ranked; they describe scope, not quality.

### 12.1.1 Core implementer

A **core implementer** is an implementation that produces and consumes `v1` wire messages.

A core implementer MUST:

- Implement the wire format of Section 3, including the strict parsing rules of Section 3.3.
- Implement the Base62 encoding and decoding of Section 4.
- Implement the Brotli compression layer of Section 5 in producer and consumer roles, and reject all other registry entries whose status is `reserved` or `deprecated`-for-rejection.
- Implement the JSON message body validation of Section 6, against the schema at `schemas/v1/message.schema.json`.
- Implement the canonical-form construction of Section 7.
- Implement the `RSA-OAEP-SHA256` suite of Section 8 in encryption, decryption, signing, and verifying roles, and reject all other registry entries whose status is `reserved` or `deprecated`-for-rejection.
- Implement the `RSA-OAEP-AES256GCM-SHA256` suite of Section 8.10 in the consumer role (decryption and signature verification). The producer role is RECOMMENDED but not REQUIRED for core conformance; producers that do not implement encryption under this suite cannot emit plaintexts larger than the `RSA-OAEP-SHA256` ceiling and SHOULD document this limitation per Section 12.3.
- Implement the key-identification algorithm of Section 9.
- Implement the producer and consumer behaviors of Section 10, including the five outcomes of Section 10.3.
- Pass 100% of the deterministic vectors at `test-vectors/v1/deterministic/`.
- Pass 100% of the verification vectors at `test-vectors/v1/verification/` for every registry entry the implementation claims to support.

A core implementer MAY additionally support any number of registered suites and compression codes whose status is `required`, `recommended`, or `optional`. This is the **core profile**: the minimal supported set is `{BR}` for compression and, for cryptographic suites, `{RSA-OAEP-SHA256}` on the producer side and `{RSA-OAEP-SHA256, RSA-OAEP-AES256GCM-SHA256}` on the consumer side (per the consumer requirement in this section). Implementations that support additional registry entries are still core-conforming; the broader support is declared per 12.3.

### 12.1.2 Producer-only

A **producer-only** implementation produces wire messages but does not consume them. It MUST:

- Implement everything in 12.1.1 except those parts of Section 8 and Section 10 that pertain exclusively to consumers (i.e. RSA-OAEP decryption, hybrid-suite decryption, and signature verification).
- Pass 100% of the deterministic vectors.
- Pass the producer-side checks of every verification vector for the registry entries it supports (i.e. the producer's wire output, when consumed by a known-good reference consumer, MUST satisfy the vector's expected outcome).

A producer-only implementation MUST document its scope in its README. It MUST NOT claim "core" conformance.

### 12.1.3 Consumer-only

A **consumer-only** implementation consumes wire messages but does not produce them (e.g. a forensic analysis tool, an inbound-only chat plugin). It MUST:

- Implement everything in 12.1.1 except RSA-OAEP encryption, hybrid-suite encryption, and RSA-PSS signing.
- Pass 100% of the deterministic vectors.
- Pass 100% of the verification vectors as a consumer for every registry entry it supports.

A consumer-only implementation MUST document its scope in its README. It MUST NOT claim "core" conformance.

## 12.2 Vector pass criteria

For each test-vector file, the pass criterion is defined by the vector's `kind` and the case-by-case `expected` block.

### 12.2.1 Deterministic vectors

For each case in a deterministic vector file:

- The implementation MUST produce, given `inputs`, output bytes equal to `expected`.
- "Equal" means byte-identical for byte-typed fields and value-identical for boolean and integer fields.
- Encoder choices that produce non-determinism (e.g. Brotli encoder block-splitting) are explicitly documented in the relevant vector and are NOT compared as exact bytes; only the round-trip property is checked.

### 12.2.2 Verification vectors

For each case in a verification vector file:

- The implementation, acting as a consumer with the inputs specified, MUST produce the outcome equal to `expected.outcome`.
- For outcomes `verified`, `signature-invalid`, and `unknown-sender`, the implementation MUST produce a plaintext equal to `expected.plaintext` if that field is present.
- For outcomes `wrong-recipient` and `decryption-failed`, the implementation MUST NOT produce any plaintext (the absence is observed by the test driver).
- The implementation's reported values for the body's `i`, `t`, `s`, and `r` fields MUST equal the corresponding fields in `expected` when those fields are present (in the test vectors these are spelled out as `msg_id`, `timestamp`, `sender_key_hash`, `recipient_key_hash` for human readability).

An implementation MAY skip verification vectors whose suite or compression code it does not support, provided it declares the unsupported entries per 12.3 and the registry entries it claims to support are exercised end-to-end.

## 12.3 Conformance reporting

An implementation claiming `v1` conformance SHOULD publish a `CONFORMANCE.md` (or equivalent section in its README) that:

- States the conformance tier.
- Pins the spec commit hash the implementation targets.
- Pins the test-vector commit hash the implementation passes against.
- Lists the suite registry entries it supports for produce and for consume, separately.
- Lists the compression registry entries it supports for produce and for consume, separately.
- States the decompression size budget enforced (Section 5.4).
- Includes the output of the implementation's vector-runner CI on a recent commit.

A `versions.json` cross-reference SHOULD point at the `v1` entry of `plaincloak-spec/versions.json` so that automated tooling can discover the implementation's targeted version.

## 12.4 Optional features

The following are explicitly NOT required for `v1` conformance:

- The keystore schema at `schemas/v1/keystore.schema.json`. It is informative companion material; an implementation MAY use a different on-disk key format and remain `v1` conforming.
- A command-line interface.
- Detection of `PLAINCLOAK:v1:` prefixes in arbitrary text. Implementations whose I/O contract is "given a single wire string" need not perform extraction.
- The `NO` (no-compression) compression code (Section 5.3). An implementation MAY support it for diagnostics or refuse it; both choices are conforming.
- Any registry entry whose status is `recommended`, `optional`, or `deprecated`. These are matters of profile coverage, not conformance.

An implementation that elects to support the keystore schema MUST do so completely (the schema is closed-object; partial support is non-conforming for the keystore feature, even though the rest of `v1` is unaffected).

## 12.5 Forward compatibility behavior

A `v1` implementation MUST reject:

- Wire messages whose envelope version is not `v1`.
- Bodies that contain a `version` field (it was removed; see Section 6.3).
- Bodies whose `a` field is unknown to the implementation, or known to it but with a registered status of `reserved` or `deprecated`-for-rejection. The error category is `unknown-suite`.
- Compression codes unknown to the implementation, or known to it but with a registered status of `reserved` or `deprecated`-for-rejection. The error category is `unknown-compression`.
- Bodies with unknown fields (Section 6.3).

These rejection behaviors are themselves part of conformance and are exercised by deterministic vectors that include negative cases. The set of rejected registry entries is implementation-specific because the registries are open (Section 13); an implementation that does not support a newly registered suite or compression code rejects it as `unknown-*` even though the entry is well-formed in the registry.

## 12.6 Self-test recommendation

Every conforming implementation SHOULD include a CI step that:

1. Clones or vendors the `plaincloak-spec` repository at a known commit.
2. Runs the implementation's vector driver against `test-vectors/v1/deterministic/` and `test-vectors/v1/verification/`, restricted to the registry entries the implementation supports.
3. Fails the build on any vector mismatch.

A reference vector driver is intentionally not provided by this repository; shipping a runner would force a language choice and add a dependency that conformance does not need. Each implementation writes a thin driver in its own language. A typical driver is approximately 50 lines.
