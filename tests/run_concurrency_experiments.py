import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
LOCUST_FILE = ROOT / "locust_concurrency.py"


EXPERIMENTS = [
    {"users": 1, "spawn_rate": 1, "run_time": "5m"},
    {"users": 5, "spawn_rate": 5, "run_time": "5m"},
    {"users": 20, "spawn_rate": 20, "run_time": "5m"},
]


def run_experiment(host: str, users: int, spawn_rate: int, run_time: str, label: str):
    csv_prefix = ROOT / f"concurrency_{label}"

    cmd = [
        "locust",
        "-f",
        str(LOCUST_FILE),
        f"--host={host}",
        "--headless",
        "-u",
        str(users),
        "-r",
        str(spawn_rate),
        "--run-time",
        run_time,
        "--csv",
        str(csv_prefix),
        "--only-summary",
    ]

    print(f"\n=== Running concurrency experiment: users={users}, spawn_rate={spawn_rate}, run_time={run_time} ===")
    subprocess.run(cmd, check=True)
    return csv_prefix.with_name(csv_prefix.name + "_stats.csv")


def extract_summary(stats_csv: Path):
    """Return (rps, p50, p95, p99, failures) for our request row."""
    with stats_csv.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Locust uses these field names in the stats CSV
            name = row.get("Name")
            if name and "POST /booking (concurrency)" in name:
                rps = float(row.get("Requests/s", 0.0))
                median = float(row.get("Median Response Time", 0.0))
                p95 = float(row.get("95%", 0.0))
                p99 = float(row.get("99%", 0.0))
                failures = int(row.get("# Failures", 0))
                return rps, median, p95, p99, failures
    return 0.0, 0.0, 0.0, 0.0, 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python run_concurrency_experiments.py http://<alb_dns_name>")
        sys.exit(1)

    host = sys.argv[1]

    summaries = []

    for exp in EXPERIMENTS:
        label = f"{exp['users']}u"
        stats_csv = run_experiment(
            host=host,
            users=exp["users"],
            spawn_rate=exp["spawn_rate"],
            run_time=exp["run_time"],
            label=label,
        )
        rps, p50, p95, p99, failures = extract_summary(stats_csv)
        summaries.append(
            {
                "users": exp["users"],
                "rps": rps,
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "failures": failures,
            }
        )

    print("\n=== Concurrency experiment summary (POST /booking (concurrency)) ===")
    print("users\tRPS\tp50(ms)\tp95(ms)\tp99(ms)\tfailures")
    for s in summaries:
        print(
            f"{s['users']}\t{s['rps']:.2f}\t{s['p50']:.1f}\t{s['p95']:.1f}\t{s['p99']:.1f}\t{s['failures']}"
        )


if __name__ == "__main__":
    main()
