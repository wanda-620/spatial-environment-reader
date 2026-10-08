#!/usr/bin/env python3
"""Create a non-destructive workspace for spatial evidence analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path


SUPPORTED = {".jpg", ".jpeg", ".png", ".pdf", ".ppt", ".pptx"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", header[16:24])
    return None


def jpeg_size(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            return None
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                return None
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if marker in {
                b"\x01",
                b"\xd0",
                b"\xd1",
                b"\xd2",
                b"\xd3",
                b"\xd4",
                b"\xd5",
                b"\xd6",
                b"\xd7",
                b"\xd8",
                b"\xd9",
            }:
                continue
            length_data = handle.read(2)
            if len(length_data) != 2:
                return None
            length = struct.unpack(">H", length_data)[0]
            if length < 2:
                return None
            if marker and marker[0] in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:
                payload = handle.read(5)
                if len(payload) != 5:
                    return None
                height, width = struct.unpack(">HH", payload[1:5])
                return width, height
            handle.seek(length - 2, 1)


def pdf_page_count(path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # type: ignore

        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def pptx_slide_count(path: Path) -> int | None:
    try:
        with zipfile.ZipFile(path) as archive:
            return sum(
                1
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
    except (OSError, zipfile.BadZipFile):
        return None


def file_record(path: Path, source_root: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    width = height = None
    if suffix == ".png":
        size = png_size(path)
        if size:
            width, height = size
    elif suffix in {".jpg", ".jpeg"}:
        size = jpeg_size(path)
        if size:
            width, height = size

    count = None
    if suffix == ".pdf":
        count = pdf_page_count(path)
    elif suffix == ".pptx":
        count = pptx_slide_count(path)

    return {
        "source_file": path.relative_to(source_root).as_posix(),
        "file_type": suffix.lstrip("."),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "image_width_px": width,
        "image_height_px": height,
        "page_or_slide_count": count,
        "inspection_status": "pending",
        "notes": "",
    }


REPORT = """# 空间环境分析报告

## 1. 结论摘要

## 2. 材料清单与覆盖

## 3. 空间总览

## 4. 逐展项空间卡

## 5. 尺寸台账

## 6. 互动空间评估

## 7. 冲突、未知与风险

## 8. 最小补充清单

## 9. 证据索引
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("case_dir", type=Path)
    args = parser.parse_args()

    source_root = args.source_dir.expanduser().resolve()
    case_dir = args.case_dir.expanduser().resolve()
    if not source_root.is_dir():
        parser.error(f"source_dir is not a directory: {source_root}")
    if (
        case_dir == source_root
        or source_root in case_dir.parents
        or case_dir in source_root.parents
    ):
        parser.error("source_dir and case_dir must not contain one another")

    if case_dir.exists():
        parser.error(f"case_dir already exists; choose a new path: {case_dir}")
    case_dir.mkdir(parents=True)

    paths = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED
    )
    manifest = {
        "source_root": str(source_root),
        "supported_extensions": sorted(SUPPORTED),
        "source_count": len(paths),
        "sources": [file_record(path, source_root) for path in paths],
    }
    (case_dir / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (case_dir / "evidence.jsonl").write_text("", encoding="utf-8")
    (case_dir / "spatial-report.md").write_text(REPORT, encoding="utf-8")

    print(f"Created case with {len(paths)} supported source file(s): {case_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
