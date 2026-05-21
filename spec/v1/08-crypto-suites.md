# 8. Cryptographic Suites

This section specifies the cryptographic algorithms, parameters, and key encodings used by `v1`. The body field `a` (Section 6.2.1) selects the suite; `v1` registers `RSA-OAEP-SHA256` (REQUIRED baseline) and `RSA-OAEP-AES256GCM-SHA256` (RECOMMENDED hybrid), per the registry of Section 8.1.

## 8.1 Suite registry

The set of valid `a` values is governed by an open registry. New suites are added under the Specification Required policy of Section 13. The registry is mirrored in machine-readable form at `schemas/v1/algorithms.json`. The currently registered `v1` entries are:

| Identifier | Encryption | Signing | Status |
|------------|-----------|---------|--------|
| `RSA-OAEP-SHA256` | RSA-OAEP with SHA-256 / MGF1-SHA-256 [RFC 8017] | RSA-PSS with SHA-256 / MGF1-SHA-256 [RFC 8017] | REQUIRED (core profile baseline) |
| `RSA-OAEP-AES256GCM-SHA256` | Hybrid: RSA-OAEP-SHA256 wraps a fresh AES-256 key; AES-256-GCM encrypts the plaintext [RFC 8017] [RFC 7518 §4.3] [NIST SP 800-38D] | RSA-PSS with SHA-256 / MGF1-SHA-256 [RFC 8017] | RECOMMENDED |

Future revisions of `v1` MAY add further suites such as `X25519-AES256GCM-ED25519`, post-quantum hybrids, or other primitives via the registry policy of Section 13. Such additions do NOT trigger a wire-version bump; consumers that do not yet support a newly registered suite reject it with `unknown-suite`, which is the correct behavior under this open-registry model. Each new suite registration MUST specify the byte layout of `p` and `g` (Section 6.2.6, 6.2.7), the public-key encoding under SPKI DER (Section 8.3.1), and any plaintext-length or AEAD-AAD semantics; see Section 13.2.

## 8.2 Key types

The `RSA-OAEP-SHA256` suite uses RSA keys for both encryption (recipient's public key) and signing (sender's private key). The recipient and sender MAY hold the same key pair, but typical use has distinct identities.

A producer or consumer MUST support RSA modulus sizes of **2048**, **3072**, and **4096** bits. Implementations MAY support additional sizes; if they do, those sizes MUST be powers of 2 multiplied by an integer in `{1, 2, 3, 4}` and MUST NOT be smaller than 2048 bits. Modulus sizes smaller than 2048 bits are forbidden and MUST be rejected.

The public exponent `e` MUST be `65537` (`0x010001`). Implementations MUST reject keys with any other public exponent.

## 8.3 Key encoding

### 8.3.1 Public keys

