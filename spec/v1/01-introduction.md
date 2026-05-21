# 1. Introduction

## 1.1 Abstract

PlainCloak is a platform-agnostic, paste-anywhere end-to-end encryption protocol for private messaging over arbitrary text-bearing channels. A PlainCloak message is a single self-contained string that encodes a recipient-encrypted payload, sender signature, and the metadata needed to decrypt and verify the message without out-of-band context. This document specifies version 1 (`v1`) of the wire format, message body, cryptographic suites, and required behavior of conforming implementations.

## 1.2 Scope

This specification defines:

- The wire envelope by which a PlainCloak message is represented as a single text string.
- The compressed JSON body that the envelope wraps.
- The canonical form over which a sender's signature is computed.
- The cryptographic algorithm suites available in `v1`.
- The procedure for deriving stable identifiers from public keys.
- The normative behavior of producers and consumers of PlainCloak messages.
- The mandatory test vectors that conforming implementations MUST pass.

This specification does NOT define:

- A transport. PlainCloak messages travel over any channel that preserves the printable ASCII characters in the wire alphabet.
- A user interface, key-discovery mechanism, contact directory, or naming service.
- A keystore wire format. A keystore JSON Schema is provided as informative companion material.
- Group messaging, forward secrecy, or post-quantum suites. These are out of scope for `v1`.

## 1.3 Goals

1. **Reproducibility.** Two independent implementations following only this document MUST be able to interoperate.
2. **Channel agnosticism.** A `v1` message MUST be representable as printable ASCII drawn from a small alphabet so that it survives transmission through chat applications, SMS, email, and similar channels without re-encoding.
3. **Self-containment.** Every PlainCloak message carries the metadata needed to identify the recipient key, the sender's public-key fingerprint, the algorithm suite, and the signature, without requiring an out-of-band lookup keyed on the message itself.
4. **Crypto agility.** New cryptographic suites and compression algorithms can be added without invalidating existing messages. Wire-format changes that alter parser behavior require a new version.
5. **No mandatory infrastructure.** Conforming implementations operate purely client-side. No server, registry, or directory is required to produce or consume a `v1` message.

## 1.4 Non-goals

- **Forward secrecy** for past messages on key compromise. `v1` uses a static recipient key; if that key leaks, all past messages encrypted to it become decryptable.
- **Metadata privacy** beyond what plaintext encryption provides. The wire format reveals that a message is a PlainCloak `v1` payload to a particular key hash. Traffic-analysis resistance is out of scope.
- **Replay protection** at the protocol layer. The body's `i` (message identifier) field permits an application to detect replays but `v1` does not require implementations to do so.
- **Identity binding.** PlainCloak does not bind public keys to real-world identities. The relationship between a `key_hash` and a person is determined entirely by out-of-band trust establishment.

## 1.5 Terminology

| Term | Definition |
|------|------------|
| Wire message | The single text string that represents an encoded PlainCloak message, beginning with `PLAINCLOAK:`. |
| Envelope | The uncompressed header portion of a wire message, consisting of magic, version, compression code, and payload, separated by colons. |
| Payload (wire) | The Base62-encoded, compressed bytes following the envelope's last separator. |
| Body | The decoded JSON object obtained by Base62-decoding and decompressing the wire payload. |
| Payload (body) | The Base64-encoded ciphertext field (`p`) inside the body. Distinct from "payload (wire)" by context. |
| Suite | An identified combination of encryption construction (direct public-key, or hybrid KEM+AEAD) and signing algorithm, named by the body's `a` field. |
| Canonical form | The deterministic string serialization of a body's signed fields used as input to the signature algorithm. |
| Key hash | The lowercase hex SHA-256 of a public key's SPKI DER encoding, used as a stable identifier. |
| Producer | An implementation that constructs and emits wire messages. |
| Consumer | An implementation that parses and decrypts wire messages. |
| Recipient | The party for whom a wire message is encrypted; identified by the body's `r` field. |
| Sender | The party who signed a wire message; identified by the body's `s` field. |
| MUST-pass vector | A test vector whose passing is required for a claim of conformance. |

## 1.6 Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **NOT RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals, as shown here.

## 1.7 Document structure

This specification is organized into the following sections:

| Section | Topic |
|---------|-------|
| 1 (this) | Introduction, scope, goals, terminology. |
| 2 | Notational and encoding conventions used throughout. |
| 3 | Wire-format envelope and parsing. |
| 4 | Base62 encoding. |
| 5 | Compression (Brotli and registry). |
| 6 | Message body fields and validation. |
| 7 | Canonical form for signing. |
| 8 | Cryptographic suites. |
| 9 | Key identification (hash derivation). |
| 10 | Producer and consumer behavior. |
| 11 | Security considerations. |
| 12 | Conformance and test vectors. |
| 13 | IANA considerations and registry policy. |
| 14 | References. |
| Appendix A | Worked end-to-end example. |
| Appendix B | Consolidated ABNF grammar. |

Companion machine-readable artifacts are normatively referenced from the relevant sections:

- `schemas/v1/wire.abnf` (Section 3)
- `schemas/v1/message.schema.json` (Section 6)
- `schemas/v1/algorithms.json` and `schemas/v1/algorithms.schema.json` (Section 8)
- `schemas/v1/compression.json` and `schemas/v1/compression.schema.json` (Section 5)
- `schemas/v1/keystore.schema.json` (informative)

The mandatory test vectors are located at `test-vectors/v1/`.
