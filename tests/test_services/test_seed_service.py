import pytest

from app.models.category import Category
from app.models.vendor import Vendor
from app.services.seed_service import (
    DEFAULT_CATEGORIES,
    DEFAULT_VENDORS,
    seed_all,
    seed_categories,
    seed_vendors,
)


class TestSeedCategories:
    def test_creates_all_top_level_categories(self, session):
        seed_categories()
        top_level = Category.query.filter_by(parent_id=None).all()
        assert {c.name for c in top_level} == set(DEFAULT_CATEGORIES.keys())

    @pytest.mark.parametrize(
        "parent_name,expected_children",
        list(DEFAULT_CATEGORIES.items()),
        ids=list(DEFAULT_CATEGORIES.keys()),
    )
    def test_subcategories_per_parent(self, session, parent_name, expected_children):
        seed_categories()
        parent = Category.query.filter_by(name=parent_name, parent_id=None).first()
        actual = {c.name for c in Category.query.filter_by(parent_id=parent.id).all()}
        assert actual == set(expected_children)

    def test_idempotent(self, session):
        first = seed_categories()
        second = seed_categories()
        assert len(first) > 0
        assert len(second) == 0
        expected = len(DEFAULT_CATEGORIES) + sum(
            len(v) for v in DEFAULT_CATEGORIES.values()
        )
        assert Category.query.count() == expected


class TestSeedVendors:
    def test_creates_all_vendors(self, session):
        seed_vendors()
        vendors = Vendor.query.all()
        assert len(vendors) == len(DEFAULT_VENDORS)
        assert {v.name for v in vendors} == {name for name, _ in DEFAULT_VENDORS}
        assert {v.short_name for v in vendors} == {sn for _, sn in DEFAULT_VENDORS}

    def test_idempotent(self, session):
        first = seed_vendors()
        second = seed_vendors()
        assert len(first) == len(DEFAULT_VENDORS)
        assert len(second) == 0


class TestSeedAll:
    def test_seeds_everything(self, session):
        result = seed_all()
        expected_cats = len(DEFAULT_CATEGORIES) + sum(
            len(v) for v in DEFAULT_CATEGORIES.values()
        )
        assert result["categories"] == expected_cats
        assert result["vendors"] == len(DEFAULT_VENDORS)
