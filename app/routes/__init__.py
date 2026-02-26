from app.routes.main import bp as main_bp
from app.routes.accounts import bp as accounts_bp
from app.routes.budgets import bp as budgets_bp
from app.routes.transactions import bp as transactions_bp
from app.routes.analysis import bp as analysis_bp


def register_blueprints(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(accounts_bp, url_prefix="/accounts")
    app.register_blueprint(budgets_bp, url_prefix="/budgets")
    app.register_blueprint(transactions_bp, url_prefix="/transactions")
    app.register_blueprint(analysis_bp, url_prefix="/analysis")
