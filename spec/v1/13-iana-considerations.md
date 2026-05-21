# 13. IANA Considerations and Registry Policy

This section describes how new entries are added to the registries that influence on-the-wire behavior, and what changes can never be made within `v1` and require a new wire version. **The registries are not currently maintained by IANA**; the section is named "IANA Considerations" by analogy with [RFC 8126] to make clear what the policy would be if PlainCloak's registries were delegated to IANA.

The PlainCloak `v1` registries are maintained in this repository at:

- `schemas/v1/algorithms.json` (cryptographic suites; see Section 8 and the prose registry in 8.1).
- `schemas/v1/compression.json` (compression codes; see Section 5 and the prose registry in 5.1).

The prose registries in Sections 5.1 and 8.1 are normative. The JSON files are derived mirrors that are CI-validated to match the prose; if they disagree, the prose wins.

## 13.1 Registration policy

Both registries are **open** under a Specification Required policy [RFC 8126 Section 4.6]. A registration is accepted only if all of the following hold:

1. A written specification of the entry is published in a stable, dated form. A pull request against this repository that adds the necessary spec text is the canonical submission form.
2. The submission specifies, at minimum, the contents listed in 13.2 below.
3. A designated expert (initially the spec maintainers; see 13.5) reviews the registration for technical soundness, naming conventions, and consistency with existing entries.
4. Test vectors covering the new entry are added to `test-vectors/v1/` in the same change.
5. At least one independent implementation has demonstrated interoperability against the proposed test vectors.

Both registries grow within the existing wire version. Adding, deprecating, or reclassifying entries in either registry does NOT trigger a wire-version bump. Consumers that do not yet support a newly registered entry reject it as `unknown-suite` or `unknown-compression`, which is the correct behavior under this open-registry model.

A registration that touches the wire format itself (the items in 13.7) MUST NOT be accepted into `v1`. Such changes require a new wire version (a new directory under `spec/`).

## 13.2 Required contents of a registration

### 13.2.1 Cryptographic suite

A new entry in `schemas/v1/algorithms.json` MUST specify:

1. **Identifier.** A short ASCII name matching the pattern of 13.4. The identifier is the value that will appear in the body's `a` field (Section 6.2.1).
2. **Encryption / KEM algorithm.** The primitive(s) used to derive the bytes placed in the body's `p` field. The submission MUST cite a stable normative reference (e.g. RFC, FIPS publication, IETF draft at last-call or later).
3. **Signing algorithm.** The primitive used to produce the bytes placed in the body's `g` field. Stable normative reference required.
4. **Public-key encoding.** The SubjectPublicKeyInfo (SPKI) DER AlgorithmIdentifier OID under which the public key is encoded. The OID MUST come from a stable normative source. SHA-256 of the SPKI DER is the body's `s` and `r` field for every suite without exception (Section 9); a suite that cannot be SPKI-DER-encoded cannot be registered in `v1`.
5. **Private-key encoding.** The PKCS#8 PrivateKeyInfo DER AlgorithmIdentifier under which the private key is encoded.
6. **Byte layout of `p`.** An exact, deterministic description of how the suite's encryption output(s) are framed inside the `p` field. The framing MUST be derivable from the suite identifier alone, with no auxiliary metadata. For a single-primitive public-key encryption (e.g. RSA-OAEP) this is "the single ciphertext blob, no framing." For a hybrid (KEM + AEAD) this typically reads "concatenation of `KEM_ct[0..K-1]` || `nonce[0..N-1]` || `AEAD_ct[0..]` || `tag[0..T-1]`" with `K`, `N`, and `T` fixed by the suite (or, for `K`, fixed by the recipient key when the KEM output length is keyed on the recipient as in RSA-OAEP).
7. **Byte layout of `g`.** Same requirement, applied to the signature output. Most signing primitives produce a single blob; a registration MAY define more complex framing if needed and justify it.
8. **Plaintext length semantics.** Whether the suite imposes a maximum plaintext length, and if so, how it is computed (e.g. `n - 66` for RSA-OAEP-SHA256). A suite MAY specify "no upper bound" if its construction supports arbitrary-length plaintext.
9. **AEAD AAD source (if applicable).** If the suite uses an AEAD, the registration MUST specify what bytes are bound as Additional Authenticated Data. The default and RECOMMENDED choice is "the canonical-form bytes of Section 7.2", which binds the AEAD authenticity to the same metadata the signature covers.
10. **Initial registry status.** One of `required`, `recommended`, `optional`, `reserved`, `deprecated` per 13.3.
11. **Security analysis.** Either a citation to an existing analysis (CFRG, NIST, peer-reviewed paper) or a new analysis published with the registration.

### 13.2.2 Compression code

A new entry in `schemas/v1/compression.json` MUST specify:

