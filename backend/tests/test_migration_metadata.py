from sqlalchemy import CheckConstraint

from growthos.models import Base

EXPECTED_ENUM_CHECKS = {
    "notifications": {
        "ck_notification_category",
        "ck_notification_importance",
    },
    "notification_category_preferences": {
        "ck_notification_category_preference_category",
        "ck_notification_category_preference_mode",
    },
    "notification_digests": {
        "ck_notification_digest_frequency",
        "ck_notification_digest_status",
    },
    "notification_deliveries": {
        "ck_notification_delivery_mode",
        "ck_notification_delivery_status",
    },
    "professional_content_reviews": {"ck_professional_review_decision"},
}


def test_migration_enum_checks_are_declared_in_sqlalchemy_metadata() -> None:
    for table_name, expected_names in EXPECTED_ENUM_CHECKS.items():
        table = Base.metadata.tables[table_name]
        actual_names = {
            constraint.name
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }
        assert expected_names <= actual_names
