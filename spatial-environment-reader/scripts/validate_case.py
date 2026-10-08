#!/usr/bin/env python3
"""Validate the source manifest and spatial evidence JSONL records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EVIDENCE_TYPES = {
    "explicit_text",
    "visible_geometry",
    "dimension_annotation",
    "cross_view_match",
    "calibrated_estimate",
    "inference",
    "unknown",
}
CONFIDENCE = {"high", "medium", "low"}
REQUIRED = {
    "evidence_id",
    "source_file",
    "locator",
    "evidence_type",
    "observation",
    "supports",
    "confidence",
    "method",
}


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path.name}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()
    case_dir = args.case_dir.expanduser().resolve()
    manifest_path = case_dir / "source_manifest.json"
    evidence_path = case_dir / "evidence.jsonl"

    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_json(manifest_path)
    except ValueError as exc:
        errors.append(str(exc))
        manifest = {}

    sources = set()
    if isinstance(manifest, dict) and isinstance(manifest.get("sources"), list):
        for item in manifest["sources"]:
            if isinstance(item, dict) and isinstance(item.get("source_file"), str):
                sources.add(item["source_file"])
    else:
        errors.append("source_manifest.json must contain a sources array")

    if not evidence_path.is_file():
        errors.append("missing evidence.jsonl")
        lines: list[str] = []
    else:
        lines = evidence_path.read_text(encoding="utf-8").splitlines()

    records: list[dict[str, object]] = []
    ids: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"evidence line {number}: invalid JSON: {exc}")
            continue
        if not isinstance(record, dict):
            errors.append(f"evidence line {number}: record must be an object")
            continue
        records.append(record)
        missing = sorted(REQUIRED - record.keys())
        if missing:
            errors.append(f"evidence line {number}: missing {', '.join(missing)}")

        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append(f"evidence line {number}: evidence_id must be a string")
        elif evidence_id in ids:
            errors.append(f"evidence line {number}: duplicate evidence_id {evidence_id}")
        else:
            ids.add(evidence_id)

        source_file = record.get("source_file")
        if source_file not in sources:
            errors.append(
                f"evidence line {number}: source_file not in manifest: {source_file!r}"
            )
        if record.get("evidence_type") not in EVIDENCE_TYPES:
            errors.append(f"evidence line {number}: invalid evidence_type")
        if record.get("confidence") not in CONFIDENCE:
            errors.append(f"evidence line {number}: invalid confidence")
        if not isinstance(record.get("supports"), list):
            errors.append(f"evidence line {number}: supports must be an array")

        if "value" in record and not record.get("unit"):
            errors.append(f"evidence line {number}: numeric value requires unit")
        if record.get("evidence_type") in {"inference", "calibrated_estimate"}:
            depends_on = record.get("depends_on")
            if not isinstance(depends_on, list) or not depends_on:
                errors.append(
                    f"evidence line {number}: derived evidence requires depends_on"
                )
        if record.get("evidence_type") == "unknown" and record.get("confidence") == "high":
            warnings.append(
                f"evidence line {number}: unknown fact normally should not be high confidence"
            )

    for number, record in enumerate(records, start=1):
        depends_on = record.get("depends_on", [])
        if isinstance(depends_on, list):
            missing_ids = [item for item in depends_on if item not in ids]
            if missing_ids:
                errors.append(
                    f"record {record.get('evidence_id', number)}: unknown dependencies "
                    + ", ".join(map(str, missing_ids))
                )

    if not records:
        warnings.append("no evidence records yet")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"Validation passed: {len(records)} record(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
