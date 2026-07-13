# routes/recommendations.py
from flask import Blueprint, render_template, session, redirect, url_for, flash
from helpers.auth_helpers import login_required
from services.recommendation_service import get_recommendations, log_view
from services.user_service import get_user_by_id

bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')


@bp.route('/')
@login_required
def index():
    """Weighted recommendation page — students only."""
    role = session.get('role')
    if role != 'student':
        flash("Recommendations are only available for students.", "info")
        return redirect(url_for('dashboard.index'))

    user_id = session['user_id']
    user    = get_user_by_id(user_id)
    events  = get_recommendations(user_id, limit=12)

    return render_template('recommendations.html',
                           events=events,
                           user=user,
                           active='recommendations')
