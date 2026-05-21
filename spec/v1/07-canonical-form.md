# 7. Canonical Form

This section specifies the **canonical form**: the deterministic byte sequence over which a sender's signature is computed and against which a consumer's signature verification is performed. Two correct implementations MUST produce byte-identical canonical forms for byte-identical input bodies.

## 7.1 Rationale

The canonical form is necessary because JSON does not have a single byte-stable serialization. Whitespace, key order, escape choices, and number formatting all vary between encoders. If implementations signed JSON directly, two correct producers could legitimately produce different signatures for the same logical message, and verifiers would have to reconstruct the producer's exact JSON serialization to verify. The canonical form sidesteps this entirely: a fixed, simple, deterministic string.

The canonical form also includes the wire version as its first segment so that the signature is bound to a specific protocol version. A signature minted under one wire version cannot be reinterpreted as valid under another, even if the body fields are otherwise compatible. This is standard cryptographic domain separation.

## 7.2 Construction

The canonical form covers the wire version (drawn from the envelope of Section 3) plus six of the body's seven fields. The signature field `g` is excluded because it is the output of the signing operation and would be self-referential.

The canonical form is the concatenation, in this fixed order, of the following seven values, separated by the colon character (`U+003A`, byte `0x3A`):

```
wire_version_int : a : i : t : s : r : p
```

Where `wire_version_int` is the integer obtained by stripping the leading `v` from the wire envelope's version token (Section 3) and parsing the remainder as a decimal integer. For `v1` this is the literal string `1`.

Concretely, given a body `B` and a wire version integer `V`, the canonical-form string `C` is:

```
C = str(V) + ":" +
    B.a + ":" +
    B.i + ":" +
    str(B.t) + ":" +
    B.s + ":" +
    B.r + ":" +
    B.p
```

The signed bytes are the UTF-8 encoding of `C`:

```
canonical_bytes = utf-8(C)
```

### 7.2.1 Per-field rules

| Segment | Rule |
|---------|------|
| `wire_version_int` | The decimal representation of the integer obtained from the wire `version` token (Section 3) with the leading `v` removed. For `v1` this is the literal string `1`. |
| `a` | The exact string from the body. For `v1` this is one of `RSA-OAEP-SHA256` or `RSA-OAEP-AES256GCM-SHA256`. |
| `i` | The exact UUIDv4 string from the body, lowercase, in 8-4-4-4-12 form. |
| `t` | The decimal representation of the integer with no leading zeros (except for the value 0 itself), sign, or whitespace. |
| `s` | The exact 64-character lowercase hex string from the body. |
| `r` | The exact 64-character lowercase hex string from the body. |
| `p` | The exact Base64 string from the body, with all padding characters preserved. |

There is no escaping. There is no quoting. There is no JSON. The colon character (`:`) MUST NOT appear inside any of the seven values; the formats specified by Sections 6 and 2 guarantee this for every field except `a`. Future suite identifiers added to the registry MUST NOT contain a colon.

### 7.2.2 No JSON canonicalization

The canonical form is **not** a canonicalized JSON object. Implementations MUST NOT produce a sorted-key JSON object, a JCS-canonicalized object [RFC 8785], or any other JSON form as the signed input. The canonical form is a flat colon-separated string and only that.

This choice is deliberate. Flat string concatenation is unambiguous, trivially implementable in any language, and easy to verify by hand. JSON canonicalization variants are subtly different across implementations and have a history of interoperability bugs.

### 7.2.3 Version source

The `wire_version_int` segment is taken from the wire envelope, not from any body field (the body has no `version` field; see Section 6.3). A producer building the canonical form before assembling the wire MUST use the wire version it intends to emit. A consumer reconstructing the canonical form MUST use the wire version it parsed from the envelope at step 3 of Section 3.3.

A consumer MUST NOT attempt to verify a `v1` signature using a canonical form built with any other version integer, even when reprocessing a stored message. The bound wire version is part of the security guarantee of Section 7.1.

## 7.3 Worked example

Given the wire envelope `PLAINCLOAK:v1:BR:...` and the body:

```json
{
  "a": "RSA-OAEP-SHA256",
  "i": "550e8400-e29b-41d4-a716-446655440000",
  "t": 1746789123456,
  "s": "abc123abc123abc123abc123abc123abc123abc123abc123abc123abc123abc1",
  "r": "def456def456def456def456def456def456def456def456def456def456def4",
  "p": "TmluZXR5IG5pbmU=",
  "g": "(ignored)"
}
```

The canonical form is the single line (with no trailing newline):

```
1:RSA-OAEP-SHA256:550e8400-e29b-41d4-a716-446655440000:1746789123456:abc123abc123abc123abc123abc123abc123abc123abc123abc123abc123abc1:def456def456def456def456def456def456def456def456def456def456def4:TmluZXR5IG5pbmU=
```

The bytes signed are the UTF-8 encoding of that line. Because every character is ASCII, the byte sequence is identical to the ASCII byte representation.

## 7.4 Determinism

For any wire version and body that satisfy Sections 3 and 6, exactly one canonical form exists. Two implementations MUST produce byte-identical canonical-form strings for byte-identical input bodies under the same wire version. The vector at `test-vectors/v1/deterministic/04-canonical-form.json` locks several worked examples that conforming implementations MUST reproduce.

## 7.5 Construction during signing vs. verification

A producer constructs the canonical form **before** computing the signature. The order of operations within the producer is:

1. Choose the body fields except `g`.
2. Determine the wire version that will be emitted (`1` for `v1`).
3. Compute the canonical form per 7.2.
4. Sign `utf-8(C)` with the sender's private key per Section 8.
5. Base64-encode the resulting signature bytes.
6. Place the Base64 signature in the `g` field.

A consumer reconstructs the canonical form **after** decrypting and identifying the sender. The order of operations within the consumer is:

1. Validate the body (Section 6.4).
2. Decrypt the `p` field to obtain the plaintext (Section 8 and Section 10).
3. Resolve the `s` field to a known sender's public key. If unknown, signature verification is skipped per Section 10.
4. Compute the canonical form per 7.2 from the same six body fields the producer used and the wire version parsed from the envelope.
5. Verify `utf-8(C)` against the Base64-decoded `g` field using the sender's public key per Section 8.

The canonical form is deterministic; both sides obtain the same `C` from the same body and wire version.

## 7.6 Failure modes

A canonical-form construction that deviates from 7.2 will produce a signature that fails verification on the consumer side, or fail to verify a producer's signature. Common implementation pitfalls:

- Including `g` in the colon list. Excluded by definition.
- Using a JSON serialization instead of the colon list.
- Inserting whitespace, line breaks, or padding around the separators.
- Encoding integers with a leading zero or a sign.
- Re-encoding `p` (e.g. Base64-decoding then re-encoding before joining). The producer's exact `p` string from the JSON body MUST be used.
- Using uppercase hex for `s` or `r`. The schema enforces lowercase but a buggy producer could violate this; consumers MUST use the literal string from the body, which the schema validation in 6.4 step 7 has already constrained.
- Omitting the leading `wire_version_int` segment, or substituting a hardcoded `1` when processing a non-`v1` envelope (a `v1` consumer never sees a non-`v1` envelope, but cross-version code MUST take the version from the envelope).

The deterministic test vectors at `test-vectors/v1/deterministic/04-canonical-form.json` exercise these pitfalls explicitly.