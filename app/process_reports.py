"""
process_reports.py

Batch job: processes a directory of insurance CLAIMS EXTRACT CSVs (in
production, regional claims offices could generate thousands of these
daily/nightly) and produces:
  1. A per-file summary (row/column counts, numeric stats)
  2. An aggregate rollup across ALL files (totals by office and status)

All sample data used with this project is synthetic and fictional --
this demonstrates the PATTERN used in real insurance claims processing
(e.g. consolidating claims extracts, similar in spirit to the kind of
nightly batch consolidation platforms like DXC Assure Claims perform),
not a connection to any real system or client data.

Design choices driven by "thousands of files" scale, not a toy demo:
  - Progress is logged every N files, not per-file, so logs stay readable
    at 3,000+ files instead of scrolling forever.
  - A single malformed/corrupt CSV is logged and skipped, not fatal --
    a batch job processing thousands of files can't abort the whole run
    over one bad upload from one office.
  - Aggregation happens with pandas.concat rather than re-reading files,
    so memory/CPU cost scales roughly linearly with file count.

This script starts, processes the batch, writes output, and exits --
the "reproducible execution" pattern, not a long-running service.
"""

import glob
import json
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"
PROGRESS_LOG_INTERVAL = 100  # log a heartbeat every N files, not every file


def find_csv_files(input_dir: str) -> list[str]:
    return sorted(glob.glob(os.path.join(input_dir, "*.csv")))


def summarize_file(filepath: str) -> tuple[dict, pd.DataFrame]:
    df = pd.read_csv(filepath)

    numeric_cols = df.select_dtypes(include="number").columns
    summary = {
        "file": os.path.basename(filepath),
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_column_stats": {
            col: {
                "sum": float(df[col].sum()),
                "mean": round(float(df[col].mean()), 2),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
            }
            for col in numeric_cols
        },
    }
    return summary, df


def build_aggregate(all_frames: list[pd.DataFrame]) -> dict:
    if not all_frames:
        return {}

    combined = pd.concat(all_frames, ignore_index=True)
    aggregate = {
        "total_claim_rows_across_all_files": len(combined),
    }

    if "claims_payout_amount" in combined.columns:
        aggregate["total_claims_payout_amount"] = float(
            combined["claims_payout_amount"].sum()
        )
    if "claims_processed" in combined.columns:
        aggregate["total_claims_processed"] = int(
            combined["claims_processed"].sum()
        )

    if "claims_office" in combined.columns and "claims_payout_amount" in combined.columns:
        by_office = (
            combined.groupby("claims_office")["claims_payout_amount"]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )
        aggregate["payout_by_office"] = {k: float(v) for k, v in by_office.items()}

    if "claim_status" in combined.columns:
        by_status = combined["claim_status"].value_counts().to_dict()
        aggregate["claim_count_by_status"] = {k: int(v) for k, v in by_status.items()}

    return aggregate


def main() -> int:
    start = time.monotonic()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Batch job started")

    if not os.path.isdir(INPUT_DIR):
        print(f"ERROR: input directory '{INPUT_DIR}' not found.")
        return 1

    csv_files = find_csv_files(INPUT_DIR)
    total_files = len(csv_files)
    if total_files == 0:
        print(f"No CSV files found in '{INPUT_DIR}'. Nothing to process.")
        return 0

    print(f"Found {total_files} claims-extract file(s) to process.")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    summaries = []
    frames = []
    failed_files = []

    for i, filepath in enumerate(csv_files, start=1):
        try:
            summary, df = summarize_file(filepath)
            summaries.append(summary)
            frames.append(df)
        except Exception as exc:
            failed_files.append({"file": os.path.basename(filepath), "error": str(exc)})

        if i % PROGRESS_LOG_INTERVAL == 0 or i == total_files:
            elapsed = time.monotonic() - start
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  Progress: {i}/{total_files} files "
                  f"({rate:.1f} files/sec, {len(failed_files)} failed)")

    aggregate = build_aggregate(frames)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files_found": total_files,
        "files_processed_successfully": len(summaries),
        "files_failed": len(failed_files),
        "failed_files": failed_files,
        "aggregate": aggregate,
        "per_file_summaries": summaries,
    }

    report_path = os.path.join(OUTPUT_DIR, "summary_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    txt_report_path = os.path.join(OUTPUT_DIR, "summary_report.txt")
    with open(txt_report_path, "w") as f:
        f.write("CLAIMS BATCH JOB SUMMARY REPORT (synthetic demo data)\n")
        f.write("=" * 55 + "\n")
        f.write(f"Files found:      {total_files}\n")
        f.write(f"Processed OK:     {len(summaries)}\n")
        f.write(f"Failed:           {len(failed_files)}\n\n")
        f.write("AGGREGATE TOTALS\n")
        f.write("-" * 55 + "\n")
        for key, value in aggregate.items():
            if isinstance(value, dict):
                f.write(f"{key}:\n")
                for k, v in value.items():
                    f.write(f"   {k}: {v}\n")
            else:
                f.write(f"{key}: {value}\n")
        if failed_files:
            f.write("\nFAILED FILES\n")
            f.write("-" * 55 + "\n")
            for ff in failed_files:
                f.write(f"{ff['file']}: {ff['error']}\n")

    elapsed = time.monotonic() - start
    print(f"Processed {len(summaries)}/{total_files} files in {elapsed:.1f}s "
          f"({len(failed_files)} failed)")
    print(f"Reports written to: {report_path}, {txt_report_path}")
    print(f"[{datetime.now(timezone.utc).isoformat()}] Batch job finished. Exiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
