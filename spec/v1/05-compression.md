# 5. Compression

This section specifies the compression layer that sits between the JSON message body (Section 6) and the Base62 wire encoding (Section 4). A `v1` producer compresses the body's JSON UTF-8 bytes; a `v1` consumer decompresses the bytes obtained from Base62 decoding. The compression algorithm is named by the `comp-code` field of the wire envelope (Section 3).

## 5.1 Registry

The set of valid `comp-code` values for `v1` is governed by an open registry. New codes are added under the Specification Required policy of Section 13. The machine-readable mirror of the registry is `schemas/v1/compression.json`.

The registry as of this revision of `v1`:

| Code | Algorithm | Status in `v1` |
|------|-----------|----------------|
| `BR` | Brotli [RFC 7932] | REQUIRED (core profile baseline) |
| `ZS` | Zstandard [RFC 8878] | RESERVED, MUST NOT be produced |
| `NO` | No compression (identity) | OPTIONAL, debug and test use only |

A `v1` producer:

- MUST emit a `comp-code` whose entry has status `required`, `recommended`, or `optional`. Producing a `comp-code` of status `reserved` or `deprecated` is non-conforming.
- MUST emit `BR` as the `comp-code` unless the producer has affirmatively opted into another registered code that the recipient is known to accept.
- MAY emit `NO` only in test or diagnostic contexts. `NO` MUST NOT be used in production messages.

A `v1` consumer:

- MUST accept any `comp-code` whose entry has status `required`. For the current registry this means `BR`.
- MAY accept any `comp-code` whose entry has status `recommended` or `optional`.
- MUST reject `comp-code` values that are unknown to the consumer or whose registered status is `reserved` or `deprecated`-for-rejection, with the `unknown-compression` error category of Section 3.6.

Future revisions of `v1` MAY add, deprecate, or reclassify codes via the registry policy of Section 13. Such changes do NOT trigger a wire-version bump; consumers that do not yet support a newly registered code reject it with `unknown-compression`, which is the correct behavior under this open-registry model.

## 5.2 Brotli (`BR`)

When `comp-code` is `BR`, the compression algorithm is Brotli as specified in [RFC 7932].

### 5.2.1 Producer parameters

A producer using `BR` MUST emit a Brotli stream that satisfies the following:

- The stream is a single complete Brotli compressed stream (no concatenation with other formats, no custom framing).
- The stream's mode SHOULD be the generic mode. The text and font modes are NOT RECOMMENDED because Brotli's text mode includes a static dictionary tuned for HTML and English prose; the savings on PlainCloak's JSON bodies are negligible and the dictionary dependency complicates cross-implementation determinism.
- The window size (`lgwin`) MAY be any value permitted by Brotli (10 through 24). Producers SHOULD use 22 (the Brotli default) unless a smaller window is needed for a specific environment. Smaller windows produce slightly larger output but reduce decoder memory.
- The quality level MAY be any value from 0 through 11. Producers SHOULD use 11 for normal messages. The quality level MUST be a value the producer's encoder accepts; this specification does not require any particular tradeoff.

The output of two conforming Brotli encoders for the same input is NOT guaranteed to be byte-identical because Brotli encoders make non-deterministic block-splitting decisions. Test vectors that depend on a specific compressed-byte sequence MUST therefore include the encoder and parameters used; see `test-vectors/v1/deterministic/03-brotli-roundtrip.json`.

### 5.2.2 Consumer parameters

A consumer using `BR` MUST accept any well-formed Brotli stream that:

- Decodes within the size budget of Section 5.4.
- Was produced with `lgwin` values up to 24 (the Brotli maximum).

A consumer MUST NOT assume any particular producer parameter. In particular, a consumer MUST NOT reject a stream because of its window size or quality level, except indirectly via the size budget of 5.4.

## 5.3 Identity (`NO`)

When `comp-code` is `NO`, there is no compression. The bytes obtained from Base62 decoding (Section 4.3) are the JSON message body bytes directly.

`NO` exists for two purposes only:

1. Authoring deterministic test vectors that exercise only the encoding and message-body layers without involving Brotli.
2. Diagnosing parser bugs where Brotli involvement obscures the failure.

Production traffic MUST use `BR`. A producer using `NO` for production traffic is non-conforming. A consumer SHOULD warn or refuse if it observes `NO` in a non-diagnostic context.

## 5.4 Decompression size budget

A consumer MUST enforce a maximum decompressed size to defend against decompression bombs. The exact size of that budget is configurable by the implementation and, where the implementation exposes it, by the operator or end user.

The RECOMMENDED default budget for general-purpose `v1` consumers is **1 MiB (1,048,576 bytes)** of decompressed output. This value is large enough to accommodate any plausible chat-message plaintext with comfortable margin, and small enough to make a malicious decompression bomb cheap to abort.

A consumer whose budget is exceeded MUST abort decompression and reject the message with the `decompressed-too-large` error category of Section 3.6. The decision to raise or lower the budget is left to the implementation:

- A consumer targeting attachment-bearing or specialized workloads MAY raise the budget arbitrarily, accepting the corresponding memory cost.
- A consumer targeting constrained environments (embedded devices, browser extensions on low-memory tabs) MAY lower the budget. Setting the budget below 64 KiB risks rejecting otherwise-valid text messages of several thousand characters and is NOT RECOMMENDED unless the deployment scope guarantees shorter messages.
- A consumer SHOULD document the budget it enforces so that producers and users can predict acceptance.

The budget applies to decompressed bytes only. It does not apply to the wire payload's encoded size, which is bounded by message-channel limits and is at least an order of magnitude smaller in practice.

Whatever the configured budget, enforcement MUST occur at the streaming layer (the consumer aborts as soon as the budget is exceeded, not by allocating then checking). This is the only requirement that is non-negotiable; the size value itself is not.

## 5.5 Cross-encoder reproducibility

Test vectors in `test-vectors/v1/deterministic/03-brotli-roundtrip.json` are authored using the Brotli encoder from the `brotli` PyPI package on Linux x86_64, with the following parameters:

- `mode = generic` (Brotli mode 0)
- `lgwin = 22`
- `quality = 11`

These values are recorded in the vector files so that other implementations can reproduce them when generating producer-side checks. A consumer MUST NOT depend on specific compressed-byte sequences; only the round-trip property (compress-then-decompress yields the original bytes) is required of a conforming consumer.
