"""Verify louis_service imports resolve correctly."""


def test_louis_service_imports_without_error():
    from louis_service import LouisService  # noqa: F401
    assert LouisService is not None


def test_response_templates_importable():
    from response_templates import get_template, TEMPLATE_METADATA  # noqa: F401
    assert get_template is not None


def test_red_flag_detector_importable():
    from louis.red_flag_detector import RedFlagDetector  # noqa: F401
    assert RedFlagDetector is not None


def test_data_domain_importable():
    from data_domain.mongo_event_repo import MongoEventRepository  # noqa: F401
    assert MongoEventRepository is not None
