#!/usr/bin/env python3
"""Parse a short BenchmarkSQL run log into a CSV row."""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    log_file, out_csv, run_id, host, user, database = sys.argv[1:7]
    text = Path(log_file).read_text(errors="replace")
    errors = len(re.findall(r"(?i)\b(ERROR|Exception|SQLException|Timeout)\b", text))
    measured = re.search(r"Measured tpmC \(NewOrders\) =\s*([0-9.]+)", text)
    measured_total = re.search(r"Measured tpmTOTAL =\s*([0-9.]+)", text)
    txn_count = re.search(r"Transaction Count =\s*([0-9]+)", text)
    tpmc = float(measured.group(1)) if measured else 0.0
    tpm_total = float(measured_total.group(1)) if measured_total else 0.0
    result_csv = Path(log_file).parents[1] / ".." / "outputs" / "real_week2" / run_id / "data" / "result.csv"
    latencies = []
    if result_csv.exists():
        with result_csv.open(newline="", encoding="utf-8") as f:
            for rec in csv.DictReader(f):
                if rec.get("ttype") == "DELIVERY_BG":
                    continue
                if rec.get("error") not in ("0", "", None):
                    errors += 1
                try:
                    latencies.append(float(rec["latency"]))
                except Exception:
                    pass
    latencies.sort()

    def percentile(p: float) -> float:
        if not latencies:
            return 0.0
        idx = round((len(latencies) - 1) * p)
        return latencies[max(0, min(len(latencies) - 1, idx))]
    fields = [
        "run_id",
        "timestamp",
        "db_host",
        "tenant",
        "database",
        "workload",
        "elapsed_ms",
        "tpmc",
        "tpm_total",
        "qps_or_tps",
        "avg_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "transaction_count",
        "error_count",
        "status",
        "notes",
        "log_file",
    ]
    row = {
        "run_id": run_id,
        "timestamp": now_iso(),
        "db_host": host,
        "tenant": user.split("@", 1)[1] if "@" in user else "UNKNOWN",
        "database": database,
        "workload": "BenchmarkSQL_TPC-C",
        "elapsed_ms": "",
        "tpmc": tpmc or "",
        "tpm_total": tpm_total or "",
        "qps_or_tps": round(tpm_total / 60, 4) if tpm_total else "",
        "avg_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else "",
        "p95_latency_ms": round(percentile(0.95), 3) if latencies else "",
        "p99_latency_ms": round(percentile(0.99), 3) if latencies else "",
        "transaction_count": int(txn_count.group(1)) if txn_count else len(latencies),
        "error_count": errors,
        "status": "real_run_completed" if errors == 0 else "real_run_with_errors",
        "notes": "Parsed from BenchmarkSQL 5.0 log and result.csv; qps_or_tps is measured tpmTOTAL/60",
        "log_file": log_file,
    }
    out = Path(out_csv)
    exists = out.exists()
    with out.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    print(row)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
