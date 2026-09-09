"""Global Ctrl+K search: RBAC-scoped quick search across every category."""
from tests.conftest import login_as


def test_quick_search_requires_login(client):
    resp = client.get('/search/api/quick?q=event')
    assert resp.status_code == 302  # login_required redirect


def test_quick_search_short_query_returns_empty(client):
    login_as(client, role='student')
    resp = client.get('/search/api/quick?q=a')
    assert resp.status_code == 200
    assert resp.get_json() == {'items': []}


def test_quick_search_returns_items_shape(client):
    login_as(client, role='student')
    resp = client.get('/search/api/quick?q=event')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'items' in data
    assert isinstance(data['items'], list)


def test_full_search_results_page_renders(client):
    login_as(client, role='student')
    resp = client.get('/search/?q=workshop')
    assert resp.status_code == 200


def test_full_search_results_page_renders_without_query(client):
    login_as(client, role='student')
    resp = client.get('/search/')
    assert resp.status_code == 200
