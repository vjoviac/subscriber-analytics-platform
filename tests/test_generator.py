import pytest
from generators.catalogs.subscribers import SUBSCRIBERS
from generators.event_generator import (
    generate_event,
    generate_events,
)


def test_generate_event_uses_consistent_subscriber_data() -> None:
    event = generate_event()

    subscriber = next(
        item
        for item in SUBSCRIBERS
        if item["imsi"] == event["imsi"]
    )

    assert event["msisdn"] == subscriber["msisdn"]


def test_generate_event_uses_known_subscriber() -> None:
    event = generate_event()

    valid_imsis = {
        subscriber["imsi"]
        for subscriber in SUBSCRIBERS
    }

    assert event["imsi"] in valid_imsis


def test_generate_events_returns_expected_count() -> None:
    events = generate_events(5)

    assert len(events) == 5


def test_generate_events_rejects_invalid_count() -> None:
    with pytest.raises(ValueError):
        generate_events(0)