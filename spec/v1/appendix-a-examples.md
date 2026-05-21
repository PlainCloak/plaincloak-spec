# Appendix A. Worked Example

This appendix walks through a complete `v1` produce-then-consume cycle using illustrative inputs. The goal is to make every protocol step concrete; the values shown are illustrative excerpts (RSA outputs are randomized, so the exact byte-level values cannot be reproduced from the inputs alone). For byte-stable cases, see `test-vectors/v1/`.

## A.1 Inputs

The producer is "Bob" using the 4096-bit key whose PEM is at `test-vectors/v1/fixtures/keys/bob-rsa4096-priv.pem`. The recipient is "Alice" with the 2048-bit key at `test-vectors/v1/fixtures/keys/alice-rsa2048-pub.pem`.

The plaintext message is:

```
Hello Alice. RSA-2048 roundtrip test.
```

The producer-chosen random and time inputs are:

| Body field | Illustrative value |
|------------|--------------------|
| `i` | `b5ca2440-fbb0-4e33-83af-4222bf2b0bf5` |
| `t` | `1746789123456` |

## A.2 Producer steps

**Step 1: Validate algorithm.** `RSA-OAEP-SHA256` is registered in Section 8.1.

**Step 2: Validate keys.** Bob's private key is RSA-4096 (acceptable per Section 8.2). Alice's public key is RSA-2048 (acceptable).

**Step 3: Normalize and encode plaintext.** The plaintext is already NFC-normalized ASCII. Its UTF-8 byte length is 37, well below the OAEP capacity of 190 bytes for RSA-2048.

**Step 4: Length check.** 37 bytes <= 190 bytes; producer continues.

**Step 5: Encrypt.** Apply RSA-OAEP-SHA256 using Alice's public key. The ciphertext is 256 bytes (RSA-2048 modulus byte length). Base64-encode it; the result is the body's `p` field - approximately 344 Base64 characters.

**Step 6: Compute `s`.** SHA-256 of Bob's SPKI DER, hex-encoded lowercase. From the test fixtures:

```
b3cef20ec636c4125ae580da93dc0f13bdcdb1c3eea907543ed35ad52e024aee
```

**Step 7: Compute `r`.** SHA-256 of Alice's SPKI DER:

```
1bf44bedd390cd114d5511c53286330f29c9fe70a4ab86118731860898ef88da
```

**Step 8-9.** `i` and `t` are taken from A.1.

**Step 10: Construct canonical form.** Per Section 7.2, prepending the wire version integer (`1` because the producer will emit a `v1` envelope):

```
1:RSA-OAEP-SHA256:b5ca2440-fbb0-4e33-83af-4222bf2b0bf5:1746789123456:b3cef20ec636c4125ae580da93dc0f13bdcdb1c3eea907543ed35ad52e024aee:1bf44bedd390cd114d5511c53286330f29c9fe70a4ab86118731860898ef88da:<p>
```

(Where `<p>` is the exact `p` string from step 5.)

**Step 11: Sign.** Apply RSA-PSS-SHA256 using Bob's private key over the UTF-8 bytes of the canonical form. The signature is 512 bytes (RSA-4096 modulus byte length). Base64-encode it; the result is the body's `g` field - approximately 684 Base64 characters.

**Step 12: Assemble body.** The seven-field JSON object:

```json
{
  "a": "RSA-OAEP-SHA256",
  "i": "b5ca2440-fbb0-4e33-83af-4222bf2b0bf5",
  "t": 1746789123456,
  "s": "b3cef20ec636c4125ae580da93dc0f13bdcdb1c3eea907543ed35ad52e024aee",
  "r": "1bf44bedd390cd114d5511c53286330f29c9fe70a4ab86118731860898ef88da",
  "p": "<base64-344-chars>",
  "g": "<base64-684-chars>"
}
```

**Step 13: Serialize JSON.** Compact (no whitespace). The body is approximately 1180 bytes (single-letter keys save roughly 100 bytes versus a verbose-key body of equivalent content).

**Step 14: Compress with Brotli.** Quality 11, window 22. The compressed size is approximately 1080 bytes.

**Step 15: Base62-encode.** Approximately 1480 characters.

**Step 16: Prepend envelope.** The final wire message:

```
PLAINCLOAK:v1:BR:CD2H2A1vIwypq4CLQVVAXvKfQEpe...
```

The complete wire string for this exact set of inputs is captured in `test-vectors/v1/verification/01-rsa2048-roundtrip.json`.

## A.3 Consumer steps

The consumer holds Alice's private key in its keystore and Bob's public key in its contacts.

**Step 1-9 of Section 3.3.** Parse envelope (`PLAINCLOAK`, `v1`, `BR`), retain the wire version token for canonical-form reconstruction, Base62-decode, Brotli-decompress, JSON-parse, validate against `message.schema.json`.

**Step 1 (Section 10.2): Recipient lookup.** The body's `r` field is `1bf4...88da`. Alice's keystore contains a private key whose public-key hash matches; the consumer continues with that key.

**Step 2: Decrypt.** RSA-OAEP-SHA256 decryption with Alice's private key, applied to the Base64-decoded `p` field, recovers the 37-byte UTF-8 plaintext `Hello Alice. RSA-2048 roundtrip test.`.

