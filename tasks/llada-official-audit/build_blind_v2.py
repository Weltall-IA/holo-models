#!/usr/bin/env python3
"""Blind 6-way review v2: uniform-correct vs wrong-schedule vs community vs Krea/Z/FLUX.
Sources are pre-existing PNGs only. No inference. New shuffle, independent mapping."""
import hashlib
import json
import random
import shutil
import struct
from pathlib import Path
from PIL import Image

ROOT = Path("/home/alpha/Playstoria/models")
AUDIT = ROOT / "tasks/llada-official-audit"
REVIEW = AUDIT / "review-uniform-v2"
BLIND = REVIEW / "blind"
GRIDS = REVIEW / "grids"
OLD = AUDIT / "outputs/llada-official-turbo-fp8"
NEW = AUDIT / "outputs/llada-official-turbo-uniform-v2"
BASE = ROOT / "benchmarks/image-t2i-16gb-v1/outputs/raw"

CANDIDATES = [
    "LLADA_OFFICIAL_TURBO_UNIFORM_CORRECT",
    "LLADA_OFFICIAL_TURBO_WRONG_SCHEDULE",
    "LLADA_COMMUNITY_INT8_Q4",
    "KREA_TURBO_INT8",
    "Z_IMAGE_TURBO_NVFP4",
    "FLUX_KLEIN_STOCK",
]
CASES = ["T01", "T03", "T06"]
TEXT_CHUNKS = {b"tEXt", b"zTXt", b"iTXt"}
LABELS = ["A", "B", "C", "D", "E", "F"]

SOURCES = {
    "T01": {
        "LLADA_OFFICIAL_TURBO_UNIFORM_CORRECT": NEW / "T01_51001.png",
        "LLADA_OFFICIAL_TURBO_WRONG_SCHEDULE": OLD / "T01_51001.png",
        "LLADA_COMMUNITY_INT8_Q4": BASE / "t2i_T01_llada.png",
        "KREA_TURBO_INT8": BASE / "t2i_T01_krea.png",
        "Z_IMAGE_TURBO_NVFP4": BASE / "t2i_T01_z-image.png",
        "FLUX_KLEIN_STOCK": BASE / "t2i_T01_flux2-klein.png",
    },
    "T03": {
        "LLADA_OFFICIAL_TURBO_UNIFORM_CORRECT": NEW / "T03_51003.png",
        "LLADA_OFFICIAL_TURBO_WRONG_SCHEDULE": OLD / "T03_51003.png",
        "LLADA_COMMUNITY_INT8_Q4": BASE / "t2i_T03_llada.png",
        "KREA_TURBO_INT8": BASE / "t2i_T03_krea.png",
        "Z_IMAGE_TURBO_NVFP4": BASE / "t2i_T03_z-image.png",
        "FLUX_KLEIN_STOCK": BASE / "t2i_T03_flux2-klein.png",
    },
    "T06": {
        "LLADA_OFFICIAL_TURBO_UNIFORM_CORRECT": NEW / "T06_51006.png",
        "LLADA_OFFICIAL_TURBO_WRONG_SCHEDULE": OLD / "T06_51006.png",
        "LLADA_COMMUNITY_INT8_Q4": BASE / "t2i_T06_llada.png",
        "KREA_TURBO_INT8": BASE / "t2i_T06_krea.png",
        "Z_IMAGE_TURBO_NVFP4": BASE / "t2i_T06_z-image.png",
        "FLUX_KLEIN_STOCK": BASE / "t2i_T06_flux2-klein.png",
    },
}


def strip_png_metadata(source: Path, destination: Path) -> None:
    data = source.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        shutil.copy2(source, destination)
        return
    output = bytearray(data[:8])
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        end = offset + 12 + length
        chunk = data[offset:end]
        if chunk_type not in TEXT_CHUNKS:
            output.extend(chunk)
        offset = end
    destination.write_bytes(output)


def main() -> None:
    BLIND.mkdir(parents=True, exist_ok=True)
    GRIDS.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict[str, str]] = {}
    seen: dict[str, str] = {}
    for idx, case_id in enumerate(CASES):
        for cand, src in SOURCES[case_id].items():
            assert src.exists(), f"missing {src}"
            with Image.open(src) as im:
                assert im.size == (1024, 1024), f"bad size {src}"
                assert im.mode in ("RGB", "RGBA"), f"bad mode {src}"
            h = hashlib.sha256(src.read_bytes()).hexdigest()
            assert h not in seen, f"duplicate hash: {src} == {seen[h]}"
            seen[h] = str(src)
        labels = list(LABELS)
        rng = random.Random(77000 + idx * 29)
        rng.shuffle(labels)
        mapping[case_id] = {}
        case_dir = BLIND / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        canvas = Image.new("RGB", (1024 * 6, 1024), (18, 18, 18))
        for cand, label in zip(CANDIDATES, labels):
            mapping[case_id][label] = cand
            strip_png_metadata(SOURCES[case_id][cand], case_dir / f"{label}.png")
            with Image.open(case_dir / f"{label}.png") as im:
                visual = im.convert("RGB")
                assert visual.size == (1024, 1024) and not im.info
                canvas.paste(visual, (LABELS.index(label) * 1024, 0))
        canvas.save(GRIDS / f"{case_id}.png", format="PNG")
        print(f"grid saved: {case_id}.png")
    contact = Image.new("RGB", (1024 * 6, 1024 * len(CASES)), (18, 18, 18))
    for i, case_id in enumerate(CASES):
        contact.paste(Image.open(GRIDS / f"{case_id}.png").convert("RGB"), (0, i * 1024))
    contact.save(GRIDS / "ALL.png", format="PNG")
    (REVIEW / "BLIND_MAPPING.json").write_text(json.dumps(mapping, indent=2) + "\n")
    print("mapping saved (hidden)")


if __name__ == "__main__":
    main()
