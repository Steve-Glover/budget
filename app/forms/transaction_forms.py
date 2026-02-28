from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, DecimalField, DateField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length

from app.models.enums import TransactionType


def _int_or_none(x):
    """Coerce for optional integer SelectFields whose None sentinel is the empty string.

    Only '' and None map to None; any other non-integer value raises ValueError so
    WTForms can reject it as 'not a valid choice'.
    """
    if x == "" or x is None:
        return None
    return int(x)  # ValueError propagates for invalid non-empty values


class TransactionForm(FlaskForm):
    transaction_date = DateField("Transaction Date", validators=[DataRequired()])
    post_date = DateField("Post Date", validators=[Optional()])
    payee = StringField("Payee", validators=[DataRequired(), Length(max=200)])
    description = StringField("Description", validators=[Optional(), Length(max=500)])
    amount = DecimalField("Amount", places=2, validators=[DataRequired()])
    transaction_type = SelectField(
        "Type",
        choices=[(t.value, t.value.title()) for t in TransactionType],
        validators=[DataRequired()],
    )
    debit_account_id = SelectField(
        "Debit Account", coerce=_int_or_none, validators=[Optional()]
    )
    credit_account_id = SelectField(
        "Credit Account", coerce=_int_or_none, validators=[Optional()]
    )
    category_id = SelectField("Category", coerce=_int_or_none, validators=[Optional()])
    subcategory_id = SelectField(
        "Subcategory", coerce=_int_or_none, validators=[Optional()]
    )
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])


class CSVImportForm(FlaskForm):
    csv_file = FileField(
        "CSV File", validators=[FileRequired(), FileAllowed(["csv"], "CSV files only")]
    )
    account_id = SelectField(
        "Default Account", coerce=_int_or_none, validators=[Optional()]
    )
