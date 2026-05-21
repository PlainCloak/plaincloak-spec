# 10. Producer and Consumer Behavior

This section specifies, as numbered procedures, the steps a `v1` producer takes to construct a wire message and the steps a `v1` consumer takes to process one. The procedures combine the rules of Sections 3 through 9 into normative end-to-end algorithms.

## 10.1 Producer

A `v1` producer is invoked with:

- `plaintext` - a Unicode string (the user's message).
- `sender_priv` - the producer's RSA private key, with corresponding public key `sender_pub`.
- `recipient_pub` - the recipient's RSA public key.
- `suite` - the suite identifier (the value that will be placed in the body's `a` field); for `v1` this is one of `"RSA-OAEP-SHA256"` or `"RSA-OAEP-AES256GCM-SHA256"` (Section 8.1).

The producer MUST execute the following steps in order:

1. Validate that `suite` is a member of the suite registry (Section 8.1). If not, fail with `unknown-suite`.
2. Validate that `sender_priv` and `recipient_pub` are RSA keys whose modulus size satisfies Section 8.2. If not, fail with `invalid-key`.
3. Normalize `plaintext` to Unicode NFC per Section 2.2.2 and encode the result as UTF-8. Let `m` be the resulting byte string.
4. Enforce the suite's plaintext-length rule:
   - For `RSA-OAEP-SHA256`: verify that `len(m)` does not exceed the maximum permitted by the recipient's modulus per Section 8.4 (e.g. 190 bytes for RSA-2048). If exceeded, fail with `plaintext-too-large`.
   - For `RSA-OAEP-AES256GCM-SHA256`: there is no per-key cap (Section 8.10.2). The producer SHOULD reject plaintexts that would cause the assembled body to exceed the practical size limit of Section 6.5; if it does, fail with `plaintext-too-large`.
5. Encrypt `m` per the rules of the selected suite:
   - For `RSA-OAEP-SHA256`: apply Section 8.4 using `recipient_pub`; Base64-encode the resulting ciphertext to produce the body's `p` field per Section 2.4.
   - For `RSA-OAEP-AES256GCM-SHA256`: apply Section 8.10.2 using `recipient_pub`; Base64-encode the framed `wrapped_K || nonce || ciphertext || tag` to produce the body's `p` field.
6. Compute the sender public-key hash `s` as the SHA-256 SPKI hex digest of `sender_pub` per Section 9.
7. Compute the recipient public-key hash `r` as the SHA-256 SPKI hex digest of `recipient_pub` per Section 9.
8. Generate a fresh UUIDv4 to use as `i` (Section 6.2.2).
9. Read the current Unix wall-clock time in milliseconds for `t` (Section 6.2.3). The producer MAY substitute any non-negative integer; consumers do not validate `t`.
10. Construct the canonical-form string `C` per Section 7.2 from the wire version integer `1`, `a`, `i`, `t`, `s`, `r`, and `p`.
11. Sign `utf-8(C)` using `sender_priv` per Section 8.6. Base64-encode the resulting signature to produce the body's `g` field.
12. Assemble the JSON body with the seven fields of Section 6.2 in any order. The body MUST validate against `schemas/v1/message.schema.json`.
13. Serialize the JSON body to UTF-8 bytes. Whitespace and key order are at the producer's discretion; the producer SHOULD use a compact serialization with no whitespace to minimize wire length.
14. Compress the UTF-8 body bytes with Brotli per Section 5.2.1.
15. Base62-encode the compressed bytes per Section 4.2 to produce the wire payload.
16. Prepend the envelope header `PLAINCLOAK:v1:BR:` and emit the resulting wire message.

The output is a single string conforming to the grammar of Section 3.2. The producer MUST NOT emit any trailing whitespace.

## 10.2 Consumer

A `v1` consumer is invoked with:

- `wire` - a candidate wire message string.
- `keystore` - a collection of the consumer's own RSA private keys, each indexed by the SPKI hex digest of its public key.
- `contacts` - a (possibly empty) collection of trusted public keys, each indexed by the SPKI hex digest of the public key.

The consumer MUST execute the steps of Section 3.3 first to obtain a validated message body. Once the body has passed Section 6.4 validation, the consumer continues:

1. Look up the body's `r` field in `keystore`. If no matching private key is present, fail with the `wrong-recipient` outcome (10.3.2). The consumer MUST NOT attempt decryption with any other key.
2. Decrypt `p` using the matched private key per the suite's decryption procedure (Section 8.5 for `RSA-OAEP-SHA256`, Section 8.10.5 for `RSA-OAEP-AES256GCM-SHA256`). If decryption fails for any reason (length mismatch, OAEP padding failure, AEAD tag failure, wrap-key length mismatch, UTF-8 decoding failure), fail with the `decryption-failed` outcome (10.3.3).
3. Construct the canonical-form string `C` per Section 7.2, using the wire version integer `1` (parsed from the envelope at step 3 of Section 3.3) and the six body fields `a`, `i`, `t`, `s`, `r`, `p`.
4. Look up the body's `s` field in `contacts`.
   1. If a matching public key is present, verify the Base64-decoded `g` field against `utf-8(C)` per Section 8.7. The result is one of the outcomes `verified` (10.3.1) or `signature-invalid` (10.3.4).
   2. If no matching public key is present, the consumer MUST NOT attempt signature verification. The result is the outcome `unknown-sender` (10.3.5).
5. Surface the decrypted plaintext together with the outcome to the application or user. The plaintext MUST be exposed only when paired with the outcome label; an application MUST be able to distinguish `verified` plaintext from `unknown-sender` plaintext from `signature-invalid` plaintext.

A consumer MUST NOT silently treat `signature-invalid` as `verified`. A consumer MUST NOT silently drop the plaintext on `signature-invalid` either; the user is informed and decides what to do with the message.

## 10.3 Outcomes

Section 10.2 produces exactly one of the following five outcomes per processed message. The outcomes are intentionally distinct because each carries different security implications for the application above.

### 10.3.1 `verified`

Decryption succeeded, the sender's public key was found in `contacts`, and the signature verified against the canonical form. The plaintext is authenticated as having been signed by the holder of the sender's private key.

This is the only outcome under which an application SHOULD present the message as "from" the sender without further qualification.

### 10.3.2 `wrong-recipient`

No private key in the consumer's keystore matched the body's `r` field. The message was not encrypted for this consumer. The consumer MUST NOT decrypt; no plaintext is produced.

### 10.3.3 `decryption-failed`

The matched private key did not decrypt the `p` field cleanly. This indicates either a producer bug, a hash collision (negligibly likely but theoretically possible), a corrupt or truncated wire message, or a deliberately tampered `p`. No plaintext is produced.

### 10.3.4 `signature-invalid`

Decryption succeeded, the sender's public key was found, but signature verification returned `false`. This indicates either a tampered body, a swap of `p`/`g` (payload/signature) between two messages, or a bug. The plaintext is delivered to the application paired with this outcome label; applications SHOULD display a prominent warning that authenticity has failed and SHOULD encourage the user to disregard the message content.

### 10.3.5 `unknown-sender`

Decryption succeeded but the sender's public key (identified by the body's `s` field) is not in the consumer's `contacts`. Signature verification cannot be attempted. The plaintext is delivered with this outcome label; applications SHOULD display the plaintext together with a notice that authenticity cannot be verified and that the sender should be added to contacts via an out-of-band channel before trust is extended.

This outcome is the design's deliberate choice: a message from a stranger is delivered, not silently dropped, because dropping unverifiable messages would force every conversation to begin with an explicit out-of-band key exchange, undermining the protocol's "paste anywhere" usability goal. The trust decision is left to the user.

## 10.4 Required and forbidden behaviors

A conforming consumer:

- MUST NOT produce any plaintext when the outcome is `wrong-recipient` or `decryption-failed`.
- MUST present the outcome together with any produced plaintext for `verified`, `signature-invalid`, and `unknown-sender`.
- MUST NOT distinguish `decryption-failed` outcomes by sub-cause in observable behavior (timing, distinct error strings, distinct logs at the public boundary). The `decryption-failed` category is opaque externally.
- MUST NOT verify a signature against any public key other than the one whose SPKI hex digest equals the body's `s` field.
- MUST NOT cache or reuse OAEP randomness, PSS salts, or (for the hybrid suite) the fresh AES-256 key or AES-GCM nonce across messages.

A conforming producer:

- MUST refuse to emit a message whose plaintext exceeds the selected suite's plaintext-length rule: the modulus's OAEP capacity for `RSA-OAEP-SHA256` (Section 8.4), or the practical body-size limit of Section 6.5 for `RSA-OAEP-AES256GCM-SHA256` (Section 8.10.2).
- MUST regenerate `i` for every message; reuse is forbidden.
- MUST NOT emit a wire message whose body fails its own JSON Schema (`schemas/v1/message.schema.json`).
- MUST emit `s` and `r` as lowercase hex; uppercase is non-conforming even though the schema's pattern would forbid it.

## 10.5 Optional producer warnings

A producer SHOULD warn its caller in the following situations even though `v1` does not REQUIRE refusal:

- The recipient's public key was added to contacts more than 365 days ago and has not been re-verified out of band. (Long-trusted keys whose holders' situations may have changed.)
- The plaintext, after NFC normalization, contains characters from Unicode confusable script-mixing classes that may indicate spoofing.
- The producer's clock is more than 24 hours skewed from a reference source. (Affects the `t` field only, not security; users may find their messages display with surprising times otherwise.)

These are informational only and have no effect on the wire protocol.
