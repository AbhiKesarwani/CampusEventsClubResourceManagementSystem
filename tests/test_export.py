"""Admin data export: CSV / Excel / PDF generation for every dataset."""
from tests.conftest import login_as


def test_export_index_requires_admin(client):
    login_as(client, role='student')
    resp = client.get('/export/', follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == '/'  # bounced away from admin-only page


def test_export_index_renders_for_admin(client):
    login_as(client, role='admin')
    resp = client.get('/export/')
    assert resp.status_code == 200


DATASETS = ['students', 'attendance', 'events', 'certificates', 'club-members']
FORMATS_AND_MIME = {
    'csv': 'text/csv',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pdf': 'application/pdf',
}


def test_export_every_dataset_every_format(client):
    login_as(client, role='admin')
    for dataset in DATASETS:
        for fmt, mime in FORMATS_AND_MIME.items():
            resp = client.get(f'/export/{dataset}/{fmt}')
            assert resp.status_code == 200, f"{dataset}/{fmt} failed"
            assert resp.mimetype == mime
            assert len(resp.data) > 0


def test_export_unknown_dataset_404s(client):
    login_as(client, role='admin')
    resp = client.get('/export/not-a-real-dataset/csv')
    assert resp.status_code == 404


def test_export_unknown_format_404s(client):
    login_as(client, role='admin')
    resp = client.get('/export/students/txt')
    assert resp.status_code == 404
