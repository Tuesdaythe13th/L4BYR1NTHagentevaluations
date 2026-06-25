#!/usr/bin/env python
"""
ingest.py – Data ingestion & QC for the AILuminate multilingual benchmark.

Pillar 1.3: Downloads images from a secure bucket (GCS or local path),
verifies SHA-256 hashes, validates prompts against schema.json, and
flags any records that fail QC.

Usage:
    # Validate a local JSONL file only (no image download):
    python ingest.py --input raw_prompts.jsonl --output clean_prompts.jsonl

    # Full pipeline with GCS image download:
    python ingest.py \\
        --input raw_prompts.jsonl \\
        --output clean_prompts.jsonl \\
        --image-dir ./images \\
        --bucket gs://your-bucket/images \\
        --strict

Exit codes:
    0 – success (all records passed or soft failures tolerated)
    1 – hard failure (--strict mode with QC errors, or schema load failure)
"""

import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_PROMPT_CHARS = 1500   # ≈ 200 tokens for most multilingual tokenisers
MIN_PROMPT_CHARS = 5
REQUIRED_FIELDS = {"id", "prompt_en", "prompt_local", "culture", "language", "hazard_tag"}
VALID_HAZARD_TAGS = {
    "hate", "self_harm", "political", "religious_sensitivity",
    "violence", "explicit", "historical_trauma",
    "social_norm_violation", "language_specific_taboo", "generic",
}

# ---------------------------------------------------------------------------
# Schema loader (optional – only used when jsonschema is installed)
# ---------------------------------------------------------------------------


def load_schema(schema_path: Path) -> Optional[dict]:
    try:
        import jsonschema  # noqa: F401
        with schema_path.open() as f:
            return json.load(f)
    except ImportError:
        log.warning("jsonschema not installed – skipping full schema validation.")
        return None
    except FileNotFoundError:
        log.warning("schema.json not found at %s – skipping schema validation.", schema_path)
        return None


def validate_with_schema(record: dict, schema: dict, record_id: str) -> List[str]:
    """Return list of validation error messages (empty = OK)."""
    try:
        import jsonschema
        errors = list(jsonschema.Draft7Validator(schema).iter_errors(record))
        return [f"{e.path}: {e.message}" for e in errors]
    except Exception as e:
        return [f"schema-validation-exception: {e}"]


# ---------------------------------------------------------------------------
# QC helpers
# ---------------------------------------------------------------------------

def check_required_fields(record: dict) -> List[str]:
    missing = REQUIRED_FIELDS - set(record.keys())
    return [f"missing_field:{f}" for f in sorted(missing)]


def check_prompt_length(record: dict) -> List[str]:
    issues = []
    for field in ("prompt_en", "prompt_local"):
        if field not in record:
            continue
        text = record[field]
        if not isinstance(text, str):
            issues.append(f"{field}:not_a_string")
            continue
        if len(text) < MIN_PROMPT_CHARS:
            issues.append(f"{field}:too_short ({len(text)} chars)")
        if len(text) > MAX_PROMPT_CHARS:
            issues.append(f"{field}:too_long ({len(text)} chars > {MAX_PROMPT_CHARS})")
    return issues


def check_hazard_tag(record: dict) -> List[str]:
    tag = record.get("hazard_tag", "")
    if tag not in VALID_HAZARD_TAGS:
        return [f"invalid_hazard_tag:{tag!r}"]
    return []


def check_language_code(record: dict) -> List[str]:
    lang = record.get("language", "")
    if not lang:
        return []
    if not re.match(r"^[a-z]{2,3}(-[A-Za-z]{2,3})?$", lang):
        return [f"invalid_language_code:{lang!r}"]
    return []


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_image(record: dict, image_dir: Path) -> List[str]:
    """
    If the record declares an image_sha256, check that the locally stored
    image matches it.  Returns a list of error strings (empty = OK).
    """
    image_url = record.get("image_url")
    expected_hash = record.get("image_sha256")
    if not image_url or not expected_hash:
        return []  # no image to verify

    # Derive local filename from the URL's last path segment
    filename = Path(image_url.split("/")[-1].split("?")[0])
    local_path = image_dir / filename
    if not local_path.exists():
        return [f"image_missing:{local_path}"]

    actual_hash = sha256_file(local_path)
    if actual_hash != expected_hash:
        return [f"image_sha256_mismatch: expected={expected_hash[:12]}… got={actual_hash[:12]}…"]
    return []


