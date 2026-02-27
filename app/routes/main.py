from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, request

from app.services import analysis_service, transaction_service

bp = Blueprint("main", __name__)

DEFAULT_USER_ID = 1


@bp.route("/")
def dashboard():
    periods = analysis_service.get_periods_for_user(DEFAULT_USER_ID)
    today = date.today()

    # Determine active period: explicit override → auto-detect → most recent
    period_id = request.args.get("period_id", type=int)
    active_period = None

    if period_id:
        active_period = analysis_service.get_period(period_id)

    if not active_period:
        for p in periods:
            if p.start_date <= today <= p.end_date:
                active_period = p
                break

    if not active_period and periods:
        active_period = periods[0]

    category_rows = []
    recent_txns = []

    if active_period:
        category_rows = analysis_service.aggregate_by_category(
            active_period.id, DEFAULT_USER_ID
        )
        recent_txns = transaction_service.get_transactions_for_user(
            DEFAULT_USER_ID,
            start_date=active_period.start_date,
            end_date=active_period.end_date,
            limit=10,
        )

    total_budgeted = sum((r.budgeted_amount for r in category_rows), Decimal("0.00"))
    total_actual = sum((r.actual_amount for r in category_rows), Decimal("0.00"))
    total_variance = total_budgeted - total_actual

    return render_template(
        "dashboard.html",
        periods=periods,
        active_period=active_period,
        category_rows=category_rows,
        recent_txns=recent_txns,
        total_budgeted=total_budgeted,
        total_actual=total_actual,
        total_variance=total_variance,
    )
