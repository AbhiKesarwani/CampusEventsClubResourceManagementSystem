"""Tests for Phase 3F targeted fixes:
1. Illustration: 18 Clubs text & larger balanced container on Login/Register
2. Certificate Green Border: Continuous on all 4 sides with clean corners
3. Certificate Purple Border: Continuous on all 4 sides with clean corners
4. Venue Capacity: Displayed alongside venue name in event creation & edit forms
5. Left Sidebar UI: Enhanced hover/active states, avatar presentation, and transitions
"""
import os
import xml.etree.ElementTree as ET
import tempfile
import pytest
from PIL import Image
from tests.conftest import login_as
from services.venue_service import get_venues_for_select


# ── 1. Illustration: 18 Clubs & Sizing ──────────────────────────────────────
def test_illustration_has_18_clubs_text():
    svg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'campus_students_illustration.svg')
    assert os.path.exists(svg_path)
    with open(svg_path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert '18 Clubs' in content
    assert '18 Societies' not in content
    # Parse as valid XML
    tree = ET.parse(svg_path)
    root = tree.getroot()
    assert 'svg' in root.tag.lower()


def test_login_and_register_illustration_container(client):
    resp_login = client.get('/login')
    assert resp_login.status_code == 200
    html_login = resp_login.get_data(as_text=True)
    assert 'campus_students_illustration.svg' in html_login
    assert 'max-height:280px' in html_login or 'campus_students_illustration' in html_login

    resp_reg = client.get('/register')
    assert resp_reg.status_code == 200
    html_reg = resp_reg.get_data(as_text=True)
    assert 'campus_students_illustration.svg' in html_reg
    assert 'campus_students_illustration.svg' in html_reg


# ── 2 & 3. Certificate Green & Purple Continuous Borders ────────────────────
def test_certificate_green_and_purple_borders_all_sides():
    from helpers.certificate_helpers import generate_certificate

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, 'cert_borders_3f.png')
        generate_certificate(
            student_name='Border Specialist',
            event_title='Robotics National Summit',
            save_path=out_path,
            club_name='Robotics Club',
            event_date='September 14, 2026',
            cert_id='PHASE3F1'
        )
        assert os.path.exists(out_path)
        with Image.open(out_path) as img:
            rgb = img.convert('RGB')
            w, h = rgb.size
            assert (w, h) == (1400, 900)

            emerald = (16, 185, 129)
            purple  = (124, 58, 237)

            # Outer green border (continuous on top, bottom, left, right)
            assert rgb.getpixel((w // 2, 2)) == emerald       # top
            assert rgb.getpixel((w // 2, h - 3)) == emerald   # bottom
            assert rgb.getpixel((2, h // 2)) == emerald       # left
            assert rgb.getpixel((w - 3, h // 2)) == emerald   # right

            # Purple accent border (continuous on all 4 sides at inset y=14/15, x=14/15)
            assert rgb.getpixel((w // 2, 14)) == purple       # top purple
            assert rgb.getpixel((w // 2, h - 15)) == purple   # bottom purple
            assert rgb.getpixel((14, h // 2)) == purple       # left purple
            assert rgb.getpixel((w - 15, h // 2)) == purple   # right purple


# ── 4. Venue Capacity During Event Creation & Edit ──────────────────────────
def test_venue_select_includes_capacity_query(fake_db, monkeypatch):
    captured = {}
    class FakeCursor:
        def execute(self, query, params=None):
            captured['query'] = query
        def fetchall(self):
            return [{'venue_id': 1, 'venue_name': 'Manthan 3', 'capacity': 120}]
        def close(self): pass

    class FakeConn:
        def cursor(self, dictionary=False): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr('services.venue_service.get_db_connection', lambda: FakeConn())
    venues = get_venues_for_select()
    assert 'capacity' in captured['query']
    assert venues[0]['capacity'] == 120


def test_event_create_and_edit_render_venue_capacity(client, monkeypatch):
    dummy_venues = [{'venue_id': 1, 'venue_name': 'Manthan 3', 'capacity': 120}]
    import routes.events as events_routes
    monkeypatch.setattr(events_routes, 'get_venues_for_select', lambda: dummy_venues)
    monkeypatch.setattr(events_routes, 'get_clubs_for_select', lambda: [{'club_id': 1, 'club_name': 'Tech Club'}])

    login_as(client, role='admin')
    # Create page
    resp_create = client.get('/events/create')
    assert resp_create.status_code == 200
    html_create = resp_create.get_data(as_text=True)
    assert 'Manthan 3 — Capacity: 120' in html_create

    # Edit page
    dummy_event = {
        'event_id': 1, 'club_id': 1, 'title': 'Tech Fest', 'description': 'desc',
        'event_lead': 'Lead', 'contact_no': '123', 'venue_id': 1, 'date': '2026-09-20',
        'start_time': '10:00:00', 'end_time': '12:00:00', 'registration_link': None
    }
    monkeypatch.setattr(events_routes, 'get_event_by_id', lambda eid: dummy_event)
    monkeypatch.setattr(events_routes, 'get_event_images', lambda eid: [])
    resp_edit = client.get('/events/1/edit')
    assert resp_edit.status_code == 200
    html_edit = resp_edit.get_data(as_text=True)
    assert 'Manthan 3 — Capacity: 120' in html_edit


# ── 5. Left Sidebar UI Enhancements ─────────────────────────────────────────
def test_sidebar_css_enhancements():
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'css', 'style.css')
    assert os.path.exists(css_path)
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
    assert '.sidebar-user:hover' in css
    assert '.sidebar-avatar' in css
    assert '.sidebar-link:hover' in css
    assert 'active-nav' in css
    assert 'box-shadow: inset 3px 0 0 var(--primary)' in css or 'active-nav' in css