Public keys are encoded in **SubjectPublicKeyInfo (SPKI) DER** as defined in [RFC 5280 Section 4.1.2.7]. When stored on disk or transferred between humans, a public key MAY be wrapped in PEM with the label `PUBLIC KEY`:

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxxxxxxxx...
-----END PUBLIC KEY-----
```

This is the standard "X.509 SubjectPublicKeyInfo" PEM format that OpenSSL emits via `openssl rsa -pubout` or `openssl pkey -pubout`. PKCS#1 RSAPublicKey-only PEM (`BEGIN RSA PUBLIC KEY`) is **not** acceptable; producers MUST emit SPKI and consumers MAY accept SPKI only.

The bytes hashed by Section 9 to produce a `key_hash` are the **DER bytes** of the SPKI, with no PEM framing, no headers, and no whitespace.

### 8.3.2 Private keys

Private keys are encoded in **PKCS#8 PrivateKeyInfo DER** as defined in [RFC 5958]. When stored on disk, a private key MAY be wrapped in PEM with the label `PRIVATE KEY`:

```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
-----END PRIVATE KEY-----
```

PKCS#1 RSAPrivateKey-only PEM (`BEGIN RSA PRIVATE KEY`) is **not** acceptable; producers MUST emit PKCS#8 and consumers MAY accept PKCS#8 only.

Encrypted-at-rest storage of private keys is implementation-defined. The on-wire `v1` protocol does not specify any private-key transport; private keys never leave the device under normal operation.

## 8.4 Encryption (RSA-OAEP-SHA256)

When `a` is `RSA-OAEP-SHA256`, the body's `p` field is produced by RSA-OAEP encryption with the parameters:

| Parameter | Value |
|-----------|-------|
| Hash function | SHA-256 |
| Mask Generation Function | MGF1 with SHA-256 |
| Label | The empty octet string |
| Modulus | The recipient's RSA public modulus |

Procedurally:

1. Let `K` be the recipient's RSA public key.
2. Let `m` be the UTF-8 encoding of the plaintext (after NFC normalization per Section 2.2.2).
3. Let `c` = `RSAES-OAEP-ENCRYPT(K, m, label = empty)` per RFC 8017 Section 7.1.1, with the parameters above.
4. The body's `p` field is the Base64 encoding of `c` per Section 2.4.

The maximum plaintext length permitted by RSA-OAEP-SHA256 with an `n`-byte modulus is `n - 2 - 2 * 32 = n - 66` bytes. For RSA-2048 (`n = 256`), the maximum is **190 bytes** of UTF-8 plaintext. For RSA-4096 (`n = 512`), the maximum is **446 bytes**.

The `RSA-OAEP-SHA256` suite encrypts plaintext directly under RSA-OAEP and has no hybrid construction; a producer using this suite MUST reject plaintexts longer than the modulus's RSA-OAEP capacity. For arbitrary-length messages, use the `RSA-OAEP-AES256GCM-SHA256` hybrid suite (Section 8.10), which is registered in `v1` and RECOMMENDED for general use.

## 8.5 Decryption (RSA-OAEP-SHA256)

When `a` is `RSA-OAEP-SHA256`, the body's `p` field is decrypted by:

1. Let `K_priv` be the consumer's RSA private key whose corresponding public key has SHA-256 SPKI digest equal to the body's `r` field (Section 9).
2. Let `c` be the Base64 decoding of `p` per Section 2.4.
3. Verify that `len(c)` equals the modulus byte length of `K_priv`. If not, reject as `decryption-failed`.
4. Let `m` = `RSAES-OAEP-DECRYPT(K_priv, c, label = empty)` per RFC 8017 Section 7.1.2.
5. Decode `m` as UTF-8. If decoding fails, reject as `decryption-failed`.
6. The decoded UTF-8 string is the plaintext.

Implementations MUST handle OAEP decoding errors as constant-time as the underlying library permits. A consumer MUST NOT expose, via timing or distinct error messages, whether the failure was a length mismatch, a padding error, or a UTF-8 error. All `decryption-failed` outcomes MUST be reported with the same error category.

Implementations SHOULD NOT post-process the decrypted plaintext (e.g. by re-normalizing). The plaintext is delivered to the application exactly as decoded from UTF-8.

## 8.6 Signing (RSA-PSS-SHA256)

The signing component of the `RSA-OAEP-SHA256` suite produces the body's `g` field as RSA-PSS with the parameters:

| Parameter | Value |
|-----------|-------|
| Hash function | SHA-256 |
| Mask Generation Function | MGF1 with SHA-256 |
| Salt length | 32 bytes (equal to the SHA-256 digest length) |
| Modulus | The sender's RSA private modulus |
| Trailer field | `0xBC` (default per RFC 8017) |

Procedurally, the producer computes:

1. Let `K_priv` be the sender's RSA private key.
2. Let `C` be the canonical-form bytes per Section 7.
3. Let `sig` = `RSASSA-PSS-SIGN(K_priv, C)` per RFC 8017 Section 8.1.1, with the parameters above.
4. The body's `g` field is the Base64 encoding of `sig` per Section 2.4.

The producer MUST use a fresh random salt of exactly 32 bytes for every signature. PSS remains secure even with a fixed or zero-length salt, so salt reuse is not an attack in practice; `v1` mandates a fresh 32-byte salt for simplicity and defense in depth.

## 8.7 Verifying (RSA-PSS-SHA256)

The consumer verifies the signature by:

1. Let `K_pub` be the sender's RSA public key whose SHA-256 SPKI digest equals the body's `s` field (Section 9). If no such key is available to the consumer, signature verification is **skipped** and the consumer surfaces the `unknown-sender` outcome of Section 10. Verification is not attempted with an unrelated key.
2. Let `sig` be the Base64 decoding of the body's `g` field per Section 2.4.
3. Verify that `len(sig)` equals the modulus byte length of `K_pub`. If not, the signature is invalid.
4. Let `C` be the canonical-form bytes per Section 7.
5. Let `valid` = `RSASSA-PSS-VERIFY(K_pub, C, sig)` per RFC 8017 Section 8.1.2 with the parameters of 8.6.
6. If `valid` is `false`, the signature is invalid; the consumer surfaces the `signature-invalid` outcome of Section 10.

Verification of an invalid signature MUST NOT prevent decryption of the `p` field; Section 10 specifies that an authenticated-but-decrypted message is presented to the user with a verification-failure indication, not silently dropped.

## 8.8 Algorithm parameter agility

Within a registered suite, the parameters of 8.4, 8.6, and 8.7 are fixed by that registration. A consumer MUST NOT permit alternative hash functions, MGF choices, or salt lengths to influence verification of a given suite. A revision that wishes to vary these parameters MUST register a new suite identifier (e.g. `RSA-OAEP-SHA384`) per Section 13. Multiple registered suites with different parameter choices may coexist within `v1`.

## 8.9 Library guidance

The `v1` parameters correspond to the defaults of widely deployed RSA-OAEP and RSA-PSS implementations. Specifically:

- Python `cryptography`: `padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)` for OAEP; `padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32)` for PSS.
- JavaScript Web Crypto: `RSA-OAEP` algorithm with `hash: "SHA-256"` and an empty `label`; `RSA-PSS` algorithm with `hash: "SHA-256"` and `saltLength: 32`.
- OpenSSL: `EVP_PKEY_CTX_set_rsa_padding(..., RSA_PKCS1_OAEP_PADDING)` with `EVP_PKEY_CTX_set_rsa_oaep_md(..., EVP_sha256())` and `EVP_PKEY_CTX_set_rsa_mgf1_md(..., EVP_sha256())`; for PSS, `RSA_PKCS1_PSS_PADDING` with `RSA_PSS_SALTLEN_DIGEST` (which is 32 for SHA-256).

These mappings are informative. The normative requirement is that the produced bytes match RFC 8017 with the parameters of 8.4 and 8.6.

## 8.10 Hybrid encryption (`RSA-OAEP-AES256GCM-SHA256`)

This section specifies the `RSA-OAEP-AES256GCM-SHA256` suite. The suite reuses the RSA key material, key encoding, key-identification, and signing components of `RSA-OAEP-SHA256` (Sections 8.2, 8.3, 8.6, 8.7, 9). It differs only in the `p` field: the asymmetric primitive wraps a fresh symmetric key, and the plaintext is encrypted under AES-256-GCM. The plaintext length is therefore not capped by the RSA modulus.

The construction is the JOSE `alg: RSA-OAEP-256` + `enc: A256GCM` pairing of [RFC 7518 §4.3, §5.3] and is also the shape used by CMS [RFC 5652] and S/MIME [RFC 8551].

### 8.10.1 Suite parameters

| Component | Parameter | Value |
|-----------|-----------|-------|
| KEM (key wrap) | Primitive | RSAES-OAEP [RFC 8017 §7.1] |
| KEM | Hash function | SHA-256 |
| KEM | Mask Generation Function | MGF1 with SHA-256 |
| KEM | Label | The empty octet string |
| KEM | Modulus | The recipient's RSA public modulus |
| AEAD | Primitive | AES-256-GCM [NIST SP 800-38D] |
| AEAD | Key length | 256 bits (32 bytes) |
| AEAD | Nonce length | 96 bits (12 bytes) |
| AEAD | Tag length | 128 bits (16 bytes) |
| AEAD | AAD source | Canonical-form-without-p (see 8.10.4) |
| Signing | Primitive | RSASSA-PSS-SHA256 (unchanged from Section 8.6) |

The KEM and AEAD parameters are fixed by this registration. A consumer MUST NOT permit alternative hashes, MGF choices, nonce sizes, tag sizes, or AEAD modes to influence processing of an `RSA-OAEP-AES256GCM-SHA256` body. A revision that wishes to vary these parameters MUST register a new suite identifier per Section 13.

### 8.10.2 Encryption procedure

When `a` is `RSA-OAEP-AES256GCM-SHA256`, the producer MUST execute the following steps:

1. Let `K_pub` be the recipient's RSA public key.
2. Let `m` be the UTF-8 encoding of the plaintext after NFC normalization per Section 2.2.2.
3. Generate `K`, a fresh 32-byte symmetric key, from a cryptographically secure random source.
4. Generate `N`, a fresh 12-byte AEAD nonce, from a cryptographically secure random source.
5. Let `wrapped_K` = `RSAES-OAEP-ENCRYPT(K_pub, K, label = empty)` per RFC 8017 §7.1.1 with the KEM parameters of 8.10.1. The length of `wrapped_K` is exactly the modulus byte length of `K_pub`.
6. Construct the AAD as specified in 8.10.4.
7. Let `(ct, tag)` = `AES-256-GCM-ENCRYPT(K, N, m, AAD)` per [NIST SP 800-38D]. The tag is exactly 16 bytes.
8. Frame the `p` payload bytes as the concatenation `wrapped_K || N || ct || tag`. The total length is `len(wrapped_K) + 12 + len(m) + 16`.
9. Base64-encode the framed bytes per Section 2.4 to produce the body's `p` field.

Producers MUST NOT reuse `K` or `N` across messages, even when the recipient is the same. Both values MUST come from a cryptographically secure random source for every produced message.

This suite imposes no per-key plaintext length cap. A producer MUST still respect the practical body size limit of Section 6.5 (64 KiB recommended); a producer SHOULD reject plaintexts that would cause the assembled body to exceed that limit.

### 8.10.3 `p` byte layout

The Base64 decoding of `p` is the concatenation of four contiguous segments at fixed offsets. There is no separator, no length prefix, and no framing metadata between segments; the boundaries are determined entirely by the fixed widths below:

```
offset 0          offset M       offset M+12              offset L-16    offset L
  |                  |                |                       |             |
  v                  v                v                       v             v
  +------------------+----------------+-----------------------+-------------+
  |    wrapped_K     |     nonce      |      ciphertext       |     tag     |
  +------------------+----------------+-----------------------+-------------+
  |<--- M bytes ---->|<-- 12 bytes -->|<-- L - M - 28 bytes ->|<- 16 bytes->|
