# Contributing to PlainCloak

Thanks for your interest. PlainCloak is a small, early-stage protocol spec, and outside eyes are genuinely useful - both on the cryptography and on the prose.

## What this repo is

This repository holds the **protocol specification only**: prose, JSON Schemas, ABNF, and canonical test vectors. Implementation bugs belong in the relevant implementation repository, not here.

## Ways to contribute

- **Spec review.** Read [`spec/v1/`](spec/v1/) and flag anything ambiguous, contradictory, or under-specified. Ambiguity in a protocol spec is a bug.
- **Threat model review.** [`docs/v1/threat-model.md`](docs/v1/threat-model.md) is the most important document for outside scrutiny.
- **Test vectors.** New deterministic or verification vectors that exercise edge cases in [`test-vectors/v1/`](test-vectors/v1/).
- **Schema fixes.** Cases where [`schemas/v1/`](schemas/v1/) disagrees with the prose.
- **Editorial fixes.** Typos, broken links, unclear wording.

## How to propose a change

1. Open an issue first for anything non-trivial. A short discussion up front avoids wasted work.
2. Use the PR template. Explain what changed and why; if behavior changes, update the relevant test vectors and `CHANGELOG.md`.
3. One logical change per PR. Editorial cleanups can be bundled.

## Reporting a vulnerability

Do **not** open a public issue for security flaws in the specification. See [`SECURITY.md`](SECURITY.md) for the private reporting process.

## Licensing

Contributions to spec text are licensed under the spec license; contributions to code, schemas, and test vectors are licensed under the code license. See [`LICENSE-SPEC`](LICENSE-SPEC) and [`LICENSE-CODE`](LICENSE-CODE).

By submitting a contribution, you agree it can be distributed under those licenses.
