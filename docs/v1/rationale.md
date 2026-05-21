# Design Rationale

This document records the design decisions made during PlainCloak `v1` development and the reasoning behind them. It is informative; the prose specification in `spec/v1/` is normative.

## Wire format

### Why a magic prefix?

The `PLAINCLOAK:` prefix lets browser extensions, clipboard watchers, and chat-app integrations detect a PlainCloak message without performing any cryptographic or decompression work.

### Why Base62 over Base64?

Base62 contains no `+`, `/`, `=`, `_`, or `-`. Each of those characters breaks in at least one widely deployed messaging context: `+` and `/` are mangled by URL encoding and some chat clients, `=` is stripped or line-wrapped by quoted-printable email, and `_`/`-` collide with Markdown emphasis and auto-linkers.

Base62 produces a 6% size penalty relative to Base64 but eliminates an entire class of message-mangling bugs.

## Message body

### Why JSON over CBOR or a binary format?

JSON is debuggable. A developer staring at a malformed wire message can decompress it and look at the body in any text editor. Binary formats save roughly 30% in raw body size, but Brotli already recovers most of that redundancy: on the compressed wire the saving is only about 1-15% - around 15% for short messages and falling to under 1% for large ones, where incompressible ciphertext and signature dominate.

### Why single-letter body field names?

Field names are wire bytes. `recipient_key_hash` costs 18 characters every message; `r` costs one. The body has seven fields, so the saving is roughly 90 raw bytes per message before compression - 30-50 bytes on the wire after Brotli and Base62. The cost is a one-time legend (Section 6.2 of the spec) that any reader needs to consult once. Long descriptive keys would otherwise repeat the same legend on every message forever.

This is a stronger argument than the equivalent for a hand-edited config file; PlainCloak bodies are produced and consumed by code, not typed by humans, and the schema's `description` strings keep the meanings discoverable from any JSON-Schema-aware tool.

### Why include the wire version in the canonical form?

Cryptographic domain separation. A signature minted under one wire version must not be reinterpreted as valid under another, even if the body fields are otherwise compatible (e.g. a future v2 that retains `RSA-OAEP-SHA256`). Without the version segment, an attacker could re-tag a v2 message as v1 and a v1 consumer would accept the signature, silently bypassing whatever defenses v2 added. The cost is one byte; the pattern matches JWT (which signs the header), TLS (which hashes the version into the transcript), and Signal (which mixes protocol constants into HKDF).

### Why no JSON canonicalization for signing?

JSON canonicalization standards exist (RFC 8785 JCS, JSON-LD canonicalization) but each has had implementation bugs. Two correct JCS implementations have been observed to produce different output for inputs containing certain Unicode edge cases. For a signing application this is fatal.

A flat colon-separated string is unambiguous, trivially implementable in any language, and easy to verify by hand. The tradeoff is that any future field added to the canonical form must be appended in a fixed position; this is exactly the kind of constraint we wanted to make explicit.

## Cryptography

### Why RSA-OAEP-SHA256 in v1?

Pragmatic. RSA is universally supported, well-understood by reviewers, has stable key-format conventions, and is implemented correctly by every mainstream cryptographic library. SHA-256 closes the documented OAEP-with-SHA-1 issues.

The known downsides of RSA in 2026 (key size, no post-quantum protection) are addressable by a future suite identifier without changing the wire envelope. The plaintext-length limit is already addressed within `v1` by the hybrid suite below.

### Why ship a hybrid suite (`RSA-OAEP-AES256GCM-SHA256`) in v1?

Direct RSA-OAEP caps plaintext at `modulus - 66` bytes - 190 bytes for RSA-2048, 446 for RSA-4096. That ceiling is too low for ordinary messages. The hybrid suite wraps a fresh AES-256 key with RSA-OAEP and encrypts the plaintext under AES-256-GCM, lifting the cap to the practical body-size limit (Section 6.5).

It is a separate suite identifier rather than a change to `RSA-OAEP-SHA256` because the open-registry model already handles this cleanly: a consumer that does not implement it rejects with `unknown-suite`, no wire-version bump. `RSA-OAEP-SHA256` remains as the minimal, smallest-payload option for short messages; `RSA-OAEP-AES256GCM-SHA256` is RECOMMENDED for general use. Binding the AEAD AAD to the canonical form keeps the AEAD and signature authenticity layers over the same bytes (see "Why include the canonical form as the AEAD AAD?" below).

### Why include both encryption and signing?

End-to-end confidentiality (encryption) and authenticity (signature) are orthogonal properties. Without the signature, an attacker who controls the recipient's transport could swap a ciphertext from another conversation and the consumer could not detect it. Without encryption, the message is plaintext.

PlainCloak provides both because both are necessary for "this message is from Alice and only Bob can read it."

### Why a fresh PSS salt per signature?

PSS is designed to be secure with deterministic salts in many cases, but fresh randomness is the most conservative choice. The salt length is fixed at 32 bytes (the SHA-256 digest size), the strongest commonly recommended length.

### Why mandate `e = 65537`?

Small `e` values (notably `e = 3`) have a documented history of implementation pitfalls. `e = 65537` is the de facto industry standard; mandating it in the spec eliminates an entire class of "interoperable in theory but broken in practice" RSA bugs.

## Key identification

### Why hash SPKI DER rather than RSA modulus alone?

SPKI DER includes the algorithm OID and parameter set, which prevents a key from being silently re-interpreted as a different algorithm in a future suite. Hashing only the modulus would conflate an `RSA-OAEP-SHA256` key with a hypothetical `RSA-OAEP-SHA384` key sharing the same modulus.

### Why SHA-256 rather than SHA-3?

Prevalence. Every cryptographic library has a tested SHA-256. SHA-3 is available but adds a dependency for a marginal benefit. If SHA-256 is later compromised, the `key_hash` algorithm changes invalidate all existing identifiers - this is unavoidable and would require a new wire version regardless of the new hash chosen.

### Why no truncated short-fingerprint variant?

Fingerprint truncation is an interoperability landmine. Any truncation length we picked would be wrong for some user-visible context, and a partial-comparison UI would risk users accepting near-matches.

A future version may add a structured short-form (e.g. 10 words from a fixed vocabulary, RFC 1751 / RFC 8949 style) for explicit verification UI. That work belongs to a UX-focused workstream, not the wire-format spec.

## Registries

### Why open registries for both suites and compressors?

The wire envelope, body schema, canonical form, and key-hash rules are all algorithm-agnostic. The schema treats `p` and `g` as opaque base64 strings; the canonical form treats `p` as an opaque segment; the key-hash uses SHA-256(SPKI DER), which works for any modern primitive whose AlgorithmIdentifier OID is registered. Nothing in the wire layer depends on RSA-OAEP-SHA256 or Brotli specifically.

So forbidding new suites or compressors at the v1 layer would only force a wire-version bump every time the cryptographic ecosystem moves. That's a heavy cost for no security benefit: a consumer that doesn't support a new suite already rejects it as `unknown-suite`, the same outcome a wire-version bump would produce. The open-registry model accepts this and adds a `recommended` / `deprecated` status to manage migration without breaking deployed code.

The boundary is clear and short. Wire-version bumps are reserved for changes to the envelope structure, body schema, canonical form, key-hash algorithm, or encoding layer (Section 13.7). Everything else is a registry update.

### Why is each suite required to specify the byte layout of `p`?

Because the suite identifier is the only signal the consumer has for how to parse `p`. RSA-OAEP places one ciphertext blob there; a hybrid suite (KEM + AEAD) places framed bytes containing the KEM ciphertext, the nonce, the AEAD ciphertext, and the AEAD tag. If two suites disagreed on framing while sharing a body schema, the consumer would have to peek inside the bytes to disambiguate, which is the kind of ambiguity a well-specified protocol must avoid.

The rule "framing is derivable from the suite identifier alone" is what keeps the body schema closed at seven fields forever while still permitting arbitrarily complex per-suite encryption constructions.

### Why include the canonical form as the AEAD AAD?

For hybrid suites that use an AEAD, the AEAD's authenticity coverage and the signature's authenticity coverage should be over the same bytes. Otherwise an attacker could tamper with metadata that the AEAD doesn't cover but the signature does (or vice versa), creating windows where the two authenticity layers disagree. Binding the AEAD AAD to the canonical-form bytes (Section 7.2) keeps both layers aligned without spec-level complexity.

### Why is the 1 MiB decompression budget a recommendation and not a hard limit?

The threat the budget addresses is malicious decompression bombs: a small wire payload that expands to gigabytes and exhausts a consumer's memory or CPU. The defense that matters is "abort at the streaming layer when a configured threshold is exceeded." The exact threshold is a deployment decision: an attachment-bearing consumer needs more, an embedded device needs less, a default chat client is well-served by 1 MiB.

Mandating a specific number across all v1 implementations would either force the embedded device to over-allocate or force the attachment-bearing consumer to ship a non-conforming variant. Neither is good. So the spec mandates *some* budget (defense is required), recommends 1 MiB (sensible default), and leaves the value configurable (operator and end-user agency). This matches how every other size budget in the deployed protocol world is handled.

## Conformance

### Why mandatory test vectors instead of a written compatibility specification?

Test vectors are byte-precise and language-agnostic. A spec sentence like "the canonical form is the colon-joined list of fields" is open to misreading; a test vector that produces the exact bytes leaves no room for misreading.

The vectors also serve as an executable safety net during spec evolution: if a proposed clarification changes the produced bytes, the regenerated vectors make that change visible in the diff.