# ---------------------------------------------------------------------------
# Optional GCS download
# ---------------------------------------------------------------------------

def download_image_gcs(image_url: str, image_dir: Path, bucket_prefix: str) -> bool:
    """
    Download a single image from GCS using gsutil.
    image_url is assumed to be a relative path appended to bucket_prefix.
    Returns True on success.
    """
    filename = image_url.split("/")[-1].split("?")[0]
    dest = image_dir / filename
    if dest.exists():
        return True  # already cached

    gcs_path = f"{bucket_prefix.rstrip('/')}/{filename}"
    result = subprocess.run(
        ["gsutil", "cp", gcs_path, str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.warning("gsutil failed for %s: %s", gcs_path, result.stderr.strip())
        return False
    return True


# ---------------------------------------------------------------------------
# Main ingestion routine
# ---------------------------------------------------------------------------

def run_ingest(args: argparse.Namespace) -> int:
    input_path: Path = args.input
    output_path: Path = args.output
    image_dir: Optional[Path] = args.image_dir
    bucket: Optional[str] = args.bucket
    strict: bool = args.strict

    if image_dir:
        image_dir.mkdir(parents=True, exist_ok=True)

    # Load JSON Schema (best-effort)
    schema_path = Path(__file__).parent.parent / "config" / "schema.json"
    schema = load_schema(schema_path)

    # Read JSONL
    records: List[dict] = []
    with input_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                log.error("Line %d: malformed JSON – %s", lineno, e)
                if strict:
                    return 1

    log.info("Loaded %d records from %s", len(records), input_path)

    # QC pass
    passed: List[dict] = []
    all_errors: List[Dict[str, Any]] = []

    seen_ids: set = set()
    for rec in records:
        rec_id = rec.get("id", "<no-id>")
        errors: List[str] = []

        # Duplicate ID
        if rec_id in seen_ids:
            errors.append(f"duplicate_id:{rec_id}")
        seen_ids.add(rec_id)

        # Required fields
        errors += check_required_fields(rec)
        # Prompt length
        errors += check_prompt_length(rec)
        # Hazard tag
        errors += check_hazard_tag(rec)
        # Language code
        errors += check_language_code(rec)

        # Full schema validation (if available)
        if schema:
            errors += validate_with_schema(rec, schema, rec_id)

        # Image download (optional)
        if image_dir and bucket and rec.get("image_url"):
            ok = download_image_gcs(rec["image_url"], image_dir, bucket)
            if not ok:
                errors.append(f"image_download_failed:{rec['image_url']}")

        # Image integrity
        if image_dir and rec.get("image_sha256"):
            errors += verify_image(rec, image_dir)

        if errors:
            all_errors.append({"id": rec_id, "errors": errors})
            log.warning("FAIL  %s — %s", rec_id, "; ".join(errors))
        else:
            passed.append(rec)

    # Summary
    n_pass = len(passed)
    n_fail = len(all_errors)
    log.info("QC complete: %d passed, %d failed (out of %d total)", n_pass, n_fail, len(records))

    # Write clean records
    with output_path.open("w", encoding="utf-8") as out:
        for rec in passed:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log.info("Clean records written to %s", output_path)

    # Write error report alongside output
    if all_errors:
        error_report_path = output_path.with_suffix(".errors.jsonl")
        with error_report_path.open("w", encoding="utf-8") as ef:
            for entry in all_errors:
                ef.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log.info("Error report written to %s", error_report_path)

    if strict and n_fail > 0:
        log.error("Exiting with error: %d record(s) failed QC (--strict mode).", n_fail)
        return 1

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AILuminate data ingestion & QC pipeline (Pillar 1.3).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, required=True,
                        help="Raw JSONL file to validate.")
    parser.add_argument("--output", type=Path, required=True,
                        help="Cleaned JSONL file (records that passed QC).")
    parser.add_argument("--image-dir", type=Path, default=None,
                        help="Local directory for downloaded / cached images.")
    parser.add_argument("--bucket", type=str, default=None,
                        help="GCS bucket prefix for image download (e.g. gs://my-bucket/images).")
    parser.add_argument("--strict", action="store_true",
                        help="Exit with code 1 if any record fails QC (for use in CI).")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(run_ingest(parse_args()))
