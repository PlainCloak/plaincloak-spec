from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

import brotli
from cryptography.hazmat.primitives import serialization

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VECTORS_DIR = REPO_ROOT / "test-vectors" / "v1"
SCHEMAS_DIR = REPO_ROOT / "schemas" / "v1"

BASE62_ALPHABET = (
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)
BASE62_INDEX: dict[str, int] = {c: i for i, c in enumerate(BASE62_ALPHABET)}

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

BODY_FIELDS = {"a", "i", "t", "s", "r", "p", "g"}

failures: list[str] = []


def fail(case_id: str, message: str) -> None:
    """Record a single check failure.

    Args:
        case_id (str): The vector case id (or file name) that failed.
        message (str): What disagreed.
    """
    failures.append(f"{case_id}: {message}")
    print(f"FAIL {case_id}: {message}")


def base62_encode(data: bytes) -> str:
    """Encode bytes per spec/v1/04-encoding.md section 4.2.

    Args:
        data (bytes): The octet string to encode.

    Returns:
        str: The Base62 encoding, with leading 0x00 bytes preserved as '0'.
    """
    leading_zeros = 0
    for byte in data:
        if byte == 0:
            leading_zeros += 1
        else:
            break
    number = int.from_bytes(data, "big")
    encoded = ""
    while number > 0:
        number, remainder = divmod(number, 62)
        encoded = BASE62_ALPHABET[remainder] + encoded
    return "0" * leading_zeros + encoded


def base62_decode(text: str) -> bytes:
    """Decode a Base62 string per spec/v1/04-encoding.md section 4.3.

    Args:
        text (str): The Base62 string to decode.

    Raises:
        ValueError: If text contains a character outside the alphabet.

    Returns:
        bytes: The decoded octet string.
    """
    for char in text:
        if char not in BASE62_INDEX:
            raise ValueError(f"invalid-base62: {char!r}")
    leading_zeros = 0
    for char in text:
        if char == "0":
            leading_zeros += 1
        else:
            break
    number = 0
    for char in text[leading_zeros:]:
        number = number * 62 + BASE62_INDEX[char]
    body = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\x00" * leading_zeros + body


def canonical_form(wire_version_int: int, body: dict) -> str:
    """Build the canonical-form string per spec/v1/07-canonical-form.md 7.2.

    Args:
        wire_version_int (int): The integer from the wire version token.
        body (dict): The message body; only the six signed fields are used.

    Returns:
        str: The colon-separated canonical form.
    """
    return (
        f"{wire_version_int}:{body['a']}:{body['i']}:{body['t']}"
        f":{body['s']}:{body['r']}:{body['p']}"
    )


def key_hash_from_pem(pem_path: Path) -> str:
    """Compute the SHA-256 SPKI key hash per spec/v1/09-key-identification.md.

    Args:
        pem_path (Path): Path to a PEM-armored public key.

    Returns:
        str: 64-character lowercase hex digest of the SPKI DER bytes.
    """
    public_key = serialization.load_pem_public_key(pem_path.read_bytes())
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()


def load_cases(file_name: str) -> list[dict]:
    """Load the cases array of a deterministic vector file.

    Args:
        file_name (str): File name inside test-vectors/v1/deterministic/.

    Returns:
        list[dict]: The vector cases.
    """
    return json.loads((VECTORS_DIR / "deterministic" / file_name).read_text())["cases"]


def check_base62_encode() -> None:
    """Check every case of deterministic/01-base62-encode.json."""
    for case in load_cases("01-base62-encode.json"):
        got = base62_encode(bytes.fromhex(case["inputs"]["bytes_hex"]))
        want = case["expected"]["base62"]
        if got != want:
            fail(case["id"], f"encoded {got!r}, expected {want!r}")


def check_base62_decode() -> None:
    """Check every case of deterministic/02-base62-decode.json."""
    for case in load_cases("02-base62-decode.json"):
        expected = case["expected"]
        if expected.get("reject"):
            try:
                base62_decode(case["inputs"]["base62"])
            except ValueError:
                continue
            fail(case["id"], "decoder accepted input that must be rejected")
        else:
            got = base62_decode(case["inputs"]["base62"]).hex()
            want = expected["bytes_hex"]
            if got != want:
                fail(case["id"], f"decoded {got!r}, expected {want!r}")


def check_brotli_roundtrip() -> None:
    """Check every case of deterministic/03-brotli-roundtrip.json."""
    for case in load_cases("03-brotli-roundtrip.json"):
        raw = bytes.fromhex(case["inputs"]["input_hex"])
        if brotli.decompress(brotli.compress(raw)) != raw:
            fail(case["id"], "compress-then-decompress did not round-trip")
        reference = case["inputs"].get("compressed_hex_for_reference")
        if reference and brotli.decompress(bytes.fromhex(reference)) != raw:
            fail(case["id"], "reference compressed bytes do not decompress to input")


def check_canonical_form() -> None:
    """Check every case of deterministic/04-canonical-form.json."""
    for case in load_cases("04-canonical-form.json"):
        got = canonical_form(case["inputs"]["wire_version_int"], case["inputs"]["body"])
        want = case["expected"]["canonical"]
        if got != want:
            fail(case["id"], f"canonical form {got!r}, expected {want!r}")