```

| Segment | Offset (bytes) | Length (bytes) | Contents |
|---------|----------------|----------------|----------|
| `wrapped_K` | `0` | `M` = modulus byte length of recipient key (256 / 384 / 512 for RSA-2048 / 3072 / 4096) | RSAES-OAEP ciphertext of the 32-byte AEAD key |
| `nonce` | `M` | `12` | AEAD nonce |
| `ciphertext` | `M + 12` | `L - M - 28` | AEAD ciphertext (same length as plaintext) |
| `tag` | `L - 16` | `16` | AEAD authentication tag |

`L` is the total decoded length of `p`. Three of the four widths (`12`, `16`, and "the rest") are constants of the suite. The fourth width `M` is the recipient's RSA modulus byte length, which the consumer knows because the body's `r` field selects the private key whose modulus determines `M`. The framing is therefore unambiguous from the suite identifier and the recipient key alone, satisfying Section 13.2.1 item 6.

A consumer MUST reject `p` if:

- `L < M + 12 + 16` (no room for the four mandatory segments), or
- `M` does not match the modulus byte length of the matched private key.

### 8.10.4 AAD construction

The AEAD additional-authenticated-data input is the UTF-8 encoding of the canonical-form string of Section 7.2 with the `p` segment replaced by the empty string. Concretely, the AAD is:

```
utf-8("<wire_version_int>:<a>:<i>:<t>:<s>:<r>:")
```

with the trailing colon retained. The omission of `p` is required because `p` itself contains the AEAD output and cannot be computed before the AEAD call. The signature of Section 8.6 still binds the full canonical form (including `p`); the AEAD AAD binds the metadata independently as defense in depth.

Worked example for the test-fixture inputs of Appendix A:

```
1:RSA-OAEP-AES256GCM-SHA256:b5ca2440-fbb0-4e33-83af-4222bf2b0bf5:1746789123456:b3cef20ec636c4125ae580da93dc0f13bdcdb1c3eea907543ed35ad52e024aee:1bf44bedd390cd114d5511c53286330f29c9fe70a4ab86118731860898ef88da:
```

### 8.10.5 Decryption procedure

When `a` is `RSA-OAEP-AES256GCM-SHA256`, the consumer MUST execute the following steps:

1. Let `K_priv` be the consumer's RSA private key whose corresponding public key has SHA-256 SPKI digest equal to the body's `r` field (Section 9).
2. Let `M` be the modulus byte length of `K_priv`.
3. Let `payload` be the Base64 decoding of `p` per Section 2.4.
4. Verify `len(payload) >= M + 28`. If not, reject as `decryption-failed`.
5. Split `payload` into `wrapped_K = payload[0..M]`, `N = payload[M..M+12]`, `ct = payload[M+12..len(payload)-16]`, `tag = payload[len(payload)-16..]`.
6. Let `K` = `RSAES-OAEP-DECRYPT(K_priv, wrapped_K, label = empty)` per RFC 8017 §7.1.2. If decryption fails, reject as `decryption-failed`.
7. Verify `len(K) == 32`. If not, reject as `decryption-failed`.
8. Construct the AAD as specified in 8.10.4.
9. Let `m` = `AES-256-GCM-DECRYPT(K, N, ct, tag, AAD)`. If the tag check fails, reject as `decryption-failed`.
10. Decode `m` as UTF-8. If decoding fails, reject as `decryption-failed`.
11. The decoded UTF-8 string is the plaintext.

Implementations MUST handle every failure mode of steps 4 through 10 as the single `decryption-failed` outcome of Section 10.3.3, with no distinguishing timing, error message, or log line at the public boundary. The constant-time requirements of Section 8.5 apply unchanged.

The signing component is `RSASSA-PSS-SHA256`, identical to Sections 8.6 and 8.7. The producer signs the canonical form of Section 7.2 (which contains the final Base64 `p` field) with `sender_priv`; the consumer verifies against `sender_pub`. No changes are required from those sections.

### 8.10.6 Library guidance

The `v1` parameters for this suite correspond to the defaults of widely deployed RSA-OAEP and AES-GCM implementations. Specifically:

- Python `cryptography`:
  - Wrap: `recipient_pub.encrypt(K, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))`.
  - AEAD: `cryptography.hazmat.primitives.ciphers.aead.AESGCM(K).encrypt(nonce, plaintext, aad)`; tag is appended to the ciphertext output. `AESGCM(K).decrypt(nonce, ct_with_tag, aad)` reverses it.
- JavaScript Web Crypto:
  - Wrap: `crypto.subtle.encrypt({ name: "RSA-OAEP" }, recipient_pub, K)`.
  - AEAD: `crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce, tagLength: 128, additionalData: aad }, K_ck, plaintext)`; Web Crypto appends the tag to the ciphertext output. `crypto.subtle.decrypt(...)` reverses it.
- OpenSSL: `EVP_PKEY_encrypt` / `EVP_PKEY_decrypt` with `RSA_PKCS1_OAEP_PADDING` plus SHA-256 OAEP/MGF1 for the wrap; `EVP_EncryptInit_ex` / `EVP_DecryptInit_ex` with `EVP_aes_256_gcm()` for the AEAD; tag handled via `EVP_CTRL_GCM_GET_TAG` and `EVP_CTRL_GCM_SET_TAG`.

These mappings are informative. The normative requirement is that the produced bytes match RFC 8017 (for the wrap) and NIST SP 800-38D (for AES-GCM) with the parameters of 8.10.1.
