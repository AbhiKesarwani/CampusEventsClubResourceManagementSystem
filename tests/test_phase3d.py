"""Tests for Phase 3D refinements:
1. Club card small image icon removed
2. Horizontal event timeline
3. Certificate full canvas utilization without signatures
4. Forgot password and reset password flow
5. Profile photo in avatar icon with initial fallback
6. Profile visibility removed from frontend
7. Session information structure and alignment
"""
import os
import tempfile
import pytest
from tests.conftest import login_as
from routes.auth import generate_reset_token, verify_reset_token


# ── 1. Club Cards: No small image/gallery icon ──────────────────────────────
def test_club_card_has_no_small_image_icon(client, monkeypatch):
    import routes.clubs as clubs_routes
    dummy_club = {
        'club_id': 1, 'club_name': 'Robotics Club', 'category': 'Technical',
        'lead_name': 'Lead', 'contact_no': '1234567890', 'email': 'robotics@college.edu',
        'description': 'Building robots', 'cover_image': None, 'photo_count': 3
    }
    monkeypatch.setattr(clubs_routes, 'get_all_clubs', lambda *a, **k: [dummy_club])
    login_as(client, role='student')
    resp = client.get('/clubs/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # The View button should exist
    assert 'View' in html
    # But the small extra gallery button on the card footer must NOT exist
    assert 'title="View Photos & Gallery"' not in html
    assert 'data-lucide="image"' not in html.split('class="club-card-actions"')[1]


# ── 2. Event Timeline: Horizontal Steps ─────────────────────────────────────
def test_event_horizontal_timeline_renders(client, monkeypatch):
    import routes.events as events_routes
    from datetime import date
    dummy_event = {
        'event_id': 1, 'title': 'AI Hackathon', 'description': 'Build AI models',
        'date': date.today(), 'start_time': '10:00:00', 'end_time': '17:00:00',
        'club_name': 'AI Club', 'venue_name': 'Auditorium', 'capacity': 100,
        'approved_status': 'Approved', 'registration_link': None, 'club_id': 1,
        'created_by': 1, 'event_lead': 'Lead', 'contact_no': '123',
    }
    monkeypatch.setattr(events_routes, 'get_event_by_id', lambda eid: dummy_event)
    monkeypatch.setattr(events_routes, 'has_attended', lambda eid, uid: True)
    monkeypatch.setattr(events_routes, 'certificate_exists', lambda eid, uid: False)

    login_as(client, role='student', user_id=1)
    resp = client.get('/events/1')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'event-timeline-horizontal' in html
    assert 'event-timeline-step' in html
    assert 'Registration' in html
    assert 'Certificate Generated' in html


# ── 3. Certificate: Full Canvas Utilization & No Signatures ─────────────────
def test_certificate_generation_no_signatures():
    from helpers.certificate_helpers import generate_certificate
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, 'test_cert.png')
        res = generate_certificate(
            student_name='Abhinav Sharma',
            event_title='Annual Tech Symposium 2026',
            save_path=out_path,
            club_name='Coding Club',
            event_date='September 14, 2026',
            cert_id='TEST9999'
        )
        assert os.path.exists(res)
        with Image.open(res) as img:
            assert img.size == (1400, 900)


# ── 4. Forgot Password & Reset Password Flow ────────────────────────────────
def test_token_serializer_flow(app):
    with app.app_context():
        email = 'student@college.edu'
        token = generate_reset_token(email)
        assert token is not None
        verified = verify_reset_token(token, max_age=60)
        assert verified == email

        # Invalid token
        assert verify_reset_token('invalid-token-xyz') is None


def test_forgot_password_page_renders(client):
    resp = client.get('/forgot-password')
    assert resp.status_code == 200
    assert 'Forgot password?' in resp.get_data(as_text=True)
    assert 'Registered Email address' in resp.get_data(as_text=True)


def test_forgot_password_submission_existing_and_nonexisting(client, monkeypatch):
    import routes.auth as auth_routes
    dummy_user = {'user_id': 1, 'email': 'student@college.edu', 'name': 'Student'}
    monkeypatch.setattr(auth_routes, 'get_user_by_email',
                        lambda email: dummy_user if email == 'student@college.edu' else None)

    # Existing user
    resp = client.post('/forgot-password', data={'email': 'student@college.edu'}, follow_redirects=True)
    assert resp.status_code == 200
    assert 'Password reset link generated' in resp.get_data(as_text=True)

    # Non-existing user (safe generic message)
    resp = client.post('/forgot-password', data={'email': 'unknown@college.edu'}, follow_redirects=True)
    assert resp.status_code == 200
    assert 'If an account exists with that email' in resp.get_data(as_text=True)


