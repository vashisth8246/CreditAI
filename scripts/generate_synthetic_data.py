from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.data.generate import generate_synthetic_data
if __name__=="__main__":
    out=ROOT/"data"/"synthetic_phase1_1"; out.mkdir(parents=True,exist_ok=True)
    tx, labels=generate_synthetic_data(); tx.to_csv(out/"transactions.csv",index=False); labels.to_csv(out/"outcomes.csv",index=False)
    print(f"Saved synthetic development data: {labels.borrower_id.nunique()} borrowers, {len(tx)} transactions")
