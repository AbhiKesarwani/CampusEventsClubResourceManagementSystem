"""Unit tests for helpers.pagination.paginate() — pure logic, no DB/Flask needed."""
from helpers.pagination import paginate


def test_paginate_basic():
    page, total_pages, offset = paginate(total=100, page=1, per_page=10)
    assert page == 1
    assert total_pages == 10
    assert offset == 0


def test_paginate_middle_page():
    page, total_pages, offset = paginate(total=95, page=3, per_page=10)
    assert page == 3
    assert total_pages == 10  # ceil(95/10)
    assert offset == 20


def test_paginate_clamps_page_too_high():
    page, total_pages, offset = paginate(total=25, page=99, per_page=10)
    assert page == total_pages == 3
    assert offset == 20


def test_paginate_clamps_page_too_low():
    page, total_pages, offset = paginate(total=25, page=0, per_page=10)
    assert page == 1
    assert offset == 0


def test_paginate_empty_dataset_never_divides_by_zero():
    page, total_pages, offset = paginate(total=0, page=1, per_page=10)
    assert total_pages == 1
    assert page == 1
    assert offset == 0
