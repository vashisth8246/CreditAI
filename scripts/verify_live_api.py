"""Start uvicorn live server and execute real HTTP network requests against /health and /v1/score."""
import json
import time
import subprocess
import sys
import httpx


def main():
    print("Starting live Uvicorn server: uvicorn src.api.app:app --host 127.0.0.1 --port 8000 ...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.app:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Allow server to initialize
    time.sleep(2.0)

    try:
        with httpx.Client(base_url="http://127.0.0.1:8000", timeout=5.0) as client:
            print("\n1. GET /health")
            resp1 = client.get("/health")
            print(f"Status Code: {resp1.status_code}")
            print(f"Headers: {dict(resp1.headers)}")
            print(f"Body: {resp1.text}")

            print("\n2. POST /v1/score (Valid Request)")
            valid_payload = {
                "schema_version": "1.0",
                "observation_start": "2025-01-01",
                "prediction_date": "2025-02-01",
                "request_id": "live-test-req-001",
                "transactions": [
                    {
                        "transaction_id": "live-tx-1",
                        "date": "2025-01-15",
                        "transaction_type": "credit",
                        "amount": 25000.0,
                        "category": "salary",
                    }
                ],
            }
            resp2 = client.post("/v1/score", json=valid_payload)
            print(f"Status Code: {resp2.status_code}")
            print(f"Body: {resp2.text}")

            print("\n3. POST /v1/score (Invalid Request - Out of Window Date)")
            invalid_payload = dict(valid_payload)
            invalid_payload["transactions"] = [
                {
                    "transaction_id": "live-tx-2",
                    "date": "2025-02-05",  # Post cutoff
                    "transaction_type": "credit",
                    "amount": 1000.0,
                }
            ]
            resp3 = client.post("/v1/score", json=invalid_payload)
            print(f"Status Code: {resp3.status_code}")
            print(f"Body: {resp3.text}")

            print("\n4. POST /v1/score (Invalid Request - Negative Amount & Unknown Field)")
            invalid_payload2 = {
                "schema_version": "1.0",
                "observation_start": "2025-01-01",
                "prediction_date": "2025-02-01",
                "extra_field": "secret_data",
                "transactions": [
                    {
                        "transaction_id": "live-tx-3",
                        "date": "2025-01-10",
                        "transaction_type": "credit",
                        "amount": -500.0,
                    }
                ],
            }
            resp4 = client.post("/v1/score", json=invalid_payload2)
            print(f"Status Code: {resp4.status_code}")
            print(f"Body: {resp4.text}")

    finally:
        print("\nShutting down Uvicorn server process...")
        proc.terminate()
        proc.wait(timeout=5.0)
        print("Uvicorn server stopped successfully.")


if __name__ == "__main__":
    main()
