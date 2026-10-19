"""Inspect LendingClub CSV and UCI datasets using chunked streaming."""
import pandas as pd
import os
import glob

LC_CSV = r"f:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI\Data\archive\accepted_2007_to_2018Q4.csv"

def inspect_lendingclub():
    print("--- Inspecting LendingClub CSV ---")
    if not os.path.exists(LC_CSV):
        print("LendingClub CSV not found at:", LC_CSV)
        return

    file_size_bytes = os.path.getsize(LC_CSV)
    print(f"File Size: {file_size_bytes / (1024**3):.2f} GB ({file_size_bytes:,} bytes)")

    chunk_size = 100000
    total_rows = 0
    status_counts = {}
    issue_dates = set()
    cols = None

    for chunk in pd.read_csv(LC_CSV, chunksize=chunk_size, low_memory=False):
        if cols is None:
            cols = list(chunk.columns)
        total_rows += len(chunk)

        if 'loan_status' in chunk.columns:
            counts = chunk['loan_status'].value_counts(dropna=False).to_dict()
            for status, val in counts.items():
                status_str = str(status)
                status_counts[status_str] = status_counts.get(status_str, 0) + val

        if 'issue_d' in chunk.columns:
            valid_issues = chunk['issue_d'].dropna().unique()
            issue_dates.update(valid_issues)

    print(f"Total Rows Processed: {total_rows:,}")
    print(f"Total Columns Found: {len(cols)}")
    print("\n--- Distinct loan_status Frequencies ---")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_rows) * 100
        print(f"  '{status}': {count:,} ({pct:.2f}%)")

    print(f"\nUnique Issue Dates Count: {len(issue_dates)}")
    sample_dates = sorted(list(issue_dates))[:5] + sorted(list(issue_dates))[-5:]
    print("Sample Issue Dates:", sample_dates)
    print("\nColumn List:")
    print(cols)

def inspect_uci():
    print("\n--- Inspecting UCI Datasets ---")
    base_uci = r"f:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI\Data\credit_default"
    for root, dirs, files in os.walk(base_uci):
        for f in files:
            full_path = os.path.join(root, f)
            size = os.path.getsize(full_path)
            print(f"  {os.path.relpath(full_path, base_uci)}: {size:,} bytes")

if __name__ == "__main__":
    inspect_lendingclub()
    inspect_uci()
