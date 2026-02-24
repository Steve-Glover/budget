from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    DecimalField,
    DateField,
    TextAreaField,
    BooleanField,
)
from wtforms.validators import DataRequired, Optional, Length

from app.models.enums import Variability, Frequency


class BudgetForm(FlaskForm):
    payee = StringField("Payee", validators=[DataRequired(), Length(max=200)])
    variability = SelectField(
        "Variability",
        choices=[(v.value, v.value.title()) for v in Variability],
        validators=[DataRequired()],
    )
    frequency = SelectField(
        "Frequency",
        choices=[(f.value, f.value.replace("_", " ").title()) for f in Frequency],
        validators=[DataRequired()],
    )
    date_scheduled = DateField("Scheduled Date", validators=[DataRequired()])
    budgeted_amount = DecimalField(
        "Budgeted Amount", places=2, validators=[DataRequired()]
    )
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    subcategory_id = SelectField("Subcategory", coerce=int, validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
    is_active = BooleanField("Active", default=True)
