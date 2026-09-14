#!/usr/bin/env python3
# run_load_test.py — CampusOps Automated Load Test Runner
# ─────────────────────────────────────────────────────────────────────────────
# Starts Waitress on a free port, runs Locust headless at 4 concurrency levels,
# captures metrics, then writes results/load_test_report.txt.
#
# Usage:
#   python run_load_test.py
#
# Pre-requisites:
#   - CampusOps MySQL database running with at least one student/admin account.
#   - Set LOCUST_STUDENT_EMAIL, LOCUST_STUDENT_PASSWORD, LOCUST_ADMIN_EMAIL,
#     LOCUST_ADMIN_PASSWORD env vars (or edit locustfile.py defaults).
#   - pip install waitress locust  (already in requirements.txt)
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys
import time
import socket
import signal
import subprocess
import threading
import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
HOST              = '127.0.0.1'
SPAWN_WAIT_SECS   = 4        # seconds to wait for server to be ready
RESULTS_DIR       = 'results'
REPORT_FILE       = os.path.join(RESULTS_DIR, 'load_test_report.txt')

# Test levels: (users, spawn-rate, run-time-seconds)
TEST_LEVELS = [
    (10,   2,  30),
    (50,   5,  60),
    (100, 10,  60),
    (150, 15,  60),
]

