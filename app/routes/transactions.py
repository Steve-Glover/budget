from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.models.category import Category
from app.models.account import Account
from app.models.enums import TransactionType
from app.services import transaction_service, analysis_service
from app.forms.transaction_forms import TransactionForm, CSVImportForm

bp = Blueprint("transactions", __name__)

PER_PAGE = 25


@bp.route("/")
@login_required
def list_transactions():
    page = request.args.get("page", 1, type=int)
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    category_id = request.args.get("category_id", type=int)
    account_id = request.args.get("account_id", type=int)

    user_id = current_user.id
    kwargs = {"user_id": user_id}
    if start:
        kwargs["start_date"] = date.fromisoformat(start)
    if end:
        kwargs["end_date"] = date.fromisoformat(end)
    if category_id:
        kwargs["category_id"] = category_id
    if account_id:
        kwargs["account_id"] = account_id

    # Simple offset-based pagination
    all_txns = transaction_service.get_transactions_for_user(**kwargs)
    total = len(all_txns)
    start_idx = (page - 1) * PER_PAGE
    txns = all_txns[start_idx : start_idx + PER_PAGE]
    total_pages = (total + PER_PAGE - 1) // PER_PAGE

    categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    accounts = (
        Account.query.filter_by(owner_id=user_id, is_active=True)
        .order_by(Account.name)
        .all()
    )

    return render_template(
        "transactions/list.html",
        transactions=txns,
        page=page,
        total_pages=total_pages,
        categories=categories,
        accounts=accounts,
        filters=request.args,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_transaction():
    form = TransactionForm()
    _populate_form_choices(form)

    if form.validate_on_submit():
        user_id = current_user.id
        txn = transaction_service.create_transaction(
            transaction_date=form.transaction_date.data,
            payee=form.payee.data,
            amount=Decimal(str(form.amount.data)),
            transaction_type=TransactionType(form.transaction_type.data),
            user_id=user_id,
            post_date=form.post_date.data or None,
            description=form.description.data or None,
            notes=form.notes.data or None,
            debit_account_id=form.debit_account_id.data or None,
            credit_account_id=form.credit_account_id.data or None,
            category_id=form.category_id.data or None,
            subcategory_id=form.subcategory_id.data or None,
        )
        analysis_service.recompute_periods_in_range(
            user_id, txn.transaction_date, txn.transaction_date
        )
        flash("Transaction created.", "success")
        return redirect(url_for("transactions.list_transactions"))

    return render_template(
        "transactions/form.html", form=form, title="Create Transaction"
    )


@bp.route("/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    user_id = current_user.id
    txn = transaction_service.get_transaction_for_user(transaction_id, user_id)
    if not txn:
        flash("Transaction not found.", "danger")
        return redirect(url_for("transactions.list_transactions"))

    form = TransactionForm(obj=txn)
    _populate_form_choices(form)

    if form.validate_on_submit():
        old_date = txn.transaction_date
        new_date = form.transaction_date.data
        transaction_service.update_transaction(
            transaction_id,
            transaction_date=new_date,
            payee=form.payee.data,
            amount=Decimal(str(form.amount.data)),
            transaction_type=form.transaction_type.data,
            post_date=form.post_date.data or None,
            description=form.description.data or None,
            notes=form.notes.data or None,
            debit_account_id=form.debit_account_id.data or None,
            credit_account_id=form.credit_account_id.data or None,
            category_id=form.category_id.data or None,
            subcategory_id=form.subcategory_id.data or None,
        )
        analysis_service.recompute_periods_in_range(
            user_id, min(old_date, new_date), max(old_date, new_date)
        )
        flash("Transaction updated.", "success")
        return redirect(url_for("transactions.list_transactions"))

    return render_template(
        "transactions/form.html", form=form, title="Edit Transaction"
    )


@bp.route("/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    user_id = current_user.id
    txn = transaction_service.get_transaction_for_user(transaction_id, user_id)
    if txn:
        txn_date = txn.transaction_date
        transaction_service.delete_transaction(transaction_id)
        analysis_service.recompute_periods_in_range(user_id, txn_date, txn_date)
        flash("Transaction deleted.", "success")
    else:
        flash("Transaction not found.", "danger")
    return redirect(url_for("transactions.list_transactions"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_csv():
    user_id = current_user.id
    form = CSVImportForm()
    accounts = (
        Account.query.filter_by(owner_id=user_id, is_active=True)
        .order_by(Account.name)
        .all()
    )
    form.account_id.choices = [("", "— None —")] + [(a.id, a.name) for a in accounts]

    if form.validate_on_submit():
        csv_file = form.csv_file.data
        csv_text = csv_file.read().decode("utf-8")
        account_id = form.account_id.data or None
        result = transaction_service.import_csv(
            csv_text, user_id, account_id=account_id
        )
        if result["min_date"] and result["max_date"]:
            analysis_service.recompute_periods_in_range(
                user_id, result["min_date"], result["max_date"]
            )
        flash(f"Imported {result['imported']} transactions.", "success")
        if result["errors"]:
            for err in result["errors"][:5]:
                flash(f"Row {err['row']}: {err['error']}", "warning")
        return redirect(url_for("transactions.list_transactions"))

    return render_template("transactions/import.html", form=form)


def _populate_form_choices(form):
    user_id = current_user.id
    categories = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    form.category_id.choices = [("", "— None —")] + [(c.id, c.name) for c in categories]

    all_subs = (
        Category.query.filter(Category.parent_id.is_not(None))
        .order_by(Category.name)
        .all()
    )
    form.subcategory_id.choices = [("", "— None —")] + [
        (s.id, s.name) for s in all_subs
    ]

    accounts = (
        Account.query.filter_by(owner_id=user_id, is_active=True)
        .order_by(Account.name)
        .all()
    )
    acct_choices = [("", "— None —")] + [(a.id, a.name) for a in accounts]
    form.debit_account_id.choices = acct_choices
    form.credit_account_id.choices = acct_choices
