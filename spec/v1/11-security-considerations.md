# 11. Security Considerations

This section discusses the threats `v1` defends against, the threats it does not, and the implementation pitfalls that would weaken the security argument. The list is not exhaustive; it covers the issues that are most likely to surface during implementation review or operational use.

## 11.1 Threat model

PlainCloak `v1` is designed to defend against:

- **Passive observers** of the transport (chat-app operators, network observers, archival systems). The wire message reveals only that a compressed encrypted blob exists destined for a specific recipient key hash (the body's `r` field). The plaintext is unrecoverable without the recipient's private key.
- **Active modifiers** of the transport (a malicious chat operator who substitutes message bodies). Modification of the wire payload causes either decryption failure or signature-verification failure, both of which are surfaced to the user (Section 10.3).
- **Compromise of the transport's storage** (a server later breached). The same protection as for active modifiers applies: stored ciphertext is not recoverable without the recipient's private key.

PlainCloak `v1` does NOT defend against:

- **Endpoint compromise.** If the user's device is compromised, plaintext, private keys, and contact lists are recoverable. PlainCloak provides no protection beyond standard local-file encryption that is out of scope.
- **Out-of-band trust failures.** PlainCloak does not bind keys to identities. A key-hash that the user trusts as "Alice" was trusted because the user added it to their contacts; if the user added a wrong key, all messages "from Alice" are spoofable by whoever controls the wrong key. Out-of-band verification is the responsibility of the user and the surrounding application.
- **Traffic analysis.** PlainCloak messages reveal their length, timing, recipient key hash, and sender key hash. An adversary observing a recipient's incoming messages can count them, time them, and group them by sender. `v1` does not pad, mix, or otherwise mask metadata.
- **Forward secrecy.** A compromise of a private key permits decryption of all past messages encrypted to its corresponding public key. `v1` does not ratchet keys. Users for whom forward secrecy is important should rotate keys periodically and accept the loss of message-archive readability that rotation entails.

## 11.2 Cryptographic choices

### 11.2.1 RSA-OAEP-SHA256

RSA-OAEP with SHA-256 is the encryption primitive. RSA-OAEP is widely deployed, well-analyzed, and supported by every major cryptographic library. The choice of SHA-256 over SHA-1 closes the documented OAEP-with-SHA-1 issues; the SHA-256 variant has no known practical weakness against well-implemented libraries with `e = 65537`.

The choice of RSA over an elliptic-curve scheme for `v1` is pragmatic: RSA is universally supported, easily understood by reviewers, and key-format conventions are mature. Arbitrary-length plaintexts are already supported within `v1` by the `RSA-OAEP-AES256GCM-SHA256` hybrid suite (Section 8.10); a future suite (e.g. `ECDH-AES-GCM`) is the planned path for compact keys.

### 11.2.2 RSA-PSS-SHA256

RSA-PSS with SHA-256 is the signing primitive. PSS is preferred over PKCS#1 v1.5 signatures because PSS's randomized padding is provably secure under standard assumptions, while PKCS#1 v1.5 has known issues with implementations that produce or accept non-canonical signatures.

A salt length of 32 bytes (the SHA-256 digest length) is mandated by Section 8.6. This is the most conservative reasonable salt length.

### 11.2.3 Key sizes

The minimum modulus size in `v1` is 2048 bits. NIST SP 800-57 Part 1 Rev 5 estimates that 2048-bit RSA provides approximately 112 bits of security, sufficient through approximately 2030. Implementations that intend to retain message readability past 2030 SHOULD use 3072 or 4096 bits.

Modulus sizes smaller than 2048 are forbidden because 1024-bit RSA is no longer considered secure against well-resourced adversaries.

### 11.2.4 Plaintext-length limits and the hybrid suite

The `RSA-OAEP-SHA256` suite encrypts plaintext directly with RSA-OAEP, which restricts plaintext length to `n - 66` bytes for an `n`-byte modulus. The `RSA-OAEP-AES256GCM-SHA256` suite (Section 8.10) lifts this limit by wrapping a fresh AES-256 key with RSA-OAEP and encrypting the plaintext under AES-256-GCM; its only length constraint is the practical body-size limit of Section 6.5. The hybrid suite adds key-wrap and AEAD handling to the consumer; both suites are registered in `v1` so deployments can choose the minimal direct suite or the unrestricted hybrid suite per message.

## 11.3 Signature verification semantics

`v1` deliberately delivers decrypted plaintext to the application even when signature verification fails or cannot be attempted. The rationale is in Section 10.3.5: dropping unverifiable plaintext would push every conversation through a friction-laden out-of-band setup, undermining the protocol's usability claim. The risk this incurs is that an attacker who controls the recipient's transport could inject ciphertexts with forged claims of authorship. The chosen mitigation is to require the consumer to surface the verification outcome prominently (Section 10.3.4 and 10.3.5).

Applications built on `v1` SHOULD make the verification outcome visually unambiguous and SHOULD NOT permit one-click "trust this sender" workflows that would normalize the `unknown-sender` outcome.

## 11.4 Replay

`v1` carries an `i` (message identifier) field but does not require consumers to track it. An adversary who observes a wire message can replay it and the consumer will decrypt it again, producing the same plaintext. Application-level deduplication based on the `i` field is RECOMMENDED for any consumer where replay would cause a user-visible problem (e.g. duplicate notifications, duplicate financial instructions). Such deduplication is out of scope for `v1`.

## 11.5 Hash collisions

A `key_hash` is a 32-byte SHA-256 digest. The probability that two independently generated RSA keys produce the same SPKI digest is bounded by the birthday bound for SHA-256, approximately `2^-128` for 2^64 generated keys. This is negligible for any realistic deployment.

A deliberately constructed hash collision attack against SHA-256 would require approximately `2^128` work, which is infeasible. If SHA-256 is later compromised, the `key_hash` algorithm of Section 9 must be replaced; the path is a new wire version, not a `v1` suite-registry update, because changing the hash would invalidate every existing `s` and `r` body value.

## 11.6 Decompression bombs

The decompression size budget of Section 5.4 (1 MiB by default) prevents a malicious producer from emitting a small wire message that decompresses to gigabytes, exhausting the consumer's memory or pinning a CPU. Implementations MUST enforce the budget at the streaming layer (i.e. abort once the budget is exceeded, rather than allocating then checking).

## 11.7 UTF-8 validity

Plaintext decoded after the suite's decryption procedure is required to be valid UTF-8 (Section 8.5 step 5 for `RSA-OAEP-SHA256`; Section 8.10.5 step 10 for the hybrid suite). This prevents an attacker who can manipulate ciphertext from delivering a bytestring that exploits parser quirks in the receiving application. A consumer that receives invalid UTF-8 MUST surface `decryption-failed`; the plaintext is not displayed.

NFC normalization (Section 2.2.2) is performed on the producer side. The consumer does not re-normalize; an adversary cannot exploit normalization mismatches at the consumer because the consumer does not normalize at all.

## 11.8 Side channels

Both decryption paths are sensitive to timing side channels: OAEP padding/length checks (RFC 8017 Section 7.1.2, mandated constant-time), and for the hybrid suite the AES-GCM tag check and the wrap-key length check of Section 8.10.5. Implementations that use modern cryptographic libraries (Python `cryptography`, OpenSSL 1.1.1+, BoringSSL, Web Crypto on modern browsers) inherit constant-time treatment for both primitives. Implementations that hand-roll OAEP decoding or AEAD tag verification inherit nothing and MUST treat side channels as a first-order design concern.

Implementations MUST NOT distinguish `decryption-failed` sub-causes by error message, log line, or HTTP status code at any boundary an adversary can observe. Section 10.4 makes this normative.

## 11.9 Key storage

This specification does not mandate a key-storage format. Producers and consumers MUST keep private keys confidential. The companion (informative) `schemas/v1/keystore.schema.json` describes a recommended JSON keystore in which private keys are encrypted at rest using a passphrase-derived AES-256-GCM key. Implementations that adopt the schema SHOULD use Argon2id for the passphrase KDF rather than PBKDF2; the wider community has moved toward Argon2id since the keystore format was first sketched. PBKDF2 with a high iteration count remains acceptable but is not preferred.

## 11.10 Quantum threats

RSA is broken by a sufficiently large quantum computer. Stored ciphertexts captured today and held until a quantum adversary becomes available are decryptable retroactively (the "harvest-now-decrypt-later" model).

Users for whom this is a relevant threat should reduce their exposure by rotating keys periodically and avoiding storage of long-lived archives of `v1` messages outside their direct control. A future post-quantum suite (e.g. an ML-KEM/ML-DSA-based suite identifier in the body's `a` field) is anticipated.

## 11.11 Out-of-band verification

The trust users place in a `key_hash` rests entirely on the channel by which they obtained the corresponding public key. PlainCloak does not provide a key-discovery service. Implementations SHOULD expose a way to display a recipient's `key_hash` to the user before the user adds the recipient to contacts so that the hash can be verified by voice, in person, or via an independent channel.

A short-fingerprint variant suitable for human comparison is not part of `v1`. Implementations that wish to display a shorter form for UX purposes SHOULD show both the short form and the full 64-character hash and SHOULD NOT permit trust decisions to be made on the short form alone.
