from flask_wtf import FlaskForm
from wtforms import StringField, DateField
from wtforms.validators import DataRequired, Length


class AnalysisPeriodForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if self.start_date.data and self.end_date.data:
            if self.start_date.data >= self.end_date.data:
                self.end_date.errors.append("End date must be after start date.")
                return False
        return True