1. **Code.** A two-character uppercase ASCII token (`^[A-Z]{2}$`) not already in use.
2. **Algorithm.** The compression algorithm, with a stable normative reference.
3. **Streaming-decoder requirement.** A description of how a consumer can implement the decoder so that it can abort at the size budget of Section 5.4 without first allocating the full decompressed output.
4. **Decoder rejection contract.** The conditions under which the decoder is required to fail, mapped to the `decompression-failed` error category of Section 3.6.
5. **Initial registry status.** One of `required`, `recommended`, `optional`, `reserved`, `deprecated` per 13.3.
6. **Worst-case ratio.** The maximum compression ratio achievable with the algorithm, used by reviewers to confirm the size-budget defense remains effective.

## 13.3 Registry statuses

Both registries use the same status values:

| Status | Producer behavior | Consumer behavior |
|--------|-------------------|-------------------|
| `required` | MUST be supported by core profile producers. | MUST be supported by core profile consumers. |
| `recommended` | SHOULD be supported by producers; ecosystem is encouraged to migrate toward it. | SHOULD be supported by consumers. |
| `optional` | MAY be produced. | MAY be supported. Implementations that do not support it reject as `unknown-*`. |
| `reserved` | MUST NOT be produced. The name is held for a future allocation. | MUST be rejected as `unknown-*`. |
| `deprecated` | SHOULD NOT be produced. Producers SHOULD migrate to a replacement. | MAY continue to be supported for backward compatibility. The registry entry MAY indicate `deprecated`-for-rejection at a future date. |

A status change is itself a registry update under 13.1. Promoting `optional` to `recommended` to `required` requires the same Specification Required process as a fresh registration; demoting in the opposite direction (e.g. `required` to `deprecated`) likewise.

## 13.4 Naming conventions

New suite identifiers MUST follow the pattern `^[A-Z0-9-]+$` and be informative shorthand for the underlying primitives, in the order encryption-mode-hash. Examples of well-formed names:

- `RSA-OAEP-SHA256` (existing)
- `RSA-OAEP-SHA384`
- `ECDH-AES-GCM`
- `MLKEM768-AESGCM-MLDSA65`
- `X25519-CHACHA20POLY1305-ED25519`

Suite identifiers MUST NOT contain colons (they would collide with the canonical-form separator), spaces, or non-ASCII characters.

Compression codes MUST be exactly two uppercase ASCII letters and SHOULD be obvious abbreviations of the underlying algorithm name (`BR` for Brotli, `ZS` for Zstandard).

## 13.5 Designated experts

The initial designated experts for `v1` are the maintainers of this repository, identified in `CONTRIBUTING.md`. The role of a designated expert is to:

- Verify the technical correctness of the registration.
- Verify that test vectors exist and pass.
- Verify that the registration meets the content requirements of 13.2.
- Reject registrations that are duplicative, ambiguous, or violate the naming conventions of 13.4.

A designated expert SHOULD complete review within 30 days of a registration submission.

## 13.6 Reserved codes

The following are reserved and MUST NOT be allocated by an in-version registration:

- Suite identifiers beginning with `EXAMPLE-`, `TEST-`, or `DRAFT-` are reserved for documentation, testing, and unstable proposals respectively.
- The compression code `XX` is reserved for a future "experimental" slot.

## 13.7 Out-of-scope changes (wire-version triggers)

Changes to any of the following require a new wire version (a new `spec/vN/` tree); they MUST NOT be made via a `v1` registry update:

1. **Wire envelope structure.** The four-field colon-separated form of Section 3.2, the magic literal `PLAINCLOAK`, the version-token format `vN`, or the introduction of additional envelope fields (e.g. the chunking form reserved in Section 3.5).
2. **Body schema.** The set of seven required body fields (`a`, `i`, `t`, `s`, `r`, `p`, `g`), their JSON types, or the closed-object property of Section 6.3.
3. **Canonical-form construction.** The segment order, separator, version-from-envelope rule, or per-segment encoding rules of Section 7.2.
4. **Key-hash algorithm.** The use of SHA-256 over SPKI DER bytes for the body's `s` and `r` fields (Section 9.2). A change to this algorithm invalidates every existing key identifier and is the canonical reason for a wire-version bump.
5. **Encoding layer.** The Base62 alphabet of Section 4.1 or the encoding/decoding algorithms of Sections 4.2 and 4.3.

Changes that are NOT in this list (new compressors, new suites, status reclassifications, registration of additional plaintext-length semantics) stay within `v1` via the registry policy of 13.1.

## 13.8 Unregistered values

`v1` consumers MUST reject suite identifiers and compression codes that are not present in the consumer's supported set at the time the consumer was built or last updated. There is no fallback or "best-effort" handling of unknown values. This strict-rejection rule is the reason for the registry policy: an unrecognized value is the signal that the consumer needs to be updated, not that the producer has used a private extension.

A consumer MAY be configured to fetch and trust a current copy of the registry at runtime, but the trust decision (whether to accept a newly registered entry without a code update) is implementation-specific and SHOULD be documented in the implementation's conformance report (Section 12.3).
