#!/usr/bin/env python3
"""Run a lightweight real SQL workload via obclient inside Docker."""

from __future__ import annotations

import csv
import json
import math
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "real_week2"
LOG_DIR = ROOT / "logs" / "real_week2"
HOST = os.environ.get("OB_HOST", "100.83.22.21")
PORT = os.environ.get("OB_PORT", "2881")
USER = os.environ.get("OB_USER", "root@test")
PASSWORD = os.environ.get("OB_PASSWORD", "")
DATABASE = "week2_bench_wang"
TENANT = "test"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] * (c - k) + ordered[c] * (k - f)


def run_sql(sql: str, log_file, capture: bool = False) -> tuple[int, str, str, float]:
    cmd = [
        "docker",
        "exec",
        "ob-node",
        "bash",
        "-lc",
        f"obclient -h{HOST} -P{PORT} -u{USER} -p{PASSWORD} -A -D{DATABASE} -B -e {json.dumps(sql)}",
    ]
    start = time.perf_counter()
    proc = subprocess.run(cmd, text=True, capture_output=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    log_file.write(f"\n[{now_iso()}] SQL ({elapsed_ms:.2f} ms): {sql}\n")
    if proc.stdout:
        log_file.write(proc.stdout)
    if proc.stderr:
        log_file.write(proc.stderr)
    return proc.returncode, proc.stdout if capture else "", proc.stderr, elapsed_ms


def append_result(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_id",
        "timestamp",
        "db_host",
        "tenant",
        "database",
        "workload",
        "operation",
        "elapsed_ms",
        "qps_or_tps",
        "avg_latency_ms",
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "error_count",
        "rows_inserted",
        "rows_read",
        "rows_updated",
        "notes",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not PASSWORD:
        raise SystemExit("Set OB_PASSWORD before running this script.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "real_week2_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    random.seed(42)
    details: list[dict] = []
    all_latencies: list[float] = []
    total_errors = 0
    total_inserted = 0
    total_read = 0
    total_updated = 0
    run_start = time.perf_counter()

    with (LOG_DIR / "workload_run.log").open("a", encoding="utf-8") as log:
        log.write(f"\n===== workload start {now_iso()} run_id={run_id} =====\n")
        setup_sql = """
CREATE TABLE IF NOT EXISTS workload_kv (
  run_id VARCHAR(64) NOT NULL,
  id INT NOT NULL,
  category INT NOT NULL,
  value_num INT NOT NULL,
  payload VARCHAR(128),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (run_id, id),
  KEY idx_category (category),
  KEY idx_value_num (value_num)
);
"""
        code, _, _, elapsed = run_sql(setup_sql, log)
        total_errors += 1 if code else 0
        all_latencies.append(elapsed)

        # Batch insert 1000 real rows in 10 chunks.
        for chunk in range(10):
            values = []
            for i in range(chunk * 100 + 1, chunk * 100 + 101):
                values.append(f"('{run_id}',{i},{i % 20},{(i * 37) % 10000},'payload_{i}')")
            sql = "INSERT INTO workload_kv(run_id,id,category,value_num,payload) VALUES " + ",".join(values)
            code, _, _, elapsed = run_sql(sql, log)
            total_errors += 1 if code else 0
            total_inserted += 0 if code else len(values)
            all_latencies.append(elapsed)
            details.append({"operation": "batch_insert", "elapsed_ms": elapsed, "rows_inserted": 0 if code else len(values), "rows_read": 0, "rows_updated": 0, "error_count": 1 if code else 0})

        # Point SELECT workload.
        for _ in range(80):
            rid = random.randint(1, 1000)
            code, out, _, elapsed = run_sql(f"SELECT id, category, value_num FROM workload_kv WHERE run_id='{run_id}' AND id={rid}", log, capture=True)
            total_errors += 1 if code else 0
            total_read += 0 if code else max(0, len(out.strip().splitlines()) - 1)
            all_latencies.append(elapsed)
            details.append({"operation": "point_select", "elapsed_ms": elapsed, "rows_inserted": 0, "rows_read": 0 if code else 1, "rows_updated": 0, "error_count": 1 if code else 0})

        # Range SELECT workload.
        for _ in range(30):
            start_id = random.randint(1, 950)
            code, out, _, elapsed = run_sql(f"SELECT COUNT(*) AS cnt, SUM(value_num) AS sum_value FROM workload_kv WHERE run_id='{run_id}' AND id BETWEEN {start_id} AND {start_id + 49}", log, capture=True)
            total_errors += 1 if code else 0
            total_read += 0 if code else 50
            all_latencies.append(elapsed)
            details.append({"operation": "range_select", "elapsed_ms": elapsed, "rows_inserted": 0, "rows_read": 0 if code else 50, "rows_updated": 0, "error_count": 1 if code else 0})

        # GROUP BY aggregate workload.
        for _ in range(20):
            code, out, _, elapsed = run_sql(f"SELECT category, COUNT(*) AS cnt, AVG(value_num) AS avg_value FROM workload_kv WHERE run_id='{run_id}' GROUP BY category", log, capture=True)
            total_errors += 1 if code else 0
            total_read += 0 if code else 1000
            all_latencies.append(elapsed)
            details.append({"operation": "group_by", "elapsed_ms": elapsed, "rows_inserted": 0, "rows_read": 0 if code else 1000, "rows_updated": 0, "error_count": 1 if code else 0})

        # UPDATE workload.
        for _ in range(40):
            rid = random.randint(1, 1000)
            code, _, _, elapsed = run_sql(f"UPDATE workload_kv SET value_num=value_num+1 WHERE run_id='{run_id}' AND id={rid}", log)
            total_errors += 1 if code else 0
            total_updated += 0 if code else 1
            all_latencies.append(elapsed)
            details.append({"operation": "update", "elapsed_ms": elapsed, "rows_inserted": 0, "rows_read": 0, "rows_updated": 0 if code else 1, "error_count": 1 if code else 0})

        # Mixed read/write loop.
        for i in range(40):
            rid = random.randint(1, 1000)
            if i % 3 == 0:
                sql = f"UPDATE workload_kv SET payload='mixed_{i}' WHERE run_id='{run_id}' AND id={rid}"
                rows_updated = 1
                rows_read = 0
            else:
                sql = f"SELECT id, payload FROM workload_kv WHERE run_id='{run_id}' AND id={rid}"
                rows_updated = 0
                rows_read = 1
            code, _, _, elapsed = run_sql(sql, log)
            total_errors += 1 if code else 0
            total_updated += 0 if code else rows_updated
            total_read += 0 if code else rows_read
            all_latencies.append(elapsed)
            details.append({"operation": "mixed_read_write", "elapsed_ms": elapsed, "rows_inserted": 0, "rows_read": 0 if code else rows_read, "rows_updated": 0 if code else rows_updated, "error_count": 1 if code else 0})

        total_elapsed_ms = (time.perf_counter() - run_start) * 1000
        operation_count = len(all_latencies)
        qps_or_tps = operation_count / (total_elapsed_ms / 1000)
        summary = {
            "run_id": run_id,
            "timestamp": now_iso(),
            "db_host": HOST,
            "tenant": TENANT,
            "database": DATABASE,
            "workload": "lightweight_real_sql",
            "operation": "summary",
            "elapsed_ms": round(total_elapsed_ms, 3),
            "qps_or_tps": round(qps_or_tps, 3),
            "avg_latency_ms": round(sum(all_latencies) / len(all_latencies), 3),
            "p50_latency_ms": round(percentile(all_latencies, 0.50), 3),
            "p95_latency_ms": round(percentile(all_latencies, 0.95), 3),
            "p99_latency_ms": round(percentile(all_latencies, 0.99), 3),
            "error_count": total_errors,
            "rows_inserted": total_inserted,
            "rows_read": total_read,
            "rows_updated": total_updated,
            "notes": "real obclient workload through Docker; includes client invocation overhead",
        }
        log.write(f"===== workload end {now_iso()} run_id={run_id} summary={json.dumps(summary, ensure_ascii=False)} =====\n")

    detail_rows = []
    for idx, rec in enumerate(details, start=1):
        detail_rows.append(
            {
                "run_id": run_id,
                "timestamp": now_iso(),
                "db_host": HOST,
                "tenant": TENANT,
                "database": DATABASE,
                "workload": "lightweight_real_sql",
                "operation": rec["operation"],
                "elapsed_ms": round(rec["elapsed_ms"], 3),
                "qps_or_tps": "",
                "avg_latency_ms": "",
                "p50_latency_ms": "",
                "p95_latency_ms": "",
                "p99_latency_ms": "",
                "error_count": rec["error_count"],
                "rows_inserted": rec["rows_inserted"],
                "rows_read": rec["rows_read"],
                "rows_updated": rec["rows_updated"],
                "notes": f"step={idx}",
            }
        )
    append_result(OUT_DIR / "workload_baseline_real.csv", detail_rows)
    append_result(OUT_DIR / "workload_summary_real.csv", [summary])
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
