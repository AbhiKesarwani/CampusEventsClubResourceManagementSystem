# routes/recommendations.py
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from helpers.auth_helpers import login_required
from services.recommendation_service import get_recommendations
from services.user_service import get_user_by_id
from helpers.pagination import paginate

bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')

PER_PAGE = 12


@bp.route('/')
@login_required
def index():
    """Weighted recommendation page — students only."""
    role = session.get('role')
    if role != 'student':
        flash("Recommendations are only available for students.", "info")
        return redirect(url_for('dashboard.index'))

    user_id    = session['user_id']
    user       = get_user_by_id(user_id)
    page       = request.args.get('page', 1, type=int)
    all_events = get_recommendations(user_id, limit=120)  # fetch more, paginate in Python
    total      = len(all_events)
    page, total_pages, offset = paginate(total, page, PER_PAGE)
    events     = all_events[offset: offset + PER_PAGE]

    return render_template('recommendations.html',
                           events=events,
                           user=user,
                           page=page, total_pages=total_pages, total=total,
                           active='recommendations')
