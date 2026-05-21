# Changelog

All notable changes to the PlainCloak protocol specification are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) for spec text. Wire-protocol versioning is independent: a new wire version is introduced as a sibling directory (`spec/v2/`) rather than as a SemVer bump.

## [Unreleased]

## [1.0.0] - 2026-05-20

Initial public release of the `v1` protocol specification.

### Added

- Wire envelope `PLAINCLOAK:vN:CC:payload` with Base62 alphabet and Brotli compression.
- Message body schema: seven single-letter fields (`a`, `i`, `t`, `s`, `r`, `p`, `g`).
- Canonical-form construction with wire-version domain separation for signatures.
- Cryptographic suites: `RSA-OAEP-SHA256` (REQUIRED) and `RSA-OAEP-AES256GCM-SHA256` (RECOMMENDED hybrid).
- Key identification by SHA-256 digest over SPKI DER.
- Open suite and compression registries under Specification Required policy.
- Conformance vectors: deterministic (encoding, canonical form, key hash) and verification (roundtrip, tampering, wrong-recipient, unknown-sender).
- JSON Schemas for message body, keystore, algorithm and compression registries; ABNF grammar.
- Informative threat model and design-rationale documents.
- Dual licensing: CC-BY-4.0 for prose, Apache-2.0 for schemas and test vectors.
