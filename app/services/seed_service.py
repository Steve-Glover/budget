from app.extensions import db
from app.models.category import Category
from app.models.vendor import Vendor

DEFAULT_CATEGORIES = {
    "Housing": [
        "Mortgage/Rent",
        "Property Tax",
        "Home Insurance",
        "Utilities",
        "Maintenance",
    ],
    "Transportation": [
        "Car Payment",
        "Gas/Fuel",
        "Auto Insurance",
        "Maintenance",
        "Public Transit",
    ],
    "Food": ["Groceries", "Dining Out", "Coffee"],
    "Healthcare": [
        "Health Insurance",
        "Doctor/Medical",
        "Dental",
        "Pharmacy",
        "Vision",
    ],
    "Entertainment": ["Streaming", "Movies/Events", "Hobbies", "Subscriptions"],
    "Personal": ["Clothing", "Personal Care", "Gym/Fitness"],
    "Education": ["Tuition", "Books", "Online Courses"],
    "Savings": ["Emergency Fund", "Retirement", "Investments"],
    "Debt": ["Student Loans", "Credit Card Payments", "Personal Loans"],
    "Insurance": ["Life Insurance", "Disability"],
    "Gifts & Donations": ["Gifts", "Charity"],
    "Miscellaneous": ["Other"],
}

DEFAULT_VENDORS = [
    ("Bank of America", "BoA"),
    ("Chase", "Chase"),
    ("American Express", "Amex"),
    ("Wells Fargo", "WF"),
    ("Citi", "Citi"),
    ("Capital One", "CapOne"),
]


def seed_categories() -> list[Category]:
    """Seed default categories and subcategories. Idempotent — skips existing."""
    created = []
    for parent_name, children in DEFAULT_CATEGORIES.items():
        parent = Category.query.filter_by(name=parent_name, parent_id=None).first()
        if not parent:
            parent = Category(name=parent_name)
            db.session.add(parent)
            db.session.flush()
            created.append(parent)

        for child_name in children:
            child = Category.query.filter_by(
                name=child_name, parent_id=parent.id
            ).first()
            if not child:
                child = Category(name=child_name, parent_id=parent.id)
                db.session.add(child)
                created.append(child)

    db.session.commit()
    return created


def seed_vendors() -> list[Vendor]:
    """Seed default vendors. Idempotent — skips existing."""
    created = []
    for name, short_name in DEFAULT_VENDORS:
        vendor = Vendor.query.filter_by(name=name).first()
        if not vendor:
            vendor = Vendor(name=name, short_name=short_name)
            db.session.add(vendor)
            created.append(vendor)

    db.session.commit()
    return created


def seed_all() -> dict:
    """Seed all default data. Returns counts of created items."""
    categories = seed_categories()
    vendors = seed_vendors()
    return {"categories": len(categories), "vendors": len(vendors)}
