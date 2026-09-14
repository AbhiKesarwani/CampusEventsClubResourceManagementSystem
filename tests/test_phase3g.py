"""Tests for Phase 3G targeted fixes:
1. Create Account page one-page viewport layout (no vertical scroll at desktop resolution)
2. Dashboard greeting box full 4-side green border & Certificate cards 4-side borders
3. Announcements target dropdown removes 'Everyone' and displays 'Students + Coordinators'
"""
import os
import pytest
from tests.conftest import login_as


# ── 1. Create Account — One-Page Viewport Layout ─────────────────────────────
def test_register_page_one_page_layout(client):
    resp = client.get('/register')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check that html and body are constrained to 100vh on desktop
    assert 'height: 100vh' in html
    assert 'max-height: 100vh' in html
    assert 'overflow: hidden' in html
    # All required fields present
    assert 'name="name"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html
    assert 'Create Account' in html


# ── 2. Dashboard Greeting Box & Certificate Cards 4-Side Borders ─────────────
def test_dashboard_greeting_box_four_side_border(client):
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'css', 'style.css')
    assert os.path.exists(css_path)
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    # .hero-banner should have full 4-side border (border: 2px solid ...)
    assert '.hero-banner {' in css
    assert 'border: 2px solid var(--primary)' in css

    # Certificate cards
    assert '.cert-card {' in css
    assert 'border: 2px solid var(--accent-purple)' in css


def test_certificates_page_renders_cert_card_border(client, monkeypatch):
    import routes.certificates as cert_routes
    dummy_certs = [{
        'cert_id': 1, 'event_title': 'Robotics Hackathon',
        'event_date': '2026-09-14', 'issue_date': '2026-09-14'
    }]
    monkeypatch.setattr(cert_routes, 'get_user_certificates', lambda uid: dummy_certs)

    login_as(client, role='student')
    resp = client.get('/certificates/my')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'cert-card' in html
    assert 'border:2px solid var(--accent-purple)' in html


# ── 3. Announcements Target Dropdown — 'Everyone' Replaced ──────────────────
def test_announcements_target_dropdown_has_no_raw_everyone(client):
    login_as(client, role='admin')
    resp = client.get('/connect/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Must contain "Students + Coordinators"
    assert 'Students + Coordinators' in html
    # Must NOT have raw "<option value="everyone">Everyone</option>"
    assert '<option value="everyone">Everyone</option>' not in html
    assert 'All Students' in html
    assert 'All Coordinators' in html
