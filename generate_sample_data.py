"""
generate_sample_data.py

Generates synthetic insurance CLAIMS EXTRACT files to simulate a
realistic scenario: multiple regional claims offices exporting daily
claim-status batches that need consolidated nightly processing.

IMPORTANT: all data here is randomly generated and fictional. This is
a portfolio/learning demo, not connected to any real claims system,
client, or policyholder data.

Not part of the Docker image itself -- this is a one-time local helper
to populate ./input with realistic-scale test data before you run the
batch job. Run it directly with Python, not inside the container:

    python generate_sample_data.py --count 2000
"""

import argparse
import csv
import os
import random

CLAIMS_OFFICES = ["Northeast", "Southeast", "Midwest", "West", "Central"]
CLAIM_TYPES = ["Auto", "Property", "Liability", "Workers Comp", "Bodily Injury"]
CLAIM_STATUSES = ["Open", "Under Review", "Approved", "Denied", "Closed"]


def generate_file(filepath: str, rows: int, seed: int) -> None:
    rng = random.Random(seed)
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "claims_office", "claim_type", "claim_status",
            "claims_processed", "claims_payout_amount",
        ])
        for _ in range(rows):
            office = rng.choice(CLAIMS_OFFICES)
            claim_type = rng.choice(CLAIM_TYPES)
            status = rng.choice(CLAIM_STATUSES)
            processed = rng.randint(1, 50)
            avg_payout = rng.uniform(500, 15000)
            writer.writerow([
                office, claim_type, status, processed,
                round(processed * avg_payout, 2),
            ])


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic insurance claims-extract CSVs for scale testing."
    )
    parser.add_argument("--count", type=int, default=1000,
                         help="Number of CSV files to generate (default: 1000)")
    parser.add_argument("--rows-per-file", type=int, default=20,
                         help="Rows per CSV file (default: 20)")
    parser.add_argument("--output-dir", default="input",
                         help="Directory to write files into (default: ./input)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Generating {args.count} synthetic claims-extract CSV files "
          f"({args.rows_per_file} rows each) into '{args.output_dir}/' ...")

    for i in range(args.count):
        filename = f"claims_extract_office_{i:05d}.csv"
        filepath = os.path.join(args.output_dir, filename)
        generate_file(filepath, args.rows_per_file, seed=i)
        if (i + 1) % 500 == 0:
            print(f"  ... {i + 1}/{args.count} files written")

    print(f"Done. {args.count} files written to '{args.output_dir}/'.")
    print("Note: all data is synthetic/fictional, for demo purposes only.")


if __name__ == "__main__":
    main()
