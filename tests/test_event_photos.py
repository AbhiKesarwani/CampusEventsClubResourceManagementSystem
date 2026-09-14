import os
import io
import pytest
from tests.conftest import login_as
import routes.events


@pytest.fixture
def mock_event():
    return {
        'event_id': 1,
        'club_id': 2,
        'title': 'Hackathon Tech Fest',
        'description': 'Annual engineering hackathon',
        'event_lead': 'Lead Coordinator',
        'contact_no': '9876543210',
        'venue_id': 1,
        'venue_name': 'Main Auditorium',
        'date': None,
        'start_time': '10:00:00',
        'end_time': '16:00:00',
        'poster': None,
        'registration_link': 'https://forms.google.com/test',
        'approved_status': 'Approved',
        'club_name': 'Coding Club',
        'club_description': 'Tech enthusiasts club'
    }


def test_coordinator_can_upload_event_photo(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    monkeypatch.setattr('routes.events.save_upload', lambda f, prefix: 'uploads/event_1_test.jpg')
    called = []
    monkeypatch.setattr('routes.events.add_event_image', lambda eid, p, uploaded_by=None, original_filename=None: called.append((eid, p)))
    monkeypatch.setattr('routes.events.log_action', lambda *args, **kwargs: None)

    login_as(client, role='club_admin', club_id=2, user_id=10)

    data = {
        'photos': (io.BytesIO(b'fake-image-bytes'), 'test_photo.jpg')
    }
    resp = client.post('/events/1/photos/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
    assert resp.status_code == 302
    assert '/events/1' in resp.headers['Location']
    assert len(called) == 1


def test_unauthorized_coordinator_cannot_upload_event_photo(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    called = []
    monkeypatch.setattr('routes.events.add_event_image', lambda *args, **kwargs: called.append(args))

    login_as(client, role='club_admin', club_id=999, user_id=11)

    data = {
        'photos': (io.BytesIO(b'fake-image-bytes'), 'test_photo.jpg')
    }
    resp = client.post('/events/1/photos/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
    assert resp.status_code == 302
    assert len(called) == 0


def test_student_cannot_upload_event_photo(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    called = []
    monkeypatch.setattr('routes.events.add_event_image', lambda *args, **kwargs: called.append(args))

    login_as(client, role='student', user_id=12)

    data = {
        'photos': (io.BytesIO(b'fake-image-bytes'), 'test_photo.jpg')
    }
    resp = client.post('/events/1/photos/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
    assert resp.status_code == 302
    assert len(called) == 0


def test_admin_can_upload_event_photo(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    monkeypatch.setattr('routes.events.save_upload', lambda f, prefix: 'uploads/event_1_admin.jpg')
    called = []
    monkeypatch.setattr('routes.events.add_event_image', lambda eid, p, uploaded_by=None, original_filename=None: called.append((eid, p)))
    monkeypatch.setattr('routes.events.log_action', lambda *args, **kwargs: None)

    login_as(client, role='admin', user_id=1)

    data = {
        'photos': (io.BytesIO(b'fake-image-bytes'), 'admin_photo.png')
    }
    resp = client.post('/events/1/photos/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
    assert resp.status_code == 302
    assert len(called) == 1


def test_upload_invalid_file_rejected(client, monkeypatch, mock_event):
    def fake_save(f, prefix):
        raise ValueError("File type not allowed.")

    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    monkeypatch.setattr('routes.events.save_upload', fake_save)
    called = []
    monkeypatch.setattr('routes.events.add_event_image', lambda *args, **kwargs: called.append(args))

    login_as(client, role='admin', user_id=1)

    data = {
        'photos': (io.BytesIO(b'executable payload'), 'bad.exe')
    }
    resp = client.post('/events/1/photos/upload', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200
    assert len(called) == 0


def test_download_gallery_zip_with_photos(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    monkeypatch.setattr('routes.events.get_event_images', lambda eid: [
        {'img_id': 1, 'img_path': 'uploads/dummy.jpg', 'event_id': 1}
    ])
    monkeypatch.setattr('routes.events.build_gallery_zip', lambda imgs: io.BytesIO(b'PK_ZIP_BYTES'))

    login_as(client, role='student', user_id=5)

    resp = client.get('/events/1/gallery/zip')
    assert resp.status_code == 200
    assert 'zip' in resp.content_type
    assert 'attachment' in resp.headers.get('Content-Disposition', '')


def test_download_gallery_zip_empty_warns(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    monkeypatch.setattr('routes.events.get_event_images', lambda eid: [])

    login_as(client, role='student', user_id=5)

    resp = client.get('/events/1/gallery/zip', follow_redirects=False)
    assert resp.status_code == 302
    assert '/events/1' in resp.headers['Location']


def test_delete_photo_rbac_enforcement(client, monkeypatch, mock_event):
    monkeypatch.setattr('routes.events.get_event_by_id', lambda eid: mock_event)
    called = []
    monkeypatch.setattr('routes.events.delete_event_image', lambda iid, eid: called.append((iid, eid)) or 'uploads/deleted.jpg')
    monkeypatch.setattr('routes.events.delete_upload', lambda p: None)
    monkeypatch.setattr('routes.events.log_action', lambda *args, **kwargs: None)

    # Student cannot delete
    login_as(client, role='student', user_id=12)
    resp = client.post('/events/1/delete_image/1', follow_redirects=False)
    assert len(called) == 0

    # Admin can delete
    login_as(client, role='admin', user_id=1)
    resp = client.post('/events/1/delete_image/1', follow_redirects=False)
    assert len(called) == 1


def test_path_traversal_prevented():
    from helpers.upload_helpers import get_image_path
    from werkzeug.exceptions import HTTPException

    traversal_images = [{'img_id': 1, 'img_path': '../../../../etc/passwd'}]
    with pytest.raises((HTTPException, Exception)):
        get_image_path(traversal_images, 1)


def test_login_and_register_render_illustration(client):
    resp_login = client.get('/login')
    assert resp_login.status_code == 200
    assert 'campus_students_illustration.svg' in resp_login.get_data(as_text=True)

    resp_reg = client.get('/register')
    assert resp_reg.status_code == 200
    assert 'campus_students_illustration.svg' in resp_reg.get_data(as_text=True)
