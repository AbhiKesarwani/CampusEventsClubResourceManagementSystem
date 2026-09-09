"""Recommendations: student-only access and rendering."""
from tests.conftest import login_as


def test_recommendations_page_renders_for_student(client):
    login_as(client, role='student')
    resp = client.get('/recommendations/')
    assert resp.status_code == 200


def test_recommendations_redirects_non_students(client):
    login_as(client, role='admin')
    resp = client.get('/recommendations/', follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == '/'


def test_recommendations_requires_login(client):
    resp = client.get('/recommendations/', follow_redirects=False)
    assert resp.status_code == 302
