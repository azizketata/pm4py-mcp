#!/usr/bin/env python
"""Download canonical process-mining benchmark event logs from 4TU.ResearchData.

The bundled `examples/running-example.xes` is a 3-case toy. Real demonstration
and Phase 3 prompt templates need real-sized logs. This script fetches them on
demand and drops them in ``examples/benchmarks/`` (gitignored).

Usage
-----
    python scripts/download_benchmark_logs.py                  # sepsis (smallest, default)
    python scripts/download_benchmark_logs.py sepsis
    python scripts/download_benchmark_logs.py bpi2012
    python scripts/download_benchmark_logs.py bpi2017
    python scripts/download_benchmark_logs.py all
    python scripts/download_benchmark_logs.py --list

Behavior
--------
* Idempotent: if a file is already on disk with the expected MD5, the download
  is skipped.
* Streaming + md5 verification: downloads chunk-by-chunk, hashing on the fly.
  On checksum mismatch the partial file is discarded.
* Atomic: writes to ``.part`` and renames on success.
* Stdlib-only — no extra dependencies.

Sources
-------
All files are public datasets from 4TU.ResearchData (DOI-backed, permanent).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BENCHMARKS_DIR = Path(__file__).resolve().parent.parent / "examples" / "benchmarks"
_USER_AGENT = "pm4py-mcp-benchmark-downloader/0.3.0"


@dataclass(frozen=True)
class Benchmark:
    slug: str
    url: str
    filename: str
    size_bytes: int
    md5: str
    description: str


BENCHMARKS: dict[str, Benchmark] = {
    "sepsis": Benchmark(
        slug="sepsis",
        url="https://data.4tu.nl/file/33632f3c-5c48-40cf-8d8f-2db57f5a6ce7/643dccf2-985a-459e-835c-a82bce1c0339",
        filename="sepsis.xes.gz",
        size_bytes=202_508,
        md5="b5671166ac71eb20680d3c74616c43d2",
        description=(
            "Sepsis Cases (Mannhardt, 2016) — hospital sepsis pathway, "
            "~1000 cases, ~15k events, 16 activities. Classic teaching log."
        ),
    ),
    "bpi2012": Benchmark(
        slug="bpi2012",
        url="https://data.4tu.nl/file/533f66a4-8911-4ac7-8612-1235d65d1f37/3276db7f-8bee-4f2b-88ee-92dbffb5a893",
        filename="bpi2012.xes.gz",
        size_bytes=3_342_406,
        md5="74c7ba9aba85bfcb181a22c9d565e5b5",
        description=(
            "BPI Challenge 2012 — Dutch financial institution loan applications. "
            "Predecessor to BPI 2017; smaller and widely cited."
        ),
    ),
    "bpi2017": Benchmark(
        slug="bpi2017",
        url="https://data.4tu.nl/file/34c3f44b-3101-4ea9-8281-e38905c68b8d/f3aec4f7-d52c-4217-82f4-57d719a8298c",
        filename="bpi2017.xes.gz",
        size_bytes=29_658_747,
        md5="10b37a2f78e870d78406198403ff13d2",
        description=(
            "BPI Challenge 2017 — richer loan-application process, "
            "larger event count, successor to BPI 2012."
        ),
    ),
}


def _human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _md5_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(bench: Benchmark, out: Path) -> None:
    print(f"downloading {bench.slug} -> {out.name}  ({_human_size(bench.size_bytes)})")
    req = urllib.request.Request(bench.url, headers={"User-Agent": _USER_AGENT})
    h = hashlib.md5()
    tmp = out.with_suffix(out.suffix + ".part")
    chunk_size = 64 * 1024
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, tmp.open("wb") as f:
            downloaded = 0
            total = bench.size_bytes
            last_pct = -1
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                downloaded += len(chunk)
                pct = int(downloaded * 100 / total) if total else 0
                # Update display every 5% to avoid terminal spam on tiny files
                if pct != last_pct and pct % 5 == 0:
                    print(f"  {pct:3d}%  ({_human_size(downloaded)})", end="\r", flush=True)
                    last_pct = pct
        print()  # newline after the \r progress updates
    except (urllib.error.URLError, TimeoutError) as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"download failed for {bench.slug}: {exc}") from exc
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    actual_md5 = h.hexdigest()
    if actual_md5 != bench.md5:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"md5 mismatch for {bench.slug}: expected {bench.md5}, got {actual_md5}")
    tmp.replace(out)
    print(f"  ok: {out}  ({_human_size(out.stat().st_size)}, md5 verified)")


def ensure(bench: Benchmark) -> Path:
    """Ensure the benchmark is on disk with correct MD5; download if missing or stale."""
    out = BENCHMARKS_DIR / bench.filename
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

    if out.exists():
        actual_md5 = _md5_of_file(out)
        if actual_md5 == bench.md5:
            print(
                f"{bench.slug}: already on disk ({out})  "
                f"[{_human_size(out.stat().st_size)}, md5 verified]  skipping"
            )
            return out
        print(
            f"{bench.slug}: on disk but md5 mismatch "
            f"(got {actual_md5}, expected {bench.md5}); re-downloading"
        )

    _download(bench, out)
    return out


def _list_benchmarks() -> None:
    print("Available benchmarks:\n")
    for b in BENCHMARKS.values():
        print(f"  {b.slug:10s}  {_human_size(b.size_bytes):>9s}  {b.description}")
    print(f"\nFiles land in: {BENCHMARKS_DIR}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="download_benchmark_logs",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "which",
        nargs="?",
        default="sepsis",
        choices=[*BENCHMARKS, "all"],
        help="Benchmark to download (default: sepsis)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available benchmarks and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        _list_benchmarks()
        return 0

    to_fetch = list(BENCHMARKS.values()) if args.which == "all" else [BENCHMARKS[args.which]]

    for b in to_fetch:
        try:
            ensure(b)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
