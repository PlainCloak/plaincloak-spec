# 9. Key Identification

This section specifies how a public key is converted into the 64-character lowercase hex string that appears as `s` (sender) and `r` (recipient) in the message body. The algorithm is identical for both fields and for any other context where a `key_hash` is needed.

## 9.1 Purpose

A `key_hash` provides a stable, compact identifier for a public key without revealing the key itself in any context where the key would be too large to display. Concretely it serves three roles in `v1`:

1. **Recipient routing.** A consumer scans the body's `r` field against its own key store to find the private key that decrypts the message.
2. **Sender lookup.** A consumer scans the body's `s` field against its contacts to find the public key that verifies the signature.
3. **Out-of-band verification.** Two parties exchanging public keys over a separate trusted channel can compare key hashes by sight or by short-string protocol; the 64-character SHA-256 hex string fits the slot of a "fingerprint" in user-visible UI.

## 9.2 Algorithm

The `key_hash` of an RSA public key `K` is computed as:

```
key_hash = lowercase_hex( SHA-256( SPKI_DER( K ) ) )
```

Concretely:

1. Encode `K` in SubjectPublicKeyInfo (SPKI) DER per [RFC 5280 Section 4.1.2.7] and Section 8.3.1.
2. Compute the SHA-256 [FIPS-180-4] digest of those DER bytes. The output is exactly 32 bytes.
3. Hex-encode the 32-byte digest using the lowercase alphabet of Section 2.3. The result is exactly 64 characters.

The bytes hashed are the **DER encoding** of the SPKI structure. They are NOT:

- The PEM-armored representation (which adds Base64 framing and PEM headers).
- The PKCS#1 `RSAPublicKey` structure (which is the inner key and lacks the algorithm identifier wrapping).
- The DER of the modulus and exponent in isolation.
- The textual fingerprint produced by `openssl rsa -modulus` or any similar tool.

Implementations that hash any other byte sequence will produce key hashes that disagree with the canonical algorithm and will fail interoperability.

## 9.3 Worked example

A 2048-bit RSA public key (PEM-armored for display):

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1z+...truncated...AB
-----END PUBLIC KEY-----
```

The DER bytes are obtained by stripping the PEM headers, decoding the Base64 lines into a single byte string, and treating that byte string as the SPKI DER. The SHA-256 of those bytes, hex-encoded lowercase, is the `key_hash`.

The vector at `test-vectors/v1/deterministic/05-key-hash-spki.json` provides several real keypairs and their canonical `key_hash` values. A conforming implementation MUST reproduce the digest values byte-for-byte from the input PEM.

## 9.4 Determinism

For a given RSA key, the SPKI DER encoding is unique up to library-defined tag-and-length canonicalization. Mainstream cryptographic libraries (OpenSSL, BoringSSL, the Python `cryptography` library, the JavaScript Web Crypto API) all produce the same DER bytes for the same key. A conforming implementation MUST NOT introduce variability in the DER bytes (e.g. by setting non-default ASN.1 BER options); strict DER as defined in [X.690] is mandatory.

If two implementations produce different `key_hash` values for the same RSA key, one of them is producing non-canonical DER. The vector at `test-vectors/v1/deterministic/05-key-hash-spki.json` is the authoritative interoperability check.

## 9.5 No truncation

The full 64-character (32-byte) hex string is always used. `v1` does NOT define a truncated short-fingerprint variant. Future versions MAY add a short-form for human-readable verification UI, but message-level fields always carry the full SHA-256 digest.

## 9.6 Use in protocols other than the message body

The same `key_hash` algorithm MAY be used by surrounding tooling - for example, naming key files (`<hash>.pem`), keying entries in a contact book, or producing a QR-code-encoded fingerprint. Such uses are out of scope for this specification but SHOULD use the same algorithm so that a key's identifier is consistent across all surfaces.
