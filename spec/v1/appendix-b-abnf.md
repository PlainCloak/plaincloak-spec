# Appendix B. Consolidated ABNF

This appendix collects the complete ABNF grammar for the `v1` wire envelope. The grammar is also stored as a separate file at `schemas/v1/wire.abnf`; both are normative. If the two disagree, the version in `schemas/v1/wire.abnf` is authoritative because it is the version consumed by automated tooling.

Notation is per [RFC 5234] with the case-sensitive string-literal extension of [RFC 7405].

```abnf
; PlainCloak v1 wire-format grammar.

wire-message    = magic ":" version ":" comp-code ":" wire-payload

magic           = %s"PLAINCLOAK"
version         = %s"v1"
comp-code       = 2(ALPHA-UPPER)
wire-payload    = 1*BASE62-CHAR

BASE62-CHAR     = DIGIT / ALPHA-UPPER / ALPHA-LOWER

ALPHA-UPPER     = %x41-5A          ; A-Z
ALPHA-LOWER     = %x61-7A          ; a-z
DIGIT           = %x30-39          ; 0-9
```

Notes on the grammar:

- The `magic` and `version` literals use the case-sensitive `%s"..."` form. A `v1` parser MUST treat `PLAINCLOAK` as case-sensitive uppercase and `v1` as case-sensitive lowercase.
- `comp-code` is a two-character uppercase token. The set of valid values for `v1` is closed at `BR`, `ZS`, and `NO` per Section 5.1; the grammar permits any two-uppercase-letter token because future-version parsers may extend the registry.
- `wire-payload` is one-or-more Base62 characters. The empty payload is forbidden by the grammar; an empty wire payload is therefore a parse error.
- The grammar does not bound `wire-payload` length. Bounds are imposed indirectly by Section 5.4 (decompression budget) and by message-channel limits external to this specification.

For the JSON message body inside the wire payload, the normative grammar is `schemas/v1/message.schema.json` (a JSON Schema); ABNF is not used to describe JSON.
