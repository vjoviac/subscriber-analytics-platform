from copy import deepcopy

import pytest

from generators.catalogs.applications import APPLICATIONS
from generators.catalogs.devices import DEVICES
from generators.catalogs.locations import NETWORK_CELLS
from generators.catalogs.subscribers import SUBSCRIBERS
from enrichment.event_enricher import (
    MATCHED,
    NOT_EVALUATED,
    NOT_FOUND,
    NULL_SOURCE_KEY,
    enrich_event,
)


@pytest.fixture
def valid_raw_event() -> dict:
    """
    Build a valid raw event using existing catalog records.

    Using catalog values prevents the test from depending on
    hardcoded IMSIs, TACs, cell IDs, or application IDs.
    """
    subscriber = SUBSCRIBERS[0]
    device = DEVICES[0]
    network_cell = NETWORK_CELLS[0]
    application = APPLICATIONS[0]

    return {
        "event_id": "test-event-001",
        "timestamp": "2026-07-21T19:00:00+00:00",
        "imsi": subscriber["imsi"],
        "msisdn": subscriber["msisdn"],
        "tac": device["tac"],
        "cell_id": network_cell["cell_id"],
        "application_id": application["application_id"],
        "bytes_dl": 1_000_000,
        "bytes_ul": 250_000,
        "total_bytes": 1_250_000,
        "latency_ms": 45,
        "packet_loss_pct": 0.25,
    }


def test_enrich_valid_event(valid_raw_event: dict) -> None:
    """
    A valid event should be enriched successfully by every catalog.
    """
    enriched_event = enrich_event(valid_raw_event)

    assert enriched_event["subscriber_enrichment_status"] == MATCHED
    assert enriched_event["plan_enrichment_status"] == MATCHED
    assert enriched_event["device_enrichment_status"] == MATCHED
    assert enriched_event["network_enrichment_status"] == MATCHED
    assert enriched_event["application_enrichment_status"] == MATCHED

    assert enriched_event["subscriber_enrichment_reason"] is None
    assert enriched_event["plan_enrichment_reason"] is None
    assert enriched_event["device_enrichment_reason"] is None
    assert enriched_event["network_enrichment_reason"] is None
    assert enriched_event["application_enrichment_reason"] is None

    assert enriched_event["subscriber_id"] != "UNKNOWN"
    assert enriched_event["plan_name"] != "UNKNOWN"
    assert enriched_event["device_vendor"] != "UNKNOWN"
    assert enriched_event["city"] != "UNKNOWN"
    assert enriched_event["application_name"] != "UNKNOWN"


def test_unknown_device_returns_not_found(
    valid_raw_event: dict,
) -> None:
    """
    An unknown TAC should not interrupt enrichment.
    """
    event = {
        **valid_raw_event,
        "tac": "99999999",
    }

    enriched_event = enrich_event(event)

    assert enriched_event["device_enrichment_status"] == NOT_FOUND

    assert enriched_event["device_vendor"] == "UNKNOWN"
    assert enriched_event["device_model"] == "UNKNOWN"
    assert enriched_event["device_os"] == "UNKNOWN"
    assert (
        enriched_event["max_supported_technology"]
        == "UNKNOWN"
    )

    assert "99999999" in enriched_event[
        "device_enrichment_reason"
    ]

    # Other independent catalog lookups should still succeed.
    assert enriched_event["subscriber_enrichment_status"] == MATCHED
    assert enriched_event["plan_enrichment_status"] == MATCHED
    assert enriched_event["network_enrichment_status"] == MATCHED
    assert enriched_event["application_enrichment_status"] == MATCHED


def test_null_application_returns_null_source_key(
    valid_raw_event: dict,
) -> None:
    """
    A null application ID should be identified as a source issue.
    """
    event = {
        **valid_raw_event,
        "application_id": None,
    }

    enriched_event = enrich_event(event)

    assert (
        enriched_event["application_enrichment_status"]
        == NULL_SOURCE_KEY
    )

    assert (
        enriched_event["application_name"]
        == "NULL IN SOURCE"
    )
    assert (
        enriched_event["application_category"]
        == "NULL IN SOURCE"
    )
    assert (
        enriched_event["application_traffic_profile"]
        == "NULL IN SOURCE"
    )
    assert (
        enriched_event["application_latency_sensitivity"]
        == "NULL IN SOURCE"
    )
    assert (
        enriched_event[
            "application_packet_loss_sensitivity"
        ]
        == "NULL IN SOURCE"
    )

    assert enriched_event["application_id"] is None

    # Other independent enrichments should still succeed.
    assert enriched_event["subscriber_enrichment_status"] == MATCHED
    assert enriched_event["plan_enrichment_status"] == MATCHED
    assert enriched_event["device_enrichment_status"] == MATCHED
    assert enriched_event["network_enrichment_status"] == MATCHED


def test_unknown_subscriber_prevents_plan_lookup(
    valid_raw_event: dict,
) -> None:
    """
    When a subscriber is unknown, plan enrichment cannot be evaluated.
    """
    event = {
        **valid_raw_event,
        "imsi": "334030999999999",
    }

    enriched_event = enrich_event(event)

    assert (
        enriched_event["subscriber_enrichment_status"]
        == NOT_FOUND
    )
    assert (
        enriched_event["plan_enrichment_status"]
        == NOT_EVALUATED
    )

    assert enriched_event["subscriber_id"] == "UNKNOWN"
    assert enriched_event["plan_id"] == "UNKNOWN"
    assert enriched_event["customer_segment"] == "UNKNOWN"
    assert enriched_event["subscriber_status"] == "UNKNOWN"

    assert enriched_event["plan_name"] == "UNKNOWN"
    assert enriched_event["plan_type"] == "UNKNOWN"
    assert enriched_event["monthly_data_allowance_gb"] is None
    assert enriched_event["max_download_mbps"] is None
    assert enriched_event["max_upload_mbps"] is None
    assert enriched_event["technology_access"] == []

    assert "334030999999999" in enriched_event[
        "subscriber_enrichment_reason"
    ]
    assert "subscriber enrichment was unsuccessful" in (
        enriched_event["plan_enrichment_reason"]
    )

    # Independent catalog lookups should still succeed.
    assert enriched_event["device_enrichment_status"] == MATCHED
    assert enriched_event["network_enrichment_status"] == MATCHED
    assert enriched_event["application_enrichment_status"] == MATCHED


def test_enrichment_does_not_modify_raw_event(
    valid_raw_event: dict,
) -> None:
    """
    Enrichment must return a new object and preserve the raw event.
    """
    original_event = deepcopy(valid_raw_event)

    enriched_event = enrich_event(valid_raw_event)

    assert valid_raw_event == original_event
    assert enriched_event is not valid_raw_event

    for field, value in original_event.items():
        assert enriched_event[field] == value