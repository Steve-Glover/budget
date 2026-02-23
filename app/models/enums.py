import enum


class AccountType(str, enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class TransactionType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class Variability(str, enum.Enum):
    FIXED = "fixed"
    VARIABLE = "variable"


class Frequency(str, enum.Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"
