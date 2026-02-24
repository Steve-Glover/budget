from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request

from app.models.vendor import Vendor
from app.models.enums import AccountType
from app.services import account_service
from app.forms.account_forms import AccountForm

bp = Blueprint("accounts", __name__)

# Hardcoded user_id until auth is added in Phase 5
DEFAULT_USER_ID = 1


@bp.route("/")
def list_accounts():
    show_inactive = request.args.get("show_inactive", "0") == "1"
    accounts = account_service.get_accounts_for_user(
        DEFAULT_USER_ID, active_only=not show_inactive
    )
    return render_template(
        "accounts/list.html", accounts=accounts, show_inactive=show_inactive
    )


@bp.route("/create", methods=["GET", "POST"])
def create_account():
    form = AccountForm()
    form.vendor_id.choices = [
        (v.id, v.name) for v in Vendor.query.order_by(Vendor.name)
    ]

    if form.validate_on_submit():
        account_service.create_account(
            name=form.name.data,
            vendor_id=form.vendor_id.data,
            account_type=AccountType(form.account_type.data),
            owner_id=DEFAULT_USER_ID,
            account_number_last4=form.account_number_last4.data or None,
            balance=Decimal(str(form.balance.data)),
        )
        flash("Account created.", "success")
        return redirect(url_for("accounts.list_accounts"))

    return render_template("accounts/form.html", form=form, title="Create Account")


@bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
def edit_account(account_id):
    account = account_service.get_account(account_id)
    if not account:
        flash("Account not found.", "danger")
        return redirect(url_for("accounts.list_accounts"))

    form = AccountForm(obj=account)
    form.vendor_id.choices = [
        (v.id, v.name) for v in Vendor.query.order_by(Vendor.name)
    ]

    if form.validate_on_submit():
        account_service.update_account(
            account_id,
            name=form.name.data,
            vendor_id=form.vendor_id.data,
            account_type=form.account_type.data,
            account_number_last4=form.account_number_last4.data or None,
            balance=Decimal(str(form.balance.data)),
            is_active=form.is_active.data,
        )
        flash("Account updated.", "success")
        return redirect(url_for("accounts.list_accounts"))

    return render_template("accounts/form.html", form=form, title="Edit Account")
