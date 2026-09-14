# locustfile.py — CampusOps concurrency / load testing
# ─────────────────────────────────────────────────────────────────────────────
# Prerequisites:
#   1. CampusOps must be running (python wsgi.py  OR  python app.py)
#   2. locust must be installed (pip install locust)
#   3. A student/admin/coordinator account must exist in the live DB
#
# Quick usage (headless, CI-friendly):
#   locust --headless -u 10  -r 2  --run-time 30s  --host http://127.0.0.1:5000
#   locust --headless -u 50  -r 5  --run-time 60s  --host http://127.0.0.1:5000
#   locust --headless -u 100 -r 10 --run-time 60s  --host http://127.0.0.1:5000
#   locust --headless -u 150 -r 15 --run-time 60s  --host http://127.0.0.1:5000
#
# Web UI mode (see graphs live):
#   locust --host http://127.0.0.1:5000
#   → open http://127.0.0.1:8089
# ─────────────────────────────────────────────────────────────────────────────

import os
from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger("campusops.loadtest")

# ── Credentials (override via env vars or edit here) ─────────────────────────
STUDENT_EMAIL    = os.getenv("LOCUST_STUDENT_EMAIL",    "test_student@example.com")
STUDENT_PASSWORD = os.getenv("LOCUST_STUDENT_PASSWORD", "Test@1234")
ADMIN_EMAIL      = os.getenv("LOCUST_ADMIN_EMAIL",      "test_admin@example.com")
ADMIN_PASSWORD   = os.getenv("LOCUST_ADMIN_PASSWORD",   "Admin@1234")


# ─────────────────────────────────────────────────────────────────────────────
# Student user — typical read-heavy workload
# ─────────────────────────────────────────────────────────────────────────────
class StudentUser(HttpUser):
    """Simulates a logged-in student browsing the platform."""
    weight       = 80          # 80 % of virtual users are students
    wait_time    = between(1, 4)  # realistic think time
    _logged_in   = False

    def on_start(self):
        """Login once per virtual user at startup."""
        resp = self.client.post(
            "/login",
            data={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
            allow_redirects=True,
            name="/login [student]",
        )
        if resp.status_code == 200 and "dashboard" in resp.url:
            self._logged_in = True
        else:
            logger.warning("Student login failed (status=%s)", resp.status_code)

    # ── Page tasks (weighted) ─────────────────────────────────────────────

    @task(5)
    def dashboard(self):
        self.client.get("/dashboard", name="/dashboard")

    @task(4)
    def events_list(self):
        self.client.get("/events", name="/events")

    @task(3)
    def clubs_list(self):
        self.client.get("/clubs", name="/clubs")

    @task(2)
    def notifications(self):
        self.client.get("/notifications", name="/notifications")

    @task(2)
    def campus_connect(self):
        self.client.get("/connect", name="/connect")

    @task(2)
    def search(self):
        self.client.get("/search?q=music", name="/search")

    @task(1)
    def calendar(self):
        self.client.get("/calendar", name="/calendar")

    @task(1)
    def profile(self):
        self.client.get("/profile", name="/profile")

    @task(1)
    def certificates(self):
        self.client.get("/certificates", name="/certificates")

    @task(1)
    def recommendations(self):
        self.client.get("/recommendations", name="/recommendations")


# ─────────────────────────────────────────────────────────────────────────────
# Admin user — management tasks (lighter, but DB-heavy operations)
# ─────────────────────────────────────────────────────────────────────────────
class AdminUser(HttpUser):
    """Simulates an admin managing the platform."""
    weight       = 20          # 20 % of virtual users are admins
    wait_time    = between(2, 6)

    def on_start(self):
        resp = self.client.post(
            "/login",
            data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            allow_redirects=True,
            name="/login [admin]",
        )
        if resp.status_code != 200:
            logger.warning("Admin login failed (status=%s)", resp.status_code)

    @task(3)
    def admin_dashboard(self):
        self.client.get("/dashboard", name="/dashboard [admin]")

    @task(2)
    def admin_panel(self):
        self.client.get("/admin", name="/admin")

    @task(1)
    def admin_events(self):
        self.client.get("/events", name="/events [admin]")

    @task(1)
    def admin_clubs(self):
        self.client.get("/clubs", name="/clubs [admin]")

    @task(1)
    def admin_venues(self):
        self.client.get("/venues", name="/venues")


# ─────────────────────────────────────────────────────────────────────────────
# Event hooks — print a summary line when the test finishes
# ─────────────────────────────────────────────────────────────────────────────
@events.quitting.add_listener
def on_locust_quit(environment, **kwargs):
    stats = environment.stats
    total = stats.total
    print("\n" + "=" * 60)
    print("CAMPUSOPS LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"  Total requests   : {total.num_requests}")
    print(f"  Failures         : {total.num_failures}")
    print(f"  Failure rate     : {total.fail_ratio * 100:.1f}%")
    print(f"  Avg response time: {total.avg_response_time:.0f} ms")
    print(f"  95th percentile  : {total.get_response_time_percentile(0.95):.0f} ms")
    print(f"  99th percentile  : {total.get_response_time_percentile(0.99):.0f} ms")
    print(f"  Max response time: {total.max_response_time:.0f} ms")
    print(f"  RPS (avg)        : {total.total_rps:.1f}")
    print("=" * 60)
    # Emit pass/fail verdict
    if total.fail_ratio > 0.05:
        print("⚠  VERDICT: FAIL — failure rate exceeds 5%")
    elif total.get_response_time_percentile(0.95) > 3000:
        print("⚠  VERDICT: WARN — P95 latency > 3 s (degraded UX)")
    else:
        print("✓  VERDICT: PASS")
    print("=" * 60)