def test_reset_password_flow(client, monkeypatch, app):
    import routes.auth as auth_routes
    dummy_user = {'user_id': 1, 'email': 'student@college.edu', 'name': 'Student', 'password_hash': 'old'}
    monkeypatch.setattr(auth_routes, 'get_user_by_email', lambda email: dummy_user)

    updated = {}
    monkeypatch.setattr(auth_routes, 'update_password', lambda uid, pw: updated.update(pw=pw))

    with app.app_context():
        token = generate_reset_token('student@college.edu')

    # GET reset form
    resp = client.get(f'/reset-password/{token}')
    assert resp.status_code == 200
    assert 'Set new password' in resp.get_data(as_text=True)

    # POST password mismatch
    resp = client.post(f'/reset-password/{token}', data={
        'password': 'newpassword123', 'confirm_password': 'mismatchpassword'
    })
    assert resp.status_code == 200
    assert 'Passwords do not match' in resp.get_data(as_text=True)

    # POST success
    resp = client.post(f'/reset-password/{token}', data={
        'password': 'newpassword123', 'confirm_password': 'newpassword123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert updated.get('pw') == 'newpassword123'
    assert 'successfully reset' in resp.get_data(as_text=True)


def test_login_page_has_forgot_password_link(client):
    resp = client.get('/login')
    assert resp.status_code == 200
    assert 'Forgot password?' in resp.get_data(as_text=True)
    assert '/forgot-password' in resp.get_data(as_text=True)


# ── 5. Profile Photo in Profile Avatar Icon ─────────────────────────────────
def test_avatar_photo_rendered_when_present(client, monkeypatch):
    import routes.profile as profile_routes
    user_with_avatar = {
        'user_id': 1, 'name': 'Photo User', 'email': 'photo@example.com',
        'role': 'student', 'club_id': None, 'avatar_path': 'uploads/test_avatar.jpg',
        'phone': None
    }
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: user_with_avatar)

    login_as(client, role='student', user_id=1)
    with client.session_transaction() as sess:
        sess['avatar_path'] = 'uploads/test_avatar.jpg'

    resp = client.get('/profile/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'uploads/test_avatar.jpg' in html


def test_avatar_initial_rendered_when_no_photo(client, monkeypatch):
    import routes.profile as profile_routes
    user_no_avatar = {
        'user_id': 1, 'name': 'Zack NoPhoto', 'email': 'zack@example.com',
        'role': 'student', 'club_id': None, 'avatar_path': None, 'phone': None
    }
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: user_no_avatar)

    login_as(client, role='student', user_id=1, name='Zack NoPhoto')
    with client.session_transaction() as sess:
        sess['avatar_path'] = None

    resp = client.get('/profile/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'sidebar-avatar">Z<' in html or 'user-avatar" title="Zack NoPhoto">Z<' in html


# ── 6. Profile Visibility Removed from Frontend ──────────────────────────────
def test_settings_has_no_profile_visibility_option(client, monkeypatch):
    import routes.settings as settings_routes
    dummy_user = {'user_id': 1, 'name': 'Student', 'email': 's@example.com', 'role': 'student', 'club_id': None}
    monkeypatch.setattr(settings_routes, 'get_user_by_id', lambda uid: dummy_user)

    login_as(client, role='student', user_id=1)
    resp = client.get('/settings/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Profile visibility' not in html
    assert 'name="profile_visibility"' not in html


# ── 7. Session Information Structure & Alignment ────────────────────────────
def test_session_information_structure(client, monkeypatch):
    import routes.settings as settings_routes
    dummy_user = {'user_id': 1, 'name': 'Abhinav', 'email': 'abhinav@example.com', 'role': 'student', 'club_id': 3}
    monkeypatch.setattr(settings_routes, 'get_user_by_id', lambda uid: dummy_user)

    login_as(client, role='club_admin', user_id=1, email='abhinav@example.com', club_id=3)
    resp = client.get('/settings/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Session Information' in html
    assert 'Email' in html
    assert 'abhinav@example.com' in html
    assert 'Role' in html
    assert 'Club ID' in html
    assert '#3' in html
    assert 'Session Cookie' in html
    assert 'HttpOnly, SameSite=Lax' in html
