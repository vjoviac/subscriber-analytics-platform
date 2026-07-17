import pytest

from generators.event_generator import (
    generate_events,
    generate_imsi,
    generate_msisdn,
)


def test_generate_msisdn_has_mexican_format() -> None:
    msisdn = generate_msisdn()

    assert msisdn.startswith("+52")
    assert len(msisdn) == 13
    assert msisdn[1:].isdigit()


def test_generate_imsi_has_valid_length() -> None:
    imsi = generate_imsi()

    assert imsi.startswith("334")
    assert len(imsi) == 15
    assert imsi.isdigit()


def test_generate_events_returns_expected_count() -> None:
    events = generate_events(5)

    assert len(events) == 5


def test_generate_events_rejects_invalid_count() -> None:
    with pytest.raises(ValueError):
        generate_events(0)