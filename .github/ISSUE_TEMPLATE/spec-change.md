---
name: Spec or registry change proposal
about: Propose a normative change to the spec, schemas, or registries
title: "[spec-change] "
labels: spec-change
---

### Summary

One sentence describing what you propose changing.

### Motivation

What problem does this solve? Cite concrete user impact, an interoperability bug, or a security concern.

### Affected sections / files

List spec sections, schema files, and test vectors that would need to be updated.

### Threat-model implications

Describe how this affects the threats defended against in `docs/v1/threat-model.md` and `spec/v1/11-security-considerations.md`. **This section is required for any change touching cryptography, the canonical form, or the wire format.**

### Backwards compatibility

- Does this require a new wire version? (See `spec/v1/13-iana-considerations.md`.)
- Does this affect existing implementations? Which ones, in what way?
- Are existing test vectors invalidated?

### Alternatives considered

Briefly describe any other approaches you considered and why this one is preferable.

### Prior art

Cite any external standards, RFCs, papers, or other protocols that inform the proposal.

### Implementation outline

A sketch of how the change would look in `spec/`, `schemas/`, and `test-vectors/`. Pseudocode is fine; final wording can come in the pull request.
