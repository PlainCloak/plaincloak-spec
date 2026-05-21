# Threat Model

This document describes the threats PlainCloak `v1` defends against and the threats it does not. It expands on the `Security Considerations` section of `spec/v1/11-security-considerations.md` with discussion that is informative rather than normative.

## Defended threats

### Passive observation of the transport

A chat-app operator, a network observer, or anyone with read access to a stored chat history sees only the wire envelope and the encrypted payload. The plaintext is not recoverable without the recipient's private key. The signature does not aid recovery; it only authenticates the producer for whoever is decrypting.

The wire envelope reveals:

- That the message is a PlainCloak `v1` payload.
- The compressed-then-Base62-encoded length of the body.
- Nothing about the plaintext content.

The body, if anyone successfully decompresses it (which requires no key), reveals:

- The cryptographic suite (the body's `a` field).
- The producer's chosen message identifier (`i`, a UUIDv4).
- The producer's timestamp (`t`, which is untrusted).
- The sender and recipient public-key fingerprints (`s`, `r`).
- The encrypted ciphertext (`p`) and signature (`g`), opaque without keys.

### Active modification of the transport

A man-in-the-middle that flips bits in the payload, signature, or any other field will cause one of:

- A parse error at the consumer (`malformed`, `invalid-base62`, `decompression-failed`, `invalid-json`, `invalid-body`, etc.).
- A decryption failure at the consumer (`decryption-failed`).
- A signature-verification failure at the consumer (`signature-invalid`).

In all cases, the consumer surfaces the failure to the user; modified messages are not silently accepted as valid.

### Passive disclosure of stored ciphertext

A breach of a chat-app server's archived storage exposes only ciphertext. The same protections as for active modification apply.

## Undefended threats

### Endpoint compromise

If the user's device is compromised, the attacker has the user's private keys, contact list, and any decrypted plaintext that the user has read. PlainCloak does not encrypt-at-rest the device's private keys beyond what the implementation chooses to do (the informative `keystore.schema.json` describes a passphrase-encrypted keystore but does not require it).

### Out-of-band trust failures

PlainCloak does not bind a public key to a real-world identity. The trust relationship between a `key_hash` and a person is established entirely outside the protocol: by exchanging keys in person, by reading a hash aloud over a verified voice channel, by trusting a key transmitted in a separate authenticated channel.

If the user adds a wrong key to their contacts (e.g. an attacker substituted their key in transit during the out-of-band exchange), every message that arrives signed by that wrong key will appear `verified` from the legitimate party. PlainCloak cannot detect this; out-of-band verification is the user's responsibility.

### Traffic analysis

PlainCloak messages reveal:

- Wire-message length.
- Time of transmission.
- Sender and recipient key hashes.

`v1` does not pad messages, mix traffic, or otherwise mask metadata. An adversary observing a recipient's incoming traffic can count messages, time them, group them by sender, and correlate with external events.

### Forward secrecy

A compromise of a private key permits decryption of all past messages encrypted to its corresponding public key. `v1` uses long-lived static RSA keys; there is no key ratcheting and no forward secrecy.

The mitigations available to a user concerned about forward secrecy:

- Rotate keys periodically. Each new key publication breaks decryption of past messages with the old key, which IS the desired property under this threat model.
- Avoid storing decrypted plaintext locally if device compromise is the concern.

### Replay attacks

`v1` does not require consumers to track the body's `i` field (message identifier) for replay detection. An adversary who captures a wire message can re-deliver it later and the consumer will decrypt and present it again. Application-level deduplication is RECOMMENDED for any context where replay would cause harm (e.g. duplicated financial instructions, duplicated emergency notifications).

### Quantum computers

RSA is broken by a sufficiently large quantum computer. Stored ciphertexts captured today and held until a quantum adversary is available will be retroactively decryptable. Users who must defend against this "harvest-now-decrypt-later" model SHOULD reduce the persistence of their `v1` ciphertext (rotate keys, encourage chat archives to be deleted) and SHOULD migrate to a post-quantum suite once one is registered in `schemas/v1/algorithms.json` (see `spec/v1/13-iana-considerations.md` Section 13). A PQ-hybrid suite will be a `v1` registry addition, not a new wire version, so producers and consumers can adopt it without breaking compatibility with existing `v1` infrastructure.

## Trust model

PlainCloak makes the following trust assumptions:

| Trusted | Untrusted |
|---------|-----------|
| The user's device, OS, and key storage. | The transport (chat app, network, server). |
| The cryptographic library implementing RSA-OAEP, RSA-PSS, and AES-256-GCM. | The producer's `t` field (timestamp, informational only). |
| The out-of-band channel through which public keys were exchanged. | Any party whose public key is not in the user's contacts. |
| The local random-number generator. | The producer's `i` field (message identifier; only its uniqueness, never its semantics). |

If any of the items in the "Trusted" column is compromised, the security of the protocol no longer holds for the affected user.

## Comparisons

Where PlainCloak sits relative to nearby protocols:

- **PGP/GPG (RFC 9580)**: Similar trust model; long-lived static keys, no forward secrecy, paste-friendly text encoding. PlainCloak's wire format is more compact, the canonical-form-for-signing avoids JSON canonicalization ambiguity, and the conformance vectors are mandatory for implementations.
- **Signal Protocol**: Stronger threat model (forward secrecy via Double Ratchet, key compromise impact bounded). Signal is platform-locked and not paste-anywhere; PlainCloak deliberately trades forward secrecy for paste-anywhere portability.
- **age-encryption.org**: Similar paste-friendly philosophy, file-format-oriented rather than chat-message-oriented. age does not include signatures in its core; PlainCloak does.

PlainCloak chose its threat-model trade-offs to optimize for "encrypt to one person, paste into any chat app." Users with stronger threat-model needs should consider Signal and accept its platform constraints.
