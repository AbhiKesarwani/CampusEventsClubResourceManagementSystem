"""Calendar view: month grid, agenda view, and day-detail API."""
from tests.conftest import login_as


def test_calendar_month_view_renders(client):
    login_as(client, role='student')
    resp = client.get('/calendar/')
    assert resp.status_code == 200


def test_calendar_agenda_view_renders(client):
    login_as(client, role='student')
    resp = client.get('/calendar/?view=agenda')
    assert resp.status_code == 200


def test_calendar_navigates_months(client):
    login_as(client, role='student')
    resp = client.get('/calendar/?year=2026&month=3')
    assert resp.status_code == 200


def test_calendar_clamps_invalid_month(client):
    login_as(client, role='student')
    resp = client.get('/calendar/?year=2026&month=99')
    assert resp.status_code == 200  # clamped to December, never 500s


def test_calendar_day_detail_api(client):
    login_as(client, role='student')
    resp = client.get('/calendar/api/day?date=2026-08-15')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['date'] == '2026-08-15'
    assert data['events'] == []


def test_calendar_day_detail_invalid_date(client):
    login_as(client, role='student')
    resp = client.get('/calendar/api/day?date=not-a-date')
    assert resp.status_code == 400


def test_calendar_requires_login(client):
    resp = client.get('/calendar/', follow_redirects=False)
    assert resp.status_code == 302
