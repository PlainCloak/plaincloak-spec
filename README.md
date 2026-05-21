# PlainCloak

A platform-agnostic, paste-anywhere end-to-end encryption protocol for private messaging over arbitrary text-bearing channels. PlainCloak messages are self-contained text strings that work in any chat application: you generate a key pair, share your public key, and exchange encrypted messages by copy-paste.

This repository is the **protocol specification**. It contains the prose specification, JSON Schemas, ABNF grammar, and canonical test vectors that any conforming implementation must reproduce.

## Repository layout

```
spec/                Prose specification
schemas/             JSON Schemas, ABNF, machine-readable registries
test-vectors/        Canonical test vectors and key fixtures
docs/                Informative supporting documents
```


## Where to start reading

| You want to... | Read |
|----------------|------|
| Understand what PlainCloak is and why | [`spec/v1/01-introduction.md`](spec/v1/01-introduction.md) |
| Implement the protocol | [`spec/v1/01-introduction.md`](spec/v1/01-introduction.md) through [`spec/v1/14-references.md`](spec/v1/14-references.md) |
| Validate a JSON message body programmatically | [`schemas/v1/message.schema.json`](schemas/v1/message.schema.json) |
| Verify your implementation | [`test-vectors/v1/`](test-vectors/v1/) and [`spec/v1/12-conformance.md`](spec/v1/12-conformance.md) |
| Understand the threat model | [`docs/v1/threat-model.md`](docs/v1/threat-model.md) |
| Understand a design decision | [`docs/v1/rationale.md`](docs/v1/rationale.md) |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to propose changes, and [`SECURITY.md`](SECURITY.md) for reporting specification vulnerabilities privately.

## License

This repository is dual-licensed:

- **Prose** (`spec/`, `docs/`, `.github/`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`) is licensed under [Creative Commons Attribution 4.0 International](LICENSE-SPEC) (CC-BY-4.0).
- **Machine-readable artifacts** (`schemas/`, `test-vectors/`, `versions.json`) are licensed under the [Apache License, Version 2.0](LICENSE-CODE).

See [`LICENSE`](LICENSE) for the summary, and the individual license files for full text.