**Step 3: Reconstruct canonical form.** From the body's six signed fields and the wire version integer `1`, the consumer rebuilds the same canonical-form string the producer signed.

**Step 4: Sender lookup.** The body's `s` field is `b3ce...4aee`. The consumer's contacts contain Bob's public key with that hash.

**Step 4.1: Verify signature.** RSA-PSS-SHA256 verification with Bob's public key, over the UTF-8 canonical-form bytes, against the Base64-decoded `g` field. The verification returns `true`.

**Step 5: Surface to application.** Outcome `verified`; plaintext `Hello Alice. RSA-2048 roundtrip test.` is delivered with the verified-from-Bob label.

## A.4 Failure-mode walkthroughs

The remaining outcomes of Section 10.3 are exercised by `test-vectors/v1/verification/03-tampered-payload.json`, `04-tampered-signature.json`, `05-wrong-recipient.json`, and `06-unknown-sender.json`. Each follows the same parsing path but diverges at one of the consumer steps:

- **Tampered payload.** Step 2 (decrypt) fails because the OAEP padding check rejects modified ciphertext. Outcome: `decryption-failed`. No plaintext.
- **Tampered signature.** Step 2 succeeds (the `p` field is unchanged); step 4.1 fails because the signature does not verify. Outcome: `signature-invalid`. Plaintext IS surfaced together with the failure label.
- **Wrong recipient.** Step 1 finds no matching private key. Outcome: `wrong-recipient`. No decryption attempted.
- **Unknown sender.** Step 4 finds no matching contact. Step 4.2 skips verification. Outcome: `unknown-sender`. Plaintext IS surfaced together with the unverifiable label.

In each failure case, the outcome label is the security-relevant signal, not the absence or presence of plaintext alone.

## A.5 Hybrid-suite example (`RSA-OAEP-AES256GCM-SHA256`)

This walkthrough reuses the keys, `i`, `t`, `s`, and `r` of A.1 but selects the hybrid suite of Section 8.10. The illustrative plaintext is deliberately too long for direct RSA-OAEP under RSA-2048 (over 190 bytes) to demonstrate the lifted ceiling:

```
Hello Alice. This is a longer message than RSA-OAEP-SHA256 alone could carry to your RSA-2048 key. The hybrid suite encrypts the plaintext under a fresh AES-256-GCM key and uses RSA only to wrap that key, so the plaintext length is bounded by Section 6.5 rather than by the modulus.
```

UTF-8 length: 286 bytes. Under `RSA-OAEP-SHA256` the producer would have failed at step 4 of Section 10.1 with `plaintext-too-large` (cap 190 bytes for RSA-2048). Under `RSA-OAEP-AES256GCM-SHA256` the producer continues.

**Encryption (Section 8.10.2).**

1. `K` is generated as a fresh 32-byte AES key from a CSPRNG (concrete bytes vary per run).
2. `N` is generated as a fresh 12-byte AEAD nonce.
3. `wrapped_K = RSAES-OAEP-ENCRYPT(alice_pub, K, label = empty)`. Length: 256 bytes (RSA-2048 modulus byte length).
4. AAD = `utf-8("1:RSA-OAEP-AES256GCM-SHA256:b5ca2440-fbb0-4e33-83af-4222bf2b0bf5:1746789123456:b3cef20ec636c4125ae580da93dc0f13bdcdb1c3eea907543ed35ad52e024aee:1bf44bedd390cd114d5511c53286330f29c9fe70a4ab86118731860898ef88da:")`. Length: 209 bytes.
5. `(ct, tag) = AES-256-GCM-ENCRYPT(K, N, plaintext_utf8, AAD)`. `len(ct) = 286`, `len(tag) = 16`.
6. The framed `p` payload is `wrapped_K || N || ct || tag`, total `256 + 12 + 286 + 16 = 570` bytes. Base64-encoded `p` is approximately 760 characters.

**Signing (unchanged from Section 8.6).** The producer constructs the canonical form per Section 7.2 over the seven fields (`a` is now `RSA-OAEP-AES256GCM-SHA256`, `p` is the Base64 string from step 6) and signs it with Bob's RSA-4096 private key. The signature is 512 bytes.

**Wire output.** After body assembly, Brotli compression, and Base62 encoding, the producer emits a single `PLAINCLOAK:v1:BR:<base62>` string. The exact wire string for these inputs is captured in `test-vectors/v1/verification/07-rsa2048-hybrid-roundtrip.json` (with longer plaintext locked by `test-vectors/v1/verification/09-hybrid-long-plaintext.json`).

**Consumer.** The consumer matches `r` to Alice's private key, decodes `p`, splits at the fixed offsets (`wrapped_K` is the first 256 bytes, `nonce` the next 12, `tag` the last 16, `ct` everything between), RSA-decrypts the wrap to recover `K`, reconstructs the AAD, runs `AES-256-GCM-DECRYPT(K, N, ct, tag, AAD)`, and decodes UTF-8. The outcome with Bob in contacts is `verified`; the plaintext is delivered.
