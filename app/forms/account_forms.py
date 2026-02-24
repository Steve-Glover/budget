from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, BooleanField
from wtforms.validators import DataRequired, Optional, Length

from app.models.enums import AccountType


class AccountForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    vendor_id = SelectField("Vendor", coerce=int, validators=[DataRequired()])
    account_type = SelectField(
        "Account Type",
        choices=[(t.value, t.value.replace("_", " ").title()) for t in AccountType],
        validators=[DataRequired()],
    )
    account_number_last4 = StringField(
        "Last 4 Digits", validators=[Optional(), Length(max=4)]
    )
    balance = DecimalField("Balance", default=0.00, places=2, validators=[Optional()])
    is_active = BooleanField("Active", default=True)
