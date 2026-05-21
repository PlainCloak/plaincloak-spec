# 3. Wire Format

This section specifies the textual envelope that carries a PlainCloak message across any text-bearing channel. Every PlainCloak `v1` wire message MUST conform to the grammar in 3.2 and the parsing rules in 3.3.

## 3.1 Overview

A `v1` wire message is a single line of printable ASCII consisting of four colon-separated fields:

```
PLAINCLOAK:v1:BR:<base62-payload>
```

The first three fields are the **envelope header** and are never compressed or encoded; a parser can read them with byte-level operations alone. The fourth field is the **wire payload**: a Base62-encoded string whose decoded bytes are a Brotli-compressed UTF-8 JSON message body (Section 6).

Header fields are intentionally uncompressed so that:

1. A parser can determine the protocol version before invoking version-specific logic.
2. A parser can determine the compression algorithm before invoking decompression.
3. Detection tools can recognize a PlainCloak message without performing any cryptographic or decompression work.

## 3.2 Grammar

The normative grammar lives in `schemas/v1/wire.abnf`. The relevant excerpt is:

```abnf
wire-message    = magic ":" version ":" comp-code ":" wire-payload
magic           = %s"PLAINCLOAK"
version         = %s"v1"                        ; literal "v1" for this specification
comp-code       = 2(%x41-5A)                    ; two uppercase ASCII letters; values registered per Section 5
wire-payload    = 1*BASE62-CHAR
BASE62-CHAR     = DIGIT / %x41-5A / %x61-7A     ; 0-9 / A-Z / a-z
DIGIT           =  %x30-39
```

A `v1` parser MUST treat `magic`, `version`, and `comp-code` as case-sensitive. A wire message that begins with `plaincloak:` (any case other than uppercase `PLAINCLOAK`) is malformed and MUST be rejected.

## 3.3 Parsing algorithm

A consumer presented with a candidate wire message MUST execute the following algorithm:

1. Locate the first colon (`U+003A`). If no colon is present, reject as malformed.
2. The substring before the first colon is the candidate magic. If it is not exactly `PLAINCLOAK` (uppercase, length 10), reject as malformed.
3. Locate the second colon. The substring between the first and second colons is the version token. If it is not exactly `v1`, reject as `unsupported-version`.
4. Locate the third colon. The substring between the second and third colons is the compression code. If it is not present in the registry of Section 5, reject as `unknown-compression`.
5. The substring after the third colon, up to but not including any trailing whitespace or message-channel termination, is the wire payload. If it is empty or contains any character outside the Base62 alphabet (Section 4.1), reject as malformed.
6. Decode the wire payload per Section 4. If decoding fails, reject as `invalid-base62`.
7. Decompress the decoded bytes per the compression code from step 4 and Section 5. If decompression fails or exceeds the size limit of Section 5.4, reject as `decompression-failed` or `decompressed-too-large` respectively.
8. Parse the decompressed bytes as UTF-8 JSON. If parsing fails, reject as `invalid-json`.
9. Validate the JSON against the schema referenced in Section 6. If validation fails, reject as `invalid-body`.
10. Continue with the body-level rules of Section 6 and the suite-specific rules of Section 8.

Steps 1 through 9 are performed in order. A consumer MUST NOT skip any step or reorder them; in particular, signature verification (Section 10) MUST NOT be attempted before successful body validation in step 9.

## 3.4 Permitted surrounding context

A wire message often appears embedded in surrounding chat text (e.g. a paragraph quoted in a reply). Detection tools and consumers MAY scan arbitrary text for the substring `PLAINCLOAK:v1:` and extract candidate wire messages. The terminator of a wire message in such embedded contexts is the first character that is not a member of the Base62 alphabet at the wire payload position.

In particular, whitespace (including space, tab, line feed, carriage return), punctuation, and other Unicode characters terminate a wire payload during extraction. The colon at position 3 (between `comp-code` and `wire-payload`) is part of the envelope and is not a terminator.

A producer MUST NOT emit a wire message containing internal whitespace or non-Base62 characters in the payload.

## 3.5 Reserved future chunking

A future version MAY introduce a chunked form for very large messages of the shape:

```
PLAINCLOAK:vN:BR:n/total:<base62>
```

where `n` and `total` are 1-based decimal indices. `v1` consumers MUST reject any wire message whose envelope header contains more than three colons in the position-counted fields above, including those resembling the chunked form.

`v1` parsers MUST NOT be designed to silently accept extra fields. The strict rejection policy preserves the right of a future version to redefine the meaning of a fourth header field without ambiguity.

## 3.6 Error categories

The error codes named in 3.3 are not part of any wire format. They are conceptual labels intended to make conformance reporting unambiguous. An implementation MAY use any internal naming. The following categories are normative:

| Category | When it occurs |
|----------|----------------|
| `malformed` | The string is structurally not a `v1` envelope. |
| `unsupported-version` | The version token is well-formed but not `v1`. |
| `unknown-compression` | The compression code is well-formed but not in the Section 5 registry. |
| `invalid-base62` | The wire payload contains characters outside the Base62 alphabet. |
| `decompression-failed` | The compression decoder rejected the input. |
| `decompressed-too-large` | The decompressed output exceeded the size limit of Section 5.4. |
| `invalid-json` | The decompressed bytes are not valid UTF-8 JSON. |
| `invalid-body` | The JSON does not validate against `message.schema.json`. |
| `unknown-suite` | The body's `a` field is not in the Section 8 registry (raised in step 10). |
| `decryption-failed` | The suite's decryption (RSA-OAEP, or RSA-OAEP wrap plus AES-GCM tag check for the hybrid suite) produced an error or a length mismatch. |
| `signature-invalid` | Signature verification returned `false` for a known-sender message. |

Sections 6, 8, and 10 define additional error categories that arise after step 10.