THRESHOLDS = {
    'max_fail_pct':  5.0,   # fail % must be < 5 %
    'p95_warn_ms':  3000,   # P95 latency < 3 s = OK
    'p95_fail_ms':  5000,   # P95 latency > 5 s = FAIL
}


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def wait_for_server(host, port, timeout=15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def run_locust_headless(host_url, users, spawn_rate, run_time_secs,
                        csv_prefix) -> dict:
    """Run locust headless and parse its CSV stats output."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    cmd = [
        sys.executable, '-m', 'locust',
        '--headless',
        f'-u', str(users),
        f'-r', str(spawn_rate),
        f'--run-time', f'{run_time_secs}s',
        f'--host', host_url,
        '--csv', csv_prefix,
        '--csv-full-history',
        '--only-summary',
    ]
    print(f"\n  → locust -u {users} -r {spawn_rate} --run-time {run_time_secs}s")
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    # Parse the _stats.csv for totals
    stats_file = csv_prefix + '_stats.csv'
    metrics = {
        'users': users,
        'run_time': run_time_secs,
        'requests': 0,
        'failures': 0,
        'fail_pct': 0.0,
        'avg_ms': 0.0,
        'p50_ms': 0.0,
        'p95_ms': 0.0,
        'p99_ms': 0.0,
        'rps': 0.0,
        'verdict': 'UNKNOWN',
        'raw_stdout': result.stdout[-3000:],
    }
    if os.path.exists(stats_file):
        import csv
        with open(stats_file, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row.get('Name') == 'Aggregated':
                    reqs = int(row.get('Request Count', 0))
                    fails = int(row.get('Failure Count', 0))
                    metrics['requests'] = reqs
                    metrics['failures'] = fails
                    metrics['fail_pct'] = (fails / reqs * 100) if reqs else 0.0
                    metrics['avg_ms']   = float(row.get('Average Response Time', 0) or 0)
                    metrics['p50_ms']   = float(row.get('50%', 0) or 0)
                    metrics['p95_ms']   = float(row.get('95%', 0) or 0)
                    metrics['p99_ms']   = float(row.get('99%', 0) or 0)
                    metrics['rps']      = float(row.get('Requests/s', 0) or 0)
                    break

    # Determine verdict
    if metrics['fail_pct'] >= THRESHOLDS['max_fail_pct']:
        metrics['verdict'] = 'FAIL (high error rate)'
    elif metrics['p95_ms'] >= THRESHOLDS['p95_fail_ms']:
        metrics['verdict'] = 'FAIL (P95 too slow)'
    elif metrics['p95_ms'] >= THRESHOLDS['p95_warn_ms']:
        metrics['verdict'] = 'WARN (P95 degraded)'
    else:
        metrics['verdict'] = 'PASS'

    return metrics


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    port = find_free_port()
    host_url = f'http://{HOST}:{port}'

    print("=" * 62)
    print("  CampusOps — Production Load Test")
    print(f"  Server : {host_url}")
    print(f"  Levels : {[u for u, _, _ in TEST_LEVELS]} users")
    print("=" * 62)

    # ── Start production server (Waitress) ─────────────────────────────────
    print(f"\n[1/3] Starting Waitress on port {port} …")
    server_cmd = [
        sys.executable, 'wsgi.py',
    ]
    env = os.environ.copy()
    env['HOST'] = HOST
    env['PORT'] = str(port)
    env['FLASK_DEBUG'] = 'false'

    server_proc = subprocess.Popen(
        server_cmd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    if not wait_for_server(HOST, port):
        print("ERROR: Server did not start within 15 s. Aborting.")
        server_proc.terminate()
        sys.exit(1)
    print(f"  Server is up (PID {server_proc.pid})")

    # ── Run load tests ──────────────────────────────────────────────────────
    print("\n[2/3] Running load tests …")
    all_results = []
    for users, rate, duration in TEST_LEVELS:
        prefix = os.path.join(RESULTS_DIR, f'locust_u{users}')
        metrics = run_locust_headless(host_url, users, rate, duration, prefix)
        all_results.append(metrics)
        verdict_icon = '✓' if metrics['verdict'] == 'PASS' else '⚠'
        print(
            f"  {verdict_icon} u={users:3d} | "
            f"reqs={metrics['requests']:5d} | "
            f"fail={metrics['fail_pct']:4.1f}% | "
            f"avg={metrics['avg_ms']:6.0f}ms | "
            f"p95={metrics['p95_ms']:6.0f}ms | "
            f"RPS={metrics['rps']:5.1f} | "
            f"{metrics['verdict']}"
        )

    # ── Stop server ─────────────────────────────────────────────────────────
    print("\n[3/3] Stopping Waitress …")
    server_proc.terminate()
    server_proc.wait(timeout=10)

    # ── Write report ────────────────────────────────────────────────────────
    write_report(all_results, host_url)
    print(f"\nReport written to: {REPORT_FILE}")

    # Overall verdict
    overall = 'PASS'
    for m in all_results:
        if 'FAIL' in m['verdict']:
            overall = 'FAIL'
        elif 'WARN' in m['verdict'] and overall == 'PASS':
            overall = 'WARN'
    print(f"\n{'=' * 62}")
    print(f"  OVERALL: {overall}")
    print(f"{'=' * 62}\n")


def write_report(results, host_url):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        "=" * 62,
        "  CampusOps — Production Readiness Load Test Report",
        f"  Generated : {now}",
        f"  Target    : {host_url}",
        f"  Server    : Waitress (Windows-compatible WSGI)",
        "=" * 62,
        "",
        "THRESHOLDS",
        f"  Fail rate     : < {THRESHOLDS['max_fail_pct']}%   → FAIL above",
        f"  P95 latency   : < {THRESHOLDS['p95_warn_ms']} ms → OK",
        f"                  < {THRESHOLDS['p95_fail_ms']} ms → WARN",
        f"                  ≥ {THRESHOLDS['p95_fail_ms']} ms → FAIL",
        "",
        "RESULTS",
        "",
        f"  {'Users':>5} | {'Requests':>8} | {'Failures':>8} | {'Fail%':>6} | "
        f"{'Avg ms':>7} | {'P50 ms':>7} | {'P95 ms':>7} | {'P99 ms':>7} | "
        f"{'RPS':>6} | Verdict",
        "  " + "-" * 80,
    ]
    for m in results:
        lines.append(
            f"  {m['users']:>5} | {m['requests']:>8} | {m['failures']:>8} | "
            f"{m['fail_pct']:>5.1f}% | {m['avg_ms']:>7.0f} | {m['p50_ms']:>7.0f} | "
            f"{m['p95_ms']:>7.0f} | {m['p99_ms']:>7.0f} | {m['rps']:>6.1f} | "
            f"{m['verdict']}"
        )

    # Determine if 100-user claim is supported
    u100 = next((m for m in results if m['users'] == 100), None)
    u150 = next((m for m in results if m['users'] == 150), None)

    lines += [
        "",
        "CONCURRENCY ASSESSMENT",
        "",
    ]
    if u100:
        if u100['verdict'] == 'PASS':
            lines.append("  ✓ 100 simultaneous users: SUPPORTED")
            lines.append(f"    (fail={u100['fail_pct']:.1f}%, P95={u100['p95_ms']:.0f}ms)")
        elif 'WARN' in u100['verdict']:
            lines.append("  ⚠ 100 simultaneous users: SUPPORTED WITH DEGRADATION")
            lines.append(f"    (fail={u100['fail_pct']:.1f}%, P95={u100['p95_ms']:.0f}ms)")
        else:
            lines.append("  ✗ 100 simultaneous users: NOT SUPPORTED")
            lines.append(f"    (fail={u100['fail_pct']:.1f}%, P95={u100['p95_ms']:.0f}ms)")
    if u150:
        if u150['verdict'] == 'PASS':
            lines.append("  ✓ 150 simultaneous users: SUPPORTED")
        elif 'WARN' in u150['verdict']:
            lines.append("  ⚠ 150 simultaneous users: SUPPORTED WITH DEGRADATION")
        else:
            lines.append("  ✗ 150 simultaneous users: NOT SUPPORTED")

    lines += [
        "",
        "=" * 62,
    ]

    with open(REPORT_FILE, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
