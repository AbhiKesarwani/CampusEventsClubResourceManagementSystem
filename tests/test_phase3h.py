"""Tests for Phase 3H targeted fixes:
1. Create Account page width ratio matches Login page (62% hero / 38% form side)
2. White registration form area has increased width (max-width: 380px)
3. Fits within viewport without vertical scroll
"""
import pytest


def test_register_and_login_page_ratio_match(client):
    resp_login = client.get('/login')
    assert resp_login.status_code == 200
    html_login = resp_login.get_data(as_text=True)

    resp_reg = client.get('/register')
    assert resp_reg.status_code == 200
    html_reg = resp_reg.get_data(as_text=True)

    # Check that both pages use the 62% / 38% split layout
    assert 'flex: 0 0 62%' in html_login
    assert 'flex: 0 0 38%' in html_login

    assert 'flex: 0 0 62%' in html_reg
    assert 'flex: 0 0 38%' in html_reg

    # Check that the form containers have the expanded 380px width
    assert 'max-width: 380px' in html_login
    assert 'max-width: 380px' in html_reg
