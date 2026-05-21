# Security Policy

## Reporting a vulnerability

If you believe you have found a vulnerability in the **PlainCloak protocol specification** itself - that is, a flaw in the prose, schemas, or test vectors that would compromise an implementation that follows the spec correctly - please report it privately. **Do not open a public issue.**

Send an email to: **PlainCloak@outlook.com** with the subject line beginning `[plaincloak-security]`.


## What counts as a specification vulnerability

Examples of in-scope reports:

- A flaw in the canonical-form construction that allows signature confusion.
- A flaw in the parsing rules that allows a malicious producer to bypass `wrong-recipient` detection.
- A test vector whose expected outcome is incorrect under a strict reading of the spec.
- A schema that accepts a body the prose forbids, or vice versa.

Out-of-scope (implementation bugs, not spec flaws): please report to the relevant implementation repository instead.

## What we will do

- Acknowledge your report within 72 hours.
- Investigate and confirm or refute the issue.
- Develop a fix.
- Publish a fixed version of the spec, with credit to the reporter unless they prefer to remain anonymous.
- Update `CHANGELOG.md` and the relevant test vectors.
