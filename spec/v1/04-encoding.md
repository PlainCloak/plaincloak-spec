# 4. Encoding (Base62)

This section specifies the Base62 encoding used for the wire payload. The Base62 alphabet and algorithm defined here MUST be used to encode and decode the bytes that follow the third colon of every `v1` wire message.

## 4.1 Alphabet

The Base62 alphabet, in canonical order, consists of the 62 characters:

```
0 1 2 3 4 5 6 7 8 9
A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
a b c d e f g h i j k l m n o p q r s t u v w x y z
```

The character at position 0 is `0` (`U+0030`). The character at position 61 is `z` (`U+007A`). The numeric value of any alphabet character is its zero-based index in this sequence; for example, `A` has value 10, `a` has value 36, `Z` has value 35.

This ordering is fixed and case-sensitive. An implementation that treats `A` and `a` as equivalent is non-conforming.

## 4.2 Encoding algorithm

The input to the Base62 encoder is an octet string `B` of length `L` bytes (`L` MAY be zero, in which case the encoder emits the empty string). The output is a string drawn from the alphabet of 4.1.

A conforming encoder MUST produce, for any input `B`, the output produced by the following procedure:

1. Let `Z` be the count of leading `0x00` bytes at the start of `B`.
2. Let `N` be the unsigned integer obtained by interpreting `B` as a big-endian unsigned integer of length `L * 8` bits. If `L` is zero, `N` is zero.
3. Let `S` be the empty string.
4. While `N` is greater than zero:
   1. Let `r` be `N mod 62`.
   2. Prepend the alphabet character at index `r` to `S`.
   3. Set `N` to `floor(N / 62)`.
5. Prepend `Z` copies of the alphabet character at index 0 (`0`) to `S`.
6. Output `S`.

The leading-zero handling in steps 1 and 5 ensures that the encoding is bijective: every distinct octet string produces a distinct Base62 string, and the count of leading `0x00` bytes is preserved as a count of leading `0` characters.

The output of the encoder for `B = (empty)` is the empty string. The output for `B = 0x00` is `0`. The output for `B = 0x00 0x00` is `00`. The output for `B = 0x01` is `1`.

## 4.3 Decoding algorithm

The input to the Base62 decoder is a string `S` whose every character is a member of the alphabet of 4.1. The output is an octet string `B`.

A conforming decoder MUST produce, for any input `S`, the output produced by the following procedure:

1. If `S` contains any character not in the alphabet of 4.1, reject as `invalid-base62`.
2. Let `Z` be the count of leading `0` characters at the start of `S` (the alphabet character at index 0).
3. Let `T` be the substring of `S` after the leading `0` characters.
4. Let `N` be `0`.
5. For each character `c` of `T` left-to-right:
   1. Let `v` be the index of `c` in the alphabet (a value in `[0, 61]`).
   2. Set `N` to `N * 62 + v`.
6. Let `B'` be the minimal big-endian unsigned-integer encoding of `N`. If `N` is zero, `B'` is the empty octet string.
7. Output `Z` copies of the byte `0x00` followed by `B'`.

Step 6's "minimal" encoding produces the shortest octet string that, interpreted big-endian, equals `N`. Together with the leading-zero injection in step 7, this guarantees that decoding is the exact inverse of encoding.

## 4.4 Determinism

For a given input, both 4.2 and 4.3 are deterministic. There is exactly one valid Base62 string for any octet string and exactly one octet string for any valid Base62 string. Implementations MUST produce identical output to the algorithms above. Test vectors in `test-vectors/v1/deterministic/01-base62-encode.json` and `02-base62-decode.json` lock several worked examples that conforming implementations MUST reproduce byte-for-byte.

## 4.5 Choice of Base62 over Base64

The choice of Base62 (rather than Base64 or Base64url) at the wire layer is motivated by transmission resilience across messaging channels:

- Base62 contains no `+`, `/`, or `=`. None of these survive cleanly across all chat clients (`+` is reserved by some markdown dialects, `/` is treated as a path separator in some link-detection rules, `=` triggers some equation-recognition heuristics).
- Base62 contains no `_` or `-`. Both are permitted in Base64url but `_` triggers Markdown italic-emphasis processing in several renderers.
- Base62 is approximately 6% longer than Base64 for typical inputs. The compactness loss is small compared with the loss incurred by a single channel rewriting or stripping a Base64 character mid-message.

Inside the message body (Section 6), Base64 is used for the encrypted payload and signature fields. There the data is already transported inside JSON and is not subject to the same channel hazards as the bare wire payload.

## 4.6 Performance

A naive implementation of the algorithms above performs `O(L^2)` work for `L`-byte inputs because the bignum division in step 4.2.4 and the multiplication in step 4.3.5 each touch every accumulator digit on every iteration. For typical PlainCloak message sizes (under 4 KB), this is acceptable. Implementations targeting large inputs MAY use chunked Base62 algorithms or precomputed quotient tables provided that they produce bit-identical output to the reference algorithms.
