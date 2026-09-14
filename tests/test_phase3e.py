"""Tests for Phase 3E targeted fixes:
1. Campus students illustration SVG is valid XML and loads on Login & Register
2. Certificate green border on all 4 sides (top, bottom, left, right)
3. Coordinator announcements can target 'All Students'
4. Admin Broadcasts tab/panel removed from Campus Connect
5. Chat bubble CSS formatting (word-break, overflow-wrap, etc.)
"""
import os
import xml.etree.ElementTree as ET
import tempfile
import pytest
from PIL import Image
from tests.conftest import login_as
import services.connect_service as connect_service


# ── 1. Fix Campus Students Image Loading ────────────────────────────────────
def test_campus_students_illustration_valid_xml():
    svg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'campus_students_illustration.svg')
    assert os.path.exists(svg_path)
    # Parse as XML — must succeed without any syntax/parse errors
    tree = ET.parse(svg_path)
    root = tree.getroot()
    assert 'svg' in root.tag.lower()


def test_login_and_register_serve_illustration(client):
    # Test static file response
    resp_img = client.get('/static/images/campus_students_illustration.svg')
    assert resp_img.status_code == 200
    assert 'image/svg+xml' in resp_img.content_type or '<svg' in resp_img.get_data(as_text=True)

    # Test login page references it
    resp_login = client.get('/login')
    assert resp_login.status_code == 200
    assert 'campus_students_illustration.svg' in resp_login.get_data(as_text=True)

    # Test register page references it
    resp_reg = client.get('/register')
    assert resp_reg.status_code == 200
    assert 'campus_students_illustration.svg' in resp_reg.get_data(as_text=True)


# ── 2. Certificate Green Border — All 4 Sides ───────────────────────────────
def test_certificate_green_border_all_sides():
    from helpers.certificate_helpers import generate_certificate

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, 'cert_border_test.png')
        generate_certificate(
            student_name='Border Tester',
            event_title='Robotics Championship',
            save_path=out_path,
            club_name='Robotics Society',
            event_date='September 14, 2026',
            cert_id='BORD1234'
        )
        assert os.path.exists(out_path)
        with Image.open(out_path) as img:
            rgb = img.convert('RGB')
            w, h = rgb.size
            assert (w, h) == (1400, 900)
            emerald = (16, 185, 129)

            # Check top border (center x, y=2)
            assert rgb.getpixel((w // 2, 2)) == emerald
            # Check bottom border (center x, y=h-3)
            assert rgb.getpixel((w // 2, h - 3)) == emerald
            # Check left border (x=2, center y)
            assert rgb.getpixel((2, h // 2)) == emerald
            # Check right border (x=w-3, center y)
            assert rgb.getpixel((w - 3, h // 2)) == emerald


# ── 3. Coordinator Announcements to All Students ────────────────────────────
def test_coordinator_can_create_announcement_for_all_students(monkeypatch, fake_db):
    monkeypatch.setattr(connect_service, '_fanout_announcement_notifications', lambda *a, **k: None)
    ann_id = connect_service.create_announcement(
        author_id=1, author_role='club_admin', author_club_id=3,
        target_type='students', target_id=None,
        title='Open Auditions For All Students',
        body='Auditions start this Friday in Room 101.'
    )
    assert ann_id == 1


def test_coordinator_sees_all_students_option_in_modal(client, monkeypatch):
    dummy_user = {'user_id': 1, 'name': 'Coordinator', 'email': 'coord@college.edu', 'role': 'club_admin', 'club_id': 2}
    import routes.connect as connect_routes
    monkeypatch.setattr(connect_routes, 'get_user_by_id', lambda uid: dummy_user)

    login_as(client, role='club_admin', user_id=1, club_id=2)
    resp = client.get('/connect/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '<option value="students">All Students</option>' in html
    assert '<option value="club">My Club Members</option>' in html


# ── 4. Remove Admin Broadcasts from Campus Connect ──────────────────────────
def test_admin_broadcasts_tab_removed_from_campus_connect(client, monkeypatch):
    dummy_admin = {'user_id': 1, 'name': 'Admin User', 'email': 'admin@college.edu', 'role': 'admin', 'club_id': None}
    import routes.connect as connect_routes
    monkeypatch.setattr(connect_routes, 'get_user_by_id', lambda uid: dummy_admin)

    login_as(client, role='admin', user_id=1)
    resp = client.get('/connect/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Admin Broadcasts tab button and panel should NOT exist
    assert 'Admin Broadcasts' not in html
    assert 'data-tab="broadcast"' not in html


# ── 5. Chat Message Bubble Styling (No single-letter wrapping) ──────────────
def test_chat_bubble_css_rules(client, monkeypatch):
    dummy_user = {'user_id': 1, 'name': 'Tester', 'email': 't@example.com', 'role': 'student', 'club_id': None}
    import routes.connect as connect_routes
    monkeypatch.setattr(connect_routes, 'get_user_by_id', lambda uid: dummy_user)
    login_as(client, role='student', user_id=1)
    resp = client.get('/connect/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert '.cc-bubble' in html
    assert 'word-break: normal' in html
    assert 'overflow-wrap: anywhere' in html
