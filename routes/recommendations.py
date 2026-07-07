# routes/recommendations.py
from flask import Blueprint, render_template, session
from helpers.auth_helpers import login_required
from services.user_service import get_user_by_id
from services.recommendation_service import get_recommendations

bp = Blueprint('recommendations', __name__, url_prefix='/recommendations')


@bp.route('/')
@login_required
def index():
    events = get_recommendations(session['user_id'], limit=12)
    user   = get_user_by_id(session['user_id'])
    return render_template('recommendations.html',
                           events=events, user=user, active='recommendations')
