"""
Phase 4 Test Suite — Responsive & Cross-Device UI Polish
Verifies responsive CSS rules, drawer sidebar, table wrappers, modal responsive sizing,
and viewport meta tags across all core templates.
"""
from tests.conftest import login_as


def test_style_css_responsive_rules(client):
    """Verify that static/css/style.css contains essential responsive rules and media queries."""
    resp = client.get('/static/css/style.css')
    assert resp.status_code == 200
    css = resp.data.decode('utf-8')

    # Media queries
    assert '@media (max-width: 1024px)' in css
    assert '@media (max-width: 768px)' in css
    assert '@media (max-width: 480px)' in css

    # Mobile Drawer sidebar rules
    assert '#sidebar.mobile-open' in css
    assert '#sidebar-overlay.active' in css
    assert '#main-content' in css

    # Table wrappers
    assert '.table-wrap' in css
    assert '.table-responsive' in css
    assert 'overflow-x: auto' in css

    # Modal responsive rules
    assert '.cc-modal' in css
    assert '.sdm-dialog' in css


def test_viewport_meta_tag_present_in_layout(client):
    """Verify layout.html contains the responsive viewport meta tag."""
    login_as(client, role='student')
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">' in html


def test_mobile_drawer_and_bottom_nav_elements_present(client):
    """Verify mobile hamburger, overlay, and bottom nav elements are present in layout."""
    login_as(client, role='student')
    resp = client.get('/')
    html = resp.data.decode('utf-8')

    assert 'id="mobile-menu-btn"' in html
    assert 'id="sidebar-overlay"' in html
    assert 'id="bottom-nav"' in html
    assert 'id="sidebar"' in html
    assert 'id="main-content"' in html


def test_login_and_register_viewport_and_media_queries(client):
    """Verify login and register templates have viewport meta tags and responsive CSS."""
    resp_login = client.get('/login')
    assert resp_login.status_code == 200
    html_login = resp_login.data.decode('utf-8')
    assert 'name="viewport"' in html_login
    assert '@media (max-width: 700px)' in html_login

    resp_reg = client.get('/register')
    assert resp_reg.status_code == 200
    html_reg = resp_reg.data.decode('utf-8')
    assert 'name="viewport"' in html_reg
    assert '@media (max-width: 860px)' in html_reg


def test_all_core_pages_render_with_responsive_containers(client, monkeypatch):
    """Verify core routes render with main-content container."""
    import routes.profile as profile_routes
    import routes.settings as settings_routes
    fake_user = {'user_id': 1, 'name': 'Test Student', 'email': 't@example.com',
                 'role': 'student', 'club_id': None, 'avatar_path': None, 'phone': None}
    monkeypatch.setattr(profile_routes, 'get_user_by_id', lambda uid: fake_user)
    monkeypatch.setattr(settings_routes, 'get_user_by_id', lambda uid: fake_user)

    login_as(client, role='student', user_id=1)

    routes = [
        '/',
        '/events/',
        '/clubs/',
        '/connect/',
        '/attendance/my',
        '/certificates/my',
        '/notifications/',
        '/calendar/',
        '/profile/',
        '/settings/'
    ]

    for route in routes:
        resp = client.get(route, follow_redirects=True)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"
        html = resp.data.decode('utf-8')
        assert 'id="main-content"' in html
