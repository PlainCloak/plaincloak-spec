# 2. Conventions

This section establishes notational, encoding, and presentation conventions used throughout the rest of this specification. Every later section assumes the rules below.

## 2.1 Notation

### 2.1.1 ABNF

Wire-format grammar is given in Augmented Backus-Naur Form as defined in [RFC 5234], with the case-sensitive string-literal extension defined in [RFC 7405]. Where a literal must match a specific case, the `%s"..."` form is used. Where case is irrelevant, a bare `"..."` literal is used.

The complete consolidated grammar lives in `schemas/v1/wire.abnf` and Appendix B. Inline ABNF excerpts in earlier sections are normative; if they disagree with the consolidated grammar, the consolidated grammar wins.

### 2.1.2 JSON Schema

The JSON message body is described in JSON Schema 2020-12 [JSON-SCHEMA-2020-12]. The schema file at `schemas/v1/message.schema.json` is the normative description of the body. Prose in Section 6 is informative where it disagrees with the schema; the schema wins.

### 2.1.3 Code blocks and examples

Examples are illustrative only unless they appear in `test-vectors/v1/`. Inline literal strings are shown in fenced code blocks; bytes are shown as lowercase hex with no `0x` prefix and no separator (e.g. `ab12cd34`).

## 2.2 Strings and bytes

### 2.2.1 Character encoding

All strings produced or consumed by this specification are encoded in UTF-8 [RFC 3629]. Where a string is hashed, signed, or otherwise consumed as bytes, the bytes are the UTF-8 encoding of the string's Unicode code points after the normalization in 2.2.2.

### 2.2.2 Unicode normalization of plaintext

Before encryption, plaintext content provided by a user MUST be normalized to Unicode Normalization Form C (NFC) [UAX-15]. Implementations MUST NOT alter normalization on the consumer side; the decrypted plaintext is delivered exactly as it was encrypted.

NFC is chosen to make `key_hash`-stable representations of human-typed text predictable across platforms (e.g. macOS vs Windows clipboard differences for accented characters) without changing the ciphertext's semantic content.

### 2.2.3 Endianness

The wire format does not encode multi-byte integers directly. Where integers appear (e.g. the body's `t` field, the numeric portion within a UUID), they are serialized as JSON numbers or as defined by the relevant cited standard (e.g. UUID byte ordering per [RFC 9562]). No big-endian or little-endian convention is mandated by this specification beyond those references.

## 2.3 Hexadecimal

Where this specification calls for a hexadecimal encoding (notably for the body's `s` and `r` fields, and any inline byte example), the encoding MUST use:

- Lowercase letters `a` through `f`.
- The decimal digits `0` through `9`.
- Exactly two hex characters per byte.
- No `0x` prefix.
- No separators between bytes.

Consumers MUST reject hex strings that contain uppercase letters or characters outside the alphabet `[0-9a-f]`. Producers MUST emit lowercase only.

## 2.4 Base64

Where this specification calls for Base64 encoding (notably for the body's `p` and `g` fields), the encoding MUST be standard Base64 as defined in [RFC 4648 Section 4]:

- Alphabet `A`-`Z`, `a`-`z`, `0`-`9`, `+`, `/`.
- Padding character `=` MUST be included.
- No line breaks. The output is a single contiguous string.

Base64**url** is NOT used inside the body. The wire envelope uses Base62 (Section 4); do not confuse the two.

Consumers MUST reject Base64 strings that contain characters outside the alphabet, that lack required padding, or whose decoded length contradicts the algorithm's expected byte count for the surrounding suite.

## 2.5 UUIDs

Where this specification calls for a UUID (notably the body's `i` field), the value MUST be a UUID version 4 [RFC 9562] serialized in the canonical 8-4-4-4-12 textual form:

```
xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
```

with `x` lowercase hex digits and the version nibble fixed at `4` and the variant nibble `y` in `[8, 9, a, b]`. Producers MUST emit lowercase. Consumers MUST reject uppercase.

## 2.6 Hashing inputs

Where this specification calls for a SHA-256 of a public key, the bytes hashed are the public key serialized in SubjectPublicKeyInfo (SPKI) DER encoding as defined in [RFC 5280 Section 4.1.2.7], without any PEM framing, headers, or whitespace. The DER bytes MUST be hashed exactly once with SHA-256 [FIPS-180-4] and the resulting 32-byte digest emitted as a lowercase hex string per Section 2.3.

## 2.7 Time

Where this specification calls for a timestamp (notably the body's `t` field), the value is an integer count of milliseconds elapsed since the Unix epoch (1970-01-01T00:00:00Z) [POSIX], not counting leap seconds. Negative values MUST be rejected. The maximum value MUST fit in a JSON number that is an exact integer; implementations SHOULD treat values larger than 2^53 - 1 as malformed.

## 2.8 Error handling

Implementations MUST reject malformed input rather than substitute defaults. Where this specification permits multiple recoverable outcomes (e.g. an unknown sender), the relevant section says so explicitly. Where it does not, any deviation from the rules constitutes a parse error and the implementation MUST surface the error to the caller without producing a decrypted plaintext.

## 2.9 Forward compatibility

Producers MUST emit only fields and values defined by this specification or by an extension that has been registered per Section 13. Consumers MUST reject unknown values for the wire envelope's version token, the body's `a` field, and the wire compression code. Consumers MUST reject unknown fields in the message body.

This restriction is intentional: PlainCloak `v1` favors strict parsing over forward-leniency to prevent a malicious producer from smuggling fields that older consumers ignore.