def check_key_hashes() -> None:
    """Check every case of deterministic/05-key-hash-spki.json."""
    for case in load_cases("05-key-hash-spki.json"):
        got = key_hash_from_pem(REPO_ROOT / case["inputs"]["public_key_pem_path"])
        want = case["expected"]["key_hash"]
        if got != want:
            fail(case["id"], f"key hash {got}, expected {want}")


def check_msg_id_formatting() -> None:
    """Check every case of deterministic/06-message-id-formatting.json."""
    for case in load_cases("06-message-id-formatting.json"):
        accepted = bool(UUID_V4_PATTERN.match(case["inputs"]["candidate"]))
        if accepted != case["expected"]["accept"]:
            fail(case["id"], f"accept={accepted}, expected {case['expected']['accept']}")


def check_verification_vectors() -> None:
    """Cross-check each verification vector's decoded body against `expected`.

    Decodes each wire message (envelope split, Base62, Brotli, JSON) without
    any key material and asserts that the body's a/i/t/s/r fields agree with
    the vector's own expected block, the suite is registered, the compression
    code is registered, and the body has exactly the seven v1 fields with
    well-formed p and g.
    """
    algorithms = json.loads((SCHEMAS_DIR / "algorithms.json").read_text())
    registered_suites = {suite["id"] for suite in algorithms["suites"]}
    compression = json.loads((SCHEMAS_DIR / "compression.json").read_text())
    registered_codes = {code["code"] for code in compression["codes"]}

    for vector_file in sorted((VECTORS_DIR / "verification").glob("*.json")):
        data = json.loads(vector_file.read_text())
        for case in data["cases"]:
            case_id = case["id"]
            wire = case["inputs"]["wire"]
            magic, version, comp_code, payload = wire.split(":", 3)
            if magic != "PLAINCLOAK" or version != "v1":
                fail(case_id, f"unexpected envelope {magic}:{version}")
                continue
            if comp_code not in registered_codes:
                fail(case_id, f"compression code {comp_code} not in registry")
                continue
            body = json.loads(brotli.decompress(base62_decode(payload)))

            if set(body) != BODY_FIELDS:
                fail(case_id, f"body fields {sorted(body)} != the seven v1 fields")
            if body["a"] not in registered_suites:
                fail(case_id, f"suite {body['a']} not in algorithms registry")
            if not UUID_V4_PATTERN.match(body["i"]):
                fail(case_id, f"body i {body['i']!r} is not canonical UUIDv4")
            for field in ("p", "g"):
                try:
                    base64.b64decode(body[field], validate=True)
                except Exception:
                    fail(case_id, f"body {field} is not well-formed Base64")

            expected = case["expected"]
            pairs = (
                ("msg_id", "i"),
                ("timestamp", "t"),
                ("sender_key_hash", "s"),
                ("recipient_key_hash", "r"),
            )
            for expected_key, body_key in pairs:
                if expected_key in expected and expected[expected_key] != body[body_key]:
                    fail(
                        case_id,
                        f"expected.{expected_key}={expected[expected_key]!r} but "
                        f"body {body_key}={body[body_key]!r}",
                    )


def check_spec_literals() -> None:
    """Check that byte-exact worked examples in the prose match the vectors.

    Guards the canonical-form line in appendix A.2 (vector 01) and the AAD
    line in section 8.10.4 (vector 07) against future drift.
    """
    def decoded_body(vector_file: str) -> dict:
        data = json.loads((VECTORS_DIR / "verification" / vector_file).read_text())
        payload = data["cases"][0]["inputs"]["wire"].split(":", 3)[3]
        return json.loads(brotli.decompress(base62_decode(payload)))

    body_01 = decoded_body("01-rsa2048-roundtrip.json")
    appendix = (REPO_ROOT / "spec" / "v1" / "appendix-a-examples.md").read_text()
    canonical_prefix = canonical_form(1, {**body_01, "p": ""})
    if canonical_prefix + "<p>" not in appendix:
        fail(
            "spec-literal-appendix-a",
            "A.2 canonical-form line does not match vector 01's body",
        )

    body_07 = decoded_body("07-rsa2048-hybrid-roundtrip.json")
    crypto_suites = (REPO_ROOT / "spec" / "v1" / "08-crypto-suites.md").read_text()
    aad = (
        f"1:{body_07['a']}:{body_07['i']}:{body_07['t']}"
        f":{body_07['s']}:{body_07['r']}:"
    )
    if aad not in crypto_suites:
        fail(
            "spec-literal-8.10.4",
            "section 8.10.4 AAD example does not match vector 07's body",
        )


def main() -> int:
    """Run all consistency checks.

    Returns:
        int: 0 when every check passes, 1 otherwise.
    """
    check_base62_encode()
    check_base62_decode()
    check_brotli_roundtrip()
    check_canonical_form()
    check_key_hashes()
    check_msg_id_formatting()
    check_verification_vectors()
    check_spec_literals()
    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("all vector consistency checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
