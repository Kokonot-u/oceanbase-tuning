#!/usr/bin/env python3
"""Run a small real TPC-H style 22-query workload through obclient in Docker."""

from __future__ import annotations

import csv
import os
import random
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "real_week2"
LOG_DIR = ROOT / "logs" / "real_week2"
HOST = os.environ.get("OB_HOST", "100.83.22.21")
PORT = os.environ.get("OB_PORT", "2881")
USER = os.environ.get("OB_USER", "root@test")
PASSWORD = os.environ.get("OB_PASSWORD", "")
DATABASE = os.environ.get("OB_DATABASE", "week2_bench_wang")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sql_quote(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def run_sql(sql: str, log, capture: bool = True) -> tuple[int, str, str, float]:
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql)
        tmp = f.name
    cmd = [
        "docker",
        "exec",
        "-i",
        "ob-node",
        "bash",
        "-lc",
        f"obclient -h{HOST} -P{PORT} -u{USER} -p{PASSWORD} -A -D{DATABASE} -B",
    ]
    start = time.perf_counter()
    with open(tmp, "r", encoding="utf-8") as f:
        proc = subprocess.run(cmd, stdin=f, text=True, capture_output=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    Path(tmp).unlink(missing_ok=True)
    log.write(f"\n[{now_iso()}] elapsed_ms={elapsed_ms:.3f}\n{sql[:2000]}\n")
    if proc.stdout:
        log.write(proc.stdout[-4000:])
    if proc.stderr:
        log.write(proc.stderr[-4000:])
    return proc.returncode, proc.stdout if capture else "", proc.stderr, elapsed_ms


def insert_sql(table: str, columns: list[str], rows: list[tuple], batch: int = 200) -> str:
    parts = []
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        values = ",\n".join("(" + ",".join(sql_quote(v) for v in row) + ")" for row in chunk)
        parts.append(f"INSERT INTO {table} ({','.join(columns)}) VALUES\n{values};")
    return "\n".join(parts)


def build_dataset_sql() -> str:
    random.seed(20260702)
    base = date(1993, 1, 1)
    ddl = """
DROP TABLE IF EXISTS tpch_lineitem;
DROP TABLE IF EXISTS tpch_orders;
DROP TABLE IF EXISTS tpch_partsupp;
DROP TABLE IF EXISTS tpch_part;
DROP TABLE IF EXISTS tpch_supplier;
DROP TABLE IF EXISTS tpch_customer;
DROP TABLE IF EXISTS tpch_nation;
DROP TABLE IF EXISTS tpch_region;

CREATE TABLE tpch_region (r_regionkey INT PRIMARY KEY, r_name VARCHAR(25));
CREATE TABLE tpch_nation (n_nationkey INT PRIMARY KEY, n_name VARCHAR(25), n_regionkey INT);
CREATE TABLE tpch_customer (c_custkey INT PRIMARY KEY, c_name VARCHAR(25), c_nationkey INT, c_acctbal DECIMAL(12,2), c_mktsegment VARCHAR(20));
CREATE TABLE tpch_supplier (s_suppkey INT PRIMARY KEY, s_name VARCHAR(25), s_nationkey INT, s_acctbal DECIMAL(12,2));
CREATE TABLE tpch_part (p_partkey INT PRIMARY KEY, p_name VARCHAR(55), p_mfgr VARCHAR(25), p_brand VARCHAR(10), p_type VARCHAR(25), p_size INT, p_container VARCHAR(10), p_retailprice DECIMAL(12,2));
CREATE TABLE tpch_partsupp (ps_partkey INT, ps_suppkey INT, ps_availqty INT, ps_supplycost DECIMAL(12,2), PRIMARY KEY(ps_partkey, ps_suppkey));
CREATE TABLE tpch_orders (o_orderkey INT PRIMARY KEY, o_custkey INT, o_orderstatus CHAR(1), o_totalprice DECIMAL(12,2), o_orderdate DATE, o_orderpriority VARCHAR(15), o_clerk VARCHAR(15), o_shippriority INT);
CREATE TABLE tpch_lineitem (l_orderkey INT, l_partkey INT, l_suppkey INT, l_linenumber INT, l_quantity DECIMAL(12,2), l_extendedprice DECIMAL(12,2), l_discount DECIMAL(12,2), l_tax DECIMAL(12,2), l_returnflag CHAR(1), l_linestatus CHAR(1), l_shipdate DATE, l_commitdate DATE, l_receiptdate DATE, l_shipmode VARCHAR(10), PRIMARY KEY(l_orderkey, l_linenumber));
"""
    regions = [(0, "AFRICA"), (1, "AMERICA"), (2, "ASIA"), (3, "EUROPE"), (4, "MIDDLE EAST")]
    nations = [(i, f"NATION{i}", i % 5) for i in range(25)]
    customers = [(i, f"Customer#{i}", i % 25, round(random.uniform(-500, 10000), 2), random.choice(["BUILDING", "AUTOMOBILE", "MACHINERY", "HOUSEHOLD"])) for i in range(1, 101)]
    suppliers = [(i, f"Supplier#{i}", i % 25, round(random.uniform(0, 10000), 2)) for i in range(1, 21)]
    parts = []
    for i in range(1, 101):
        parts.append((i, f"Part#{i}", f"MFGR#{i%5}", f"Brand#{i%10}", random.choice(["STANDARD", "ECONOMY", "PROMO", "LARGE BRASS", "SMALL ANODIZED"]), random.randint(1, 50), random.choice(["SM BOX", "LG BOX", "WRAP PKG"]), round(random.uniform(10, 2000), 2)))
    partsupp = [(p, s, random.randint(1, 9999), round(random.uniform(1, 500), 2)) for p in range(1, 101) for s in range(1, 6)]
    orders, lineitems = [], []
    for o in range(1, 301):
        od = base + timedelta(days=random.randint(0, 1800))
        total = 0.0
        for ln in range(1, random.randint(2, 6)):
            part = random.randint(1, 100)
            supp = random.randint(1, 20)
            qty = random.randint(1, 50)
            price = round(qty * random.uniform(20, 300), 2)
            disc = random.choice([0.0, 0.02, 0.05, 0.07, 0.1])
            tax = random.choice([0.0, 0.03, 0.05, 0.08])
            ship = od + timedelta(days=random.randint(1, 90))
            commit = ship - timedelta(days=random.randint(0, 10))
            receipt = ship + timedelta(days=random.randint(0, 10))
            total += price * (1 - disc) * (1 + tax)
            lineitems.append((o, part, supp, ln, qty, price, disc, tax, random.choice(["A", "R", "N"]), random.choice(["O", "F"]), ship.isoformat(), commit.isoformat(), receipt.isoformat(), random.choice(["MAIL", "SHIP", "RAIL", "AIR"])))
        orders.append((o, random.randint(1, 100), random.choice(["O", "F", "P"]), round(total, 2), od.isoformat(), random.choice(["1-URGENT", "2-HIGH", "3-MEDIUM", "4-NOT SPECIFIED"]), f"Clerk#{o%20}", 0))
    inserts = [
        insert_sql("tpch_region", ["r_regionkey", "r_name"], regions),
        insert_sql("tpch_nation", ["n_nationkey", "n_name", "n_regionkey"], nations),
        insert_sql("tpch_customer", ["c_custkey", "c_name", "c_nationkey", "c_acctbal", "c_mktsegment"], customers),
        insert_sql("tpch_supplier", ["s_suppkey", "s_name", "s_nationkey", "s_acctbal"], suppliers),
        insert_sql("tpch_part", ["p_partkey", "p_name", "p_mfgr", "p_brand", "p_type", "p_size", "p_container", "p_retailprice"], parts),
        insert_sql("tpch_partsupp", ["ps_partkey", "ps_suppkey", "ps_availqty", "ps_supplycost"], partsupp),
        insert_sql("tpch_orders", ["o_orderkey", "o_custkey", "o_orderstatus", "o_totalprice", "o_orderdate", "o_orderpriority", "o_clerk", "o_shippriority"], orders),
        insert_sql("tpch_lineitem", ["l_orderkey", "l_partkey", "l_suppkey", "l_linenumber", "l_quantity", "l_extendedprice", "l_discount", "l_tax", "l_returnflag", "l_linestatus", "l_shipdate", "l_commitdate", "l_receiptdate", "l_shipmode"], lineitems),
    ]
    return ddl + "\n".join(inserts)


QUERIES = {
    "Q01": "SELECT l_returnflag,l_linestatus,SUM(l_quantity),SUM(l_extendedprice),AVG(l_discount),COUNT(*) FROM tpch_lineitem WHERE l_shipdate <= DATE '1998-09-02' GROUP BY l_returnflag,l_linestatus ORDER BY l_returnflag,l_linestatus",
    "Q02": "SELECT s.s_acctbal,s.s_name,n.n_name,p.p_partkey,p.p_mfgr FROM tpch_part p JOIN tpch_partsupp ps ON p.p_partkey=ps.ps_partkey JOIN tpch_supplier s ON s.s_suppkey=ps.ps_suppkey JOIN tpch_nation n ON s.s_nationkey=n.n_nationkey WHERE p.p_size=15 ORDER BY s.s_acctbal DESC LIMIT 10",
    "Q03": "SELECT l.l_orderkey,SUM(l.l_extendedprice*(1-l.l_discount)) revenue,o.o_orderdate FROM tpch_customer c JOIN tpch_orders o ON c.c_custkey=o.o_custkey JOIN tpch_lineitem l ON l.l_orderkey=o.o_orderkey WHERE c.c_mktsegment='BUILDING' GROUP BY l.l_orderkey,o.o_orderdate ORDER BY revenue DESC LIMIT 10",
    "Q04": "SELECT o_orderpriority,COUNT(*) FROM tpch_orders WHERE o_orderdate >= DATE '1994-01-01' AND o_orderdate < DATE '1994-04-01' GROUP BY o_orderpriority ORDER BY o_orderpriority",
    "Q05": "SELECT n.n_name,SUM(l.l_extendedprice*(1-l.l_discount)) revenue FROM tpch_customer c JOIN tpch_orders o ON c.c_custkey=o.o_custkey JOIN tpch_lineitem l ON o.o_orderkey=l.l_orderkey JOIN tpch_supplier s ON l.l_suppkey=s.s_suppkey JOIN tpch_nation n ON s.s_nationkey=n.n_nationkey GROUP BY n.n_name ORDER BY revenue DESC",
    "Q06": "SELECT SUM(l_extendedprice*l_discount) revenue FROM tpch_lineitem WHERE l_shipdate >= DATE '1994-01-01' AND l_discount BETWEEN 0.05 AND 0.07 AND l_quantity < 24",
    "Q07": "SELECT supp_n.n_name, cust_n.n_name, YEAR(l.l_shipdate), SUM(l.l_extendedprice*(1-l.l_discount)) FROM tpch_supplier s JOIN tpch_lineitem l ON s.s_suppkey=l.l_suppkey JOIN tpch_orders o ON o.o_orderkey=l.l_orderkey JOIN tpch_customer c ON c.c_custkey=o.o_custkey JOIN tpch_nation supp_n ON s.s_nationkey=supp_n.n_nationkey JOIN tpch_nation cust_n ON c.c_nationkey=cust_n.n_nationkey GROUP BY supp_n.n_name,cust_n.n_name,YEAR(l.l_shipdate) LIMIT 20",
    "Q08": "SELECT YEAR(o.o_orderdate),SUM(CASE WHEN n.n_name='NATION1' THEN l.l_extendedprice*(1-l.l_discount) ELSE 0 END)/SUM(l.l_extendedprice*(1-l.l_discount)) FROM tpch_part p JOIN tpch_lineitem l ON p.p_partkey=l.l_partkey JOIN tpch_orders o ON l.l_orderkey=o.o_orderkey JOIN tpch_supplier s ON s.s_suppkey=l.l_suppkey JOIN tpch_nation n ON n.n_nationkey=s.s_nationkey GROUP BY YEAR(o.o_orderdate)",
    "Q09": "SELECT n.n_name,YEAR(o.o_orderdate),SUM(l.l_extendedprice*(1-l.l_discount)-ps.ps_supplycost*l.l_quantity) profit FROM tpch_part p JOIN tpch_lineitem l ON p.p_partkey=l.l_partkey JOIN tpch_partsupp ps ON ps.ps_partkey=l.l_partkey AND ps.ps_suppkey=l.l_suppkey JOIN tpch_orders o ON o.o_orderkey=l.l_orderkey JOIN tpch_supplier s ON s.s_suppkey=l.l_suppkey JOIN tpch_nation n ON n.n_nationkey=s.s_nationkey GROUP BY n.n_name,YEAR(o.o_orderdate) LIMIT 20",
    "Q10": "SELECT c.c_custkey,c.c_name,SUM(l.l_extendedprice*(1-l.l_discount)) revenue FROM tpch_customer c JOIN tpch_orders o ON c.c_custkey=o.o_custkey JOIN tpch_lineitem l ON l.l_orderkey=o.o_orderkey WHERE l.l_returnflag='R' GROUP BY c.c_custkey,c.c_name ORDER BY revenue DESC LIMIT 20",
    "Q11": "SELECT ps_partkey,SUM(ps_supplycost*ps_availqty) value FROM tpch_partsupp GROUP BY ps_partkey HAVING value > 10000 ORDER BY value DESC LIMIT 20",
    "Q12": "SELECT l_shipmode,SUM(CASE WHEN o_orderpriority IN ('1-URGENT','2-HIGH') THEN 1 ELSE 0 END),SUM(CASE WHEN o_orderpriority NOT IN ('1-URGENT','2-HIGH') THEN 1 ELSE 0 END) FROM tpch_orders o JOIN tpch_lineitem l ON o.o_orderkey=l.l_orderkey GROUP BY l_shipmode",
    "Q13": "SELECT c_count,COUNT(*) custdist FROM (SELECT c.c_custkey,COUNT(o.o_orderkey) c_count FROM tpch_customer c LEFT JOIN tpch_orders o ON c.c_custkey=o.o_custkey GROUP BY c.c_custkey) x GROUP BY c_count ORDER BY custdist DESC,c_count DESC",
    "Q14": "SELECT 100.00*SUM(CASE WHEN p.p_type LIKE 'PROMO%' THEN l.l_extendedprice*(1-l.l_discount) ELSE 0 END)/SUM(l.l_extendedprice*(1-l.l_discount)) promo_revenue FROM tpch_lineitem l JOIN tpch_part p ON l.l_partkey=p.p_partkey",
    "Q15": "SELECT s.s_suppkey,s.s_name,SUM(l.l_extendedprice*(1-l.l_discount)) revenue FROM tpch_supplier s JOIN tpch_lineitem l ON s.s_suppkey=l.l_suppkey GROUP BY s.s_suppkey,s.s_name ORDER BY revenue DESC LIMIT 10",
    "Q16": "SELECT p_brand,p_type,p_size,COUNT(DISTINCT ps_suppkey) supplier_cnt FROM tpch_partsupp ps JOIN tpch_part p ON p.p_partkey=ps.ps_partkey GROUP BY p_brand,p_type,p_size ORDER BY supplier_cnt DESC LIMIT 20",
    "Q17": "SELECT SUM(l.l_extendedprice)/7.0 avg_yearly FROM tpch_lineitem l JOIN tpch_part p ON p.p_partkey=l.l_partkey WHERE p.p_brand='Brand1' AND l.l_quantity < 30",
    "Q18": "SELECT c.c_name,o.o_orderkey,o.o_orderdate,o.o_totalprice,SUM(l.l_quantity) FROM tpch_customer c JOIN tpch_orders o ON c.c_custkey=o.o_custkey JOIN tpch_lineitem l ON o.o_orderkey=l.l_orderkey GROUP BY c.c_name,o.o_orderkey,o.o_orderdate,o.o_totalprice HAVING SUM(l.l_quantity)>100 ORDER BY o.o_totalprice DESC LIMIT 20",
    "Q19": "SELECT SUM(l.l_extendedprice*(1-l.l_discount)) revenue FROM tpch_lineitem l JOIN tpch_part p ON p.p_partkey=l.l_partkey WHERE p.p_brand IN ('Brand1','Brand2','Brand3') AND l.l_quantity BETWEEN 1 AND 30",
    "Q20": "SELECT s.s_name,s.s_suppkey FROM tpch_supplier s WHERE s.s_suppkey IN (SELECT ps.ps_suppkey FROM tpch_partsupp ps JOIN tpch_lineitem l ON ps.ps_partkey=l.l_partkey AND ps.ps_suppkey=l.l_suppkey GROUP BY ps.ps_suppkey HAVING SUM(l.l_quantity)>100) ORDER BY s.s_name",
    "Q21": "SELECT s.s_name,COUNT(*) numwait FROM tpch_supplier s JOIN tpch_lineitem l ON s.s_suppkey=l.l_suppkey JOIN tpch_orders o ON o.o_orderkey=l.l_orderkey WHERE o.o_orderstatus='F' GROUP BY s.s_name ORDER BY numwait DESC LIMIT 20",
    "Q22": "SELECT SUBSTRING(c.c_name,1,8) cntrycode,COUNT(*),SUM(c.c_acctbal) FROM tpch_customer c WHERE c.c_acctbal > (SELECT AVG(c_acctbal) FROM tpch_customer) GROUP BY SUBSTRING(c.c_name,1,8) ORDER BY cntrycode",
}


def main() -> int:
    if not PASSWORD:
        raise SystemExit("Set OB_PASSWORD before running TPC-H workload.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_id = "tpch_22_real_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{run_id}.log"
    rows = []
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"run_id={run_id}\nstart_time={now_iso()}\n")
        code, _, err, elapsed = run_sql(build_dataset_sql(), log, capture=False)
        if code:
            raise SystemExit(f"dataset load failed: {err[-500:]}")
        for qid, sql in QUERIES.items():
            code, out, err, elapsed = run_sql(sql + ";", log)
            result_rows = max(0, len(out.strip().splitlines()) - 1) if out else 0
            rows.append(
                {
                    "run_id": run_id,
                    "timestamp": now_iso(),
                    "db_host": HOST,
                    "tenant": USER.split("@", 1)[1] if "@" in USER else "UNKNOWN",
                    "database": DATABASE,
                    "workload": "TPC-H-22-lightweight-real",
                    "query_id": qid,
                    "elapsed_ms": round(elapsed, 3),
                    "result_rows": result_rows,
                    "status": "success" if code == 0 else "failed",
                    "error_count": 0 if code == 0 else 1,
                    "notes": "Real OceanBase SQL execution on deterministic small TPC-H style dataset",
                }
            )
        log.write(f"end_time={now_iso()}\n")
    out = OUT_DIR / "tpch_22_real.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    total = sum(float(r["elapsed_ms"]) for r in rows)
    summary = OUT_DIR / "tpch_22_summary_real.csv"
    with summary.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["run_id", "timestamp", "query_count", "total_elapsed_ms", "avg_elapsed_ms", "failed_queries", "log_file"])
        writer.writeheader()
        writer.writerow({"run_id": run_id, "timestamp": now_iso(), "query_count": len(rows), "total_elapsed_ms": round(total, 3), "avg_elapsed_ms": round(total / len(rows), 3), "failed_queries": sum(int(r["error_count"]) for r in rows), "log_file": str(log_path)})
    print(f"Wrote {out} and {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
