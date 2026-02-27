from flask import Blueprint, render_template, redirect, url_for, flash, request

from app.extensions import db
from app.forms.analysis_forms import AnalysisPeriodForm
from app.models.category import Category
from app.services import analysis_service

bp = Blueprint("analysis", __name__)

DEFAULT_USER_ID = 1


@bp.route("/")
def list_periods():
    periods = analysis_service.get_periods_for_user(DEFAULT_USER_ID)
    return render_template("analysis/list.html", periods=periods)


@bp.route("/create", methods=["GET", "POST"])
def create_period():
    form = AnalysisPeriodForm()
    if form.validate_on_submit():
        analysis_service.create_period(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            user_id=DEFAULT_USER_ID,
        )
        flash("Analysis period created.", "success")
        return redirect(url_for("analysis.list_periods"))
    return render_template("analysis/form.html", form=form, title="Create Period")


@bp.route("/<int:period_id>/edit", methods=["GET", "POST"])
def edit_period(period_id):
    period = analysis_service.get_period(period_id)
    if not period:
        flash("Period not found.", "danger")
        return redirect(url_for("analysis.list_periods"))

    form = AnalysisPeriodForm(obj=period)
    if form.validate_on_submit():
        analysis_service.update_period(
            period_id,
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
        )
        flash("Period updated.", "success")
        return redirect(url_for("analysis.list_periods"))
    return render_template("analysis/form.html", form=form, title="Edit Period")


@bp.route("/<int:period_id>/delete", methods=["POST"])
def delete_period(period_id):
    if analysis_service.delete_period(period_id):
        flash("Period deleted.", "success")
    else:
        flash("Period not found.", "danger")
    return redirect(url_for("analysis.list_periods"))


@bp.route("/<int:period_id>/report")
def period_report(period_id):
    period = analysis_service.get_period(period_id)
    if not period:
        flash("Period not found.", "danger")
        return redirect(url_for("analysis.list_periods"))

    category_id = request.args.get("category_id", type=int)
    rows = analysis_service.aggregate_by_category(
        period_id, DEFAULT_USER_ID, category_id
    )

    drill_category = None
    if category_id:
        drill_category = db.session.get(Category, category_id)

    return render_template(
        "analysis/report.html",
        period=period,
        rows=rows,
        category_id=category_id,
        drill_category=drill_category,
    )


@bp.route("/<int:period_id>/recompute", methods=["POST"])
def recompute_period(period_id):
    period = analysis_service.get_period(period_id)
    if not period:
        flash("Period not found.", "danger")
        return redirect(url_for("analysis.list_periods"))
    analysis_service.recompute_analysis(period_id, DEFAULT_USER_ID)
    flash("Analysis recomputed.", "success")
    return redirect(url_for("analysis.period_report", period_id=period_id))
