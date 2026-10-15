"""
Batch Lead Ingestion — Phase 1: Preprocessing

Parses a prospects CSV, deduplicates against the Outbound Pipeline Tracker,
runs a cheap ICP pre-screen on CSV columns only (no token spend), and
generates a manifest.json that Phase 2 (the /batch-ingest command) reads.

Usage:
    python utils/batch_ingest.py prepare \
        --csv "context/prospects_export_New list_20260907_185827.csv" \
        --batch-name "batch-2026-09-08"

Requires: Python 3.10+ (stdlib only — no third-party deps).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# ICP pre-screen constants (cheap — CSV columns only)
# ---------------------------------------------------------------------------

# Geography — substring match (case-insensitive) for US/Canada
GEO_KEYWORDS: list[str] = [
    "united states", "us", "canada",
    # US states (common abbreviations + full names)
    "tx", "ny", "california", "florida", "texas", "colorado", "washington",
    "illinois", "ontario", "toronto", "vancouver",
    "alabama", "alaska", "arizona", "arkansas", "connecticut", "delaware",
    "georgia", "hawaii", "idaho", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska",
    "nevada", "new hampshire", "new jersey", "new mexico",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "utah", "vermont", "virginia", "west virginia",
    "wisconsin", "wyoming", "district of columbia",
    # Canadian provinces
    "alberta", "british columbia", "manitoba", "new brunswick",
    "newfoundland", "nova scotia", "quebec", "saskatchewan", "pe",
]

# Industry — substring match against ICP (case-insensitive)
INDUSTRY_KEYWORDS: list[str] = [
    "wholesale", "distribution", "import", "export", "e-commerce",
    "ecommerce", "manufacturing", "consumer goods", "retail",
    "logistics", "3pl", "construction", "field service",
    "food", "beverage", "professional service", "franchise",
    # Extended ICP industries from context/icp.md
    "light manufacturing", "multi-location", "trades",
    "plumbing", "hvac", "electrical", "landscaping",
    "project-based", "inventory-heavy", "multi-unit",
    "real estate", "property management", "automotive",
    "staffing", "recruiting", "consulting",
]

# Size range: 10-250 employees (inclusive)
SIZE_MIN = 10
SIZE_MAX = 250


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(first: str, last: str, company: str) -> str:
    """Deterministic lead_id: first-last-company, ASCII, kebab-case."""
    raw = f"{first} {last} {company}"
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def _load_existing_names(tracker_path: Path) -> set[str]:
    """Extract lowercased full names from the Outbound Pipeline Tracker table.

    Parses the first column of every markdown table row that starts with '|'
    and isn't a header/separator row.
    """
    if not tracker_path.exists():
        return set()

    names: set[str] = set()
    text = tracker_path.read_text(encoding="utf-8")

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")]
        # cells[0] and cells[-1] are empty (leading/trailing |)
        if len(cells) < 3:
            continue
        prospect_cell = cells[1].strip()
        # Skip header and separator rows
        if prospect_cell in ("Prospecto", "---", "") or prospect_cell.startswith("---"):
            continue
        # Skip italic placeholder rows
        if prospect_cell.startswith("*"):
            continue
        names.add(prospect_cell.lower())

    return names


def _parse_size(size_str: str) -> tuple[int | None, int | None]:
    """Parse company size string into (low, high) tuple.

    Examples:
        "11-50 employees" -> (11, 50)
        "201-500 employees" -> (201, 500)
        "10+" -> (10, None)
        "" -> (None, None)
    """
    if not size_str or not size_str.strip():
        return None, None

    cleaned = (
        size_str.strip().lower()
        .replace(",", "")
        .replace("employees", "")
        .replace("employee", "")
        .strip()
    )

    # Range pattern: "11-50" or "11 - 50"
    range_match = re.match(r"(\d+)\s*[-–]\s*(\d+)", cleaned)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))

    # Single number with "+": "10+"
    plus_match = re.match(r"(\d+)\+", cleaned)
    if plus_match:
        return int(plus_match.group(1)), None

    # Single number: "50"
    single_match = re.match(r"(\d+)", cleaned)
    if single_match:
        val = int(single_match.group(1))
        return val, val

    return None, None


def _check_geo(location: str, company_location: str) -> tuple[bool, str]:
    """Check if location matches US/Canada geography.

    Returns (pass, detail_string).
    """
    candidates = [location, company_location]
    for loc in candidates:
        if not loc:
            continue
        loc_lower = loc.lower()
        for kw in GEO_KEYWORDS:
            if kw in loc_lower:
                return True, loc.strip()

    # Determine the actual location for the rejection detail
    display = location or company_location or "Unknown"
    return False, display.strip()


def _check_industry(industry: str) -> tuple[bool | None, str]:
    """Check if industry matches ICP keywords.

    Returns (pass_or_None_if_empty, industry_string).
    """
    if not industry or not industry.strip():
        return None, ""

    industry_lower = industry.lower()
    for kw in INDUSTRY_KEYWORDS:
        if kw in industry_lower:
            return True, industry.strip()

    return False, industry.strip()


def _check_size(size_str: str) -> tuple[bool | None, str]:
    """Check if company size falls within ICP range (10-250).

    Returns (pass_or_None_if_empty, size_string).
    """
    low, high = _parse_size(size_str)
    if low is None and high is None:
        return None, size_str.strip() if size_str else ""

    # If we have at least one bound, check overlap with [SIZE_MIN, SIZE_MAX]
    effective_low = low if low is not None else SIZE_MIN
    effective_high = high if high is not None else SIZE_MAX

    if effective_high < SIZE_MIN or effective_low > SIZE_MAX:
        return False, size_str.strip()

    return True, size_str.strip()


def _map_csv_row(row: dict[str, str]) -> dict[str, str]:
    """Map CSV columns to pipeline field names."""
    first = (row.get("First Name") or "").strip()
    last = (row.get("Last Name") or "").strip()
    location = (row.get("Location") or "").strip()
    company_location = (row.get("Company Location") or "").strip()

    # Location fallback: use Company Location if Location is empty
    effective_location = location if location else company_location

    return {
        "first_name": first,
        "last_name": last,
        "email": (row.get("Email") or "").strip(),
        "linkedin_url": (row.get("LinkedIn Profile") or "").strip(),
        "location": effective_location,
        "job_title": (row.get("Job Title") or "").strip(),
        "company_name": (row.get("Company Name") or "").strip(),
        "company_website": (row.get("Company Website") or "").strip(),
        "company_industry": (row.get("Company Industry") or "").strip(),
        "company_size": (row.get("Company Size") or "").strip(),
        "raw_location": location,
        "raw_company_location": company_location,
    }


# ---------------------------------------------------------------------------
# Core: prepare
# ---------------------------------------------------------------------------

def prepare(csv_path: Path, batch_name: str) -> dict:
    """Parse CSV, dedup, pre-screen, and write manifest + rejected files.

    Returns the manifest dict for downstream use.
    """
    # 1. Parse CSV (utf-8-sig strips the BOM so DictReader keys are clean)
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Strip any residual BOM from the first header key
        if reader.fieldnames and reader.fieldnames[0].startswith("﻿"):
            reader.fieldnames[0] = reader.fieldnames[0].lstrip("﻿")
        raw_rows = list(reader)

    total_csv_rows = len(raw_rows)

    # 2. Map to pipeline fields
    mapped = [_map_csv_row(row) for row in raw_rows]

    # 3. Dedup — internal CSV duplicates (by LinkedIn URL)
    seen_linkedin: dict[str, int] = {}
    deduped: list[dict[str, str]] = []
    duplicates_removed = 0

    for lead in mapped:
        li = lead["linkedin_url"]
        if li and li in seen_linkedin:
            duplicates_removed += 1
            continue
        if li:
            seen_linkedin[li] = len(deduped)
        deduped.append(lead)

    # 4. Dedup — against existing tracker names
    tracker_path = PROJECT_ROOT / "Documents" / "Outbound_Pipeline_Tracker.md"
    existing_names = _load_existing_names(tracker_path)

    tracker_deduped: list[dict[str, str]] = []
    tracker_duplicates = 0

    for lead in deduped:
        full_name = f"{lead['first_name']} {lead['last_name']}".strip()
        name_lower = full_name.lower()

        is_duplicate = False
        for existing in existing_names:
            # Match on name alone or name + company
            if name_lower in existing or existing in name_lower:
                is_duplicate = True
                break
            # Match "FirstName LastName" pattern without spaces
            if name_lower.replace(" ", "") in existing.replace(" ", ""):
                is_duplicate = True
                break

        if is_duplicate:
            tracker_duplicates += 1
            continue
        tracker_deduped.append(lead)

    duplicates_removed += tracker_duplicates

    # 5. ICP pre-screen
    qualified: list[dict] = []
    rejected: list[dict] = []

    for lead in tracker_deduped:
        geo_pass, geo_detail = _check_geo(lead["raw_location"], lead["raw_company_location"])
        industry_pass, industry_detail = _check_industry(lead["company_industry"])
        size_pass, size_detail = _check_size(lead["company_size"])

        lead_id = _slug(lead["first_name"], lead["last_name"], lead["company_name"])

        # Determine pass/fail — geography is hard gate
        if not geo_pass:
            rejected.append({
                "lead_id": lead_id,
                "first_name": lead["first_name"],
                "last_name": lead["last_name"],
                "company_name": lead["company_name"],
                "reason": "geography",
                "detail": f"Location: {geo_detail} — outside US/Canada",
            })
            continue

        # Build pre_screen note for qualified leads
        if industry_pass is None and size_pass is None:
            note = "Insufficient CSV data — verified at signal-builder Step 0"
        elif industry_pass is None:
            note = f"Industry unknown ({industry_detail or 'empty'}) — verified at signal-builder Step 0"
        elif size_pass is None:
            note = f"Size unknown ({size_detail or 'empty'}) — verified at signal-builder Step 0"
        elif not industry_pass:
            # Industry mismatch — reject
            rejected.append({
                "lead_id": lead_id,
                "first_name": lead["first_name"],
                "last_name": lead["last_name"],
                "company_name": lead["company_name"],
                "reason": "industry",
                "detail": f"Industry: {industry_detail} — outside ICP",
            })
            continue
        elif not size_pass:
            # Size out of range — reject
            rejected.append({
                "lead_id": lead_id,
                "first_name": lead["first_name"],
                "last_name": lead["last_name"],
                "company_name": lead["company_name"],
                "reason": "company_size",
                "detail": f"Size: {size_detail} — outside {SIZE_MIN}-{SIZE_MAX} range",
            })
            continue
        else:
            note = f"Pass — size: {size_detail}, industry: {industry_detail}"

        qualified.append({
            "lead_id": lead_id,
            "first_name": lead["first_name"],
            "last_name": lead["last_name"],
            "email": lead["email"],
            "linkedin_url": lead["linkedin_url"],
            "location": lead["location"],
            "job_title": lead["job_title"],
            "company_name": lead["company_name"],
            "company_website": lead["company_website"],
            "company_industry": lead["company_industry"],
            "company_size": lead["company_size"],
            "pre_screen": {
                "size_pass": size_pass,
                "industry_pass": industry_pass,
                "geo_pass": True,
                "note": note,
            },
        })

    # 6. Build manifest
    manifest = {
        "batch_name": batch_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "csv_source": (
            str(csv_path.relative_to(PROJECT_ROOT))
            if csv_path.is_absolute()
            else str(csv_path)
        ),
        "stats": {
            "total_csv_rows": total_csv_rows,
            "duplicates_removed": duplicates_removed,
            "failed_pre_screen": len(rejected),
            "qualified_for_pipeline": len(qualified),
        },
        "qualified_leads": qualified,
        "rejected_leads": rejected,
    }

    # 7. Write batch directory
    batch_dir = PROJECT_ROOT / "batches" / batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / "results").mkdir(exist_ok=True)

    (batch_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (batch_dir / "rejected.json").write_text(
        json.dumps(rejected, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (batch_dir / "processing.log").write_text(
        f"[{datetime.now(timezone.utc).isoformat()}] Batch {batch_name} created — "
        f"{len(qualified)} qualified, {len(rejected)} rejected\n",
        encoding="utf-8",
    )

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch Lead Ingestion — Phase 1: Preprocessing",
    )
    sub = parser.add_subparsers(dest="command")

    prep = sub.add_parser("prepare", help="Parse CSV, dedup, pre-screen, generate manifest")
    prep.add_argument(
        "--csv",
        required=True,
        help="Path to prospects CSV (relative to project root or absolute)",
    )
    prep.add_argument(
        "--batch-name",
        required=True,
        help="Batch identifier, e.g. batch-2026-09-08",
    )

    args = parser.parse_args()

    if args.command == "prepare":
        csv_path = Path(args.csv)
        if not csv_path.is_absolute():
            csv_path = PROJECT_ROOT / csv_path

        if not csv_path.exists():
            print(f"Error: CSV not found at {csv_path}", flush=True)
            raise SystemExit(1)

        manifest = prepare(csv_path, args.batch_name)
        stats = manifest["stats"]

        print(f"Batch '{manifest['batch_name']}' prepared.", flush=True)
        print(f"  Total CSV rows:      {stats['total_csv_rows']}", flush=True)
        print(f"  Duplicates removed:  {stats['duplicates_removed']}", flush=True)
        print(f"  Failed pre-screen:   {stats['failed_pre_screen']}", flush=True)
        print(f"  Qualified for pipe:  {stats['qualified_for_pipeline']}", flush=True)
        print("", flush=True)

        if manifest["rejected_leads"]:
            print("Rejected leads:", flush=True)
            for r in manifest["rejected_leads"]:
                print(
                    f"  - {r['first_name']} {r['last_name']} "
                    f"({r['company_name']}): {r['reason']} — {r['detail']}",
                    flush=True,
                )
            print("", flush=True)

        batch_dir = PROJECT_ROOT / "batches" / args.batch_name
        print(f"Manifest written to:  {batch_dir / 'manifest.json'}", flush=True)
        print(f"Rejected written to:  {batch_dir / 'rejected.json'}", flush=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
