from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.models.category import Category
from app.models.enums import Variability, Frequency
from app.services import budget_service
from app.forms.budget_forms import BudgetForm

bp = Blueprint("budgets", __name__)


@bp.route("/")
@login_required
def list_budgets():
    show_inactive = request.args.get("show_inactive", "0") == "1"
    items = budget_service.get_budget_items_for_user(
        current_user.id, active_only=not show_inactive
    )
    return render_template(
        "budgets/list.html", items=items, show_inactive=show_inactive
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_budget():
    form = BudgetForm()
    _populate_category_choices(form)

    if form.validate_on_submit():
        budget_service.create_budget_item(
            payee=form.payee.data,
            variability=Variability(form.variability.data),
            frequency=Frequency(form.frequency.data),
            date_scheduled=form.date_scheduled.data,
            budgeted_amount=Decimal(str(form.budgeted_amount.data)),
            user_id=current_user.id,
            category_id=form.category_id.data,
            subcategory_id=form.subcategory_id.data or None,
            notes=form.notes.data or None,
        )
        flash("Budget item created.", "success")
        return redirect(url_for("budgets.list_budgets"))

    return render_template("budgets/form.html", form=form, title="Create Budget Item")


@bp.route("/<int:budget_id>/edit", methods=["GET", "POST"])
@login_required
def edit_budget(budget_id):
    item = budget_service.get_budget_item_for_user(budget_id, current_user.id)
    if not item:
        flash("Budget item not found.", "danger")
        return redirect(url_for("budgets.list_budgets"))

    form = BudgetForm(obj=item)
    _populate_category_choices(form)

    if form.validate_on_submit():
        budget_service.update_budget_item(
            budget_id,
            payee=form.payee.data,
            variability=form.variability.data,
            frequency=form.frequency.data,
            date_scheduled=form.date_scheduled.data,
            budgeted_amount=Decimal(str(form.budgeted_amount.data)),
            category_id=form.category_id.data,
            subcategory_id=form.subcategory_id.data or None,
            notes=form.notes.data or None,
            is_active=form.is_active.data,
        )
        flash("Budget item updated.", "success")
        return redirect(url_for("budgets.list_budgets"))

    return render_template("budgets/form.html", form=form, title="Edit Budget Item")


@bp.route("/api/subcategories/<int:category_id>")
@login_required
def subcategories_for_category(category_id):
    """JSON endpoint for dynamic subcategory dropdown."""
    subs = Category.query.filter_by(parent_id=category_id).order_by(Category.name).all()
    return jsonify([{"id": s.id, "name": s.name} for s in subs])


def _populate_category_choices(form):
    top_level = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    form.category_id.choices = [(c.id, c.name) for c in top_level]
    # Populate subcategories — all subcategories initially, JS will filter
    all_subs = (
        Category.query.filter(Category.parent_id.is_not(None))
        .order_by(Category.name)
        .all()
    )
    form.subcategory_id.choices = [("", "— None —")] + [
        (s.id, s.name) for s in all_subs
    ]
