# helpers/pagination.py
"""Shared pagination arithmetic used by every paginated list route.

Centralizes the page-clamping + offset math that was previously copy-pasted
across routes/events.py, routes/clubs.py, routes/certificates.py,
routes/recommendations.py, and routes/notifications.py.
"""


def paginate(total: int, page: int, per_page: int) -> tuple[int, int, int]:
    """
    Compute pagination values for a result set.

    Args:
        total:    total number of items across all pages.
        page:     the requested page number (1-indexed, may be out of range).
        per_page: number of items per page.

    Returns:
        (page, total_pages, offset) — page and offset are clamped to valid
        bounds so callers never need to guard against out-of-range values.
    """
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page
    return page, total_pages, offset
