from generators.catalogs.applications import APPLICATIONS
from generators.catalogs.devices import DEVICES
from generators.catalogs.locations import NETWORK_CELLS
from generators.catalogs.plans import PLANS
from generators.catalogs.subscribers import SUBSCRIBERS


SUBSCRIBERS_BY_IMSI = {
    subscriber["imsi"]: subscriber
    for subscriber in SUBSCRIBERS
}

PLANS_BY_ID = {
    plan["plan_id"]: plan
    for plan in PLANS
}

DEVICES_BY_TAC = {
    device["tac"]: device
    for device in DEVICES
}

NETWORK_CELLS_BY_ID = {
    cell["cell_id"]: cell
    for cell in NETWORK_CELLS
}

APPLICATIONS_BY_ID = {
    application["application_id"]: application
    for application in APPLICATIONS
}

MATCHED = "MATCHED"
NOT_FOUND = "NOT_FOUND"
NULL_SOURCE_KEY = "NULL_SOURCE_KEY"
NOT_EVALUATED = "NOT_EVALUATED"

UNKNOWN = "UNKNOWN"
NULL_IN_SOURCE = "NULL IN SOURCE"

class EnrichmentError(Exception):
    """Raised when an event cannot be enriched."""


def is_null_or_empty(value: object) -> bool:
    """
    Determine whether a source key is null or empty.
    """
    return value is None or (
        isinstance(value, str)
        and not value.strip()
    )


def lookup_catalog_record(
    catalog_index: dict[str, dict],
    key: object,
    catalog_name: str,
) -> tuple[dict | None, str, str | None]:
    """
    Look up a record without interrupting the enrichment process.

    Returns:
        A tuple containing:
        - catalog record or None;
        - enrichment status;
        - failure reason or None.
    """
    if is_null_or_empty(key):
        return (
            None,
            NULL_SOURCE_KEY,
            f"Source key is null or empty for catalog "
            f"'{catalog_name}'",
        )

    record = catalog_index.get(str(key))

    if record is None:
        return (
            None,
            NOT_FOUND,
            f"Key '{key}' was not found in catalog "
            f"'{catalog_name}'",
        )

    return record, MATCHED, None

def get_missing_marker(status: str) -> str:
    """
    Return the appropriate marker for missing string values.
    """
    if status == NULL_SOURCE_KEY:
        return NULL_IN_SOURCE

    return UNKNOWN


def build_subscriber_defaults(status: str) -> dict:
    marker = get_missing_marker(status)

    return {
        "subscriber_id": marker,
        "plan_id": marker,
        "customer_segment": marker,
        "subscriber_status": marker,
    }


def build_plan_defaults(status: str) -> dict:
    marker = get_missing_marker(status)

    return {
        "plan_name": marker,
        "plan_type": marker,
        "monthly_data_allowance_gb": None,
        "max_download_mbps": None,
        "max_upload_mbps": None,
        "technology_access": [],
    }


def build_device_defaults(status: str) -> dict:
    marker = get_missing_marker(status)

    return {
        "device_vendor": marker,
        "device_model": marker,
        "device_os": marker,
        "max_supported_technology": marker,
    }


def build_network_defaults(status: str) -> dict:
    marker = get_missing_marker(status)

    return {
        "city": marker,
        "state": marker,
        "network_technology": marker,
    }


def build_application_defaults(status: str) -> dict:
    marker = get_missing_marker(status)

    return {
        "application_name": marker,
        "application_category": marker,
        "application_traffic_profile": marker,
        "application_latency_sensitivity": marker,
        "application_packet_loss_sensitivity": marker,
    }



def enrich_event(raw_event: dict) -> dict:
    """
    Enrich a raw telecom event with catalog information.

    Missing or unknown catalog references do not interrupt
    processing. Instead, enrichment status fields are added.
    """
    enriched_event = dict(raw_event)

    imsi = raw_event.get("imsi")
    tac = raw_event.get("tac")
    cell_id = raw_event.get("cell_id")
    application_id = raw_event.get("application_id")

    # ---------------------------------------------------------
    # Subscriber enrichment
    # ---------------------------------------------------------
    subscriber, subscriber_status, subscriber_reason = (
        lookup_catalog_record(
            SUBSCRIBERS_BY_IMSI,
            imsi,
            "subscribers",
        )
    )

    if subscriber_status == MATCHED:
        subscriber_fields = {
            "subscriber_id": subscriber["subscriber_id"],
            "plan_id": subscriber["plan_id"],
            "customer_segment": subscriber[
                "customer_segment"
            ],
            "subscriber_status": subscriber["status"],
        }
    else:
        subscriber_fields = build_subscriber_defaults(
            subscriber_status
        )

    enriched_event.update(subscriber_fields)
    enriched_event["subscriber_enrichment_status"] = (
        subscriber_status
    )
    enriched_event["subscriber_enrichment_reason"] = (
        subscriber_reason
    )

    # ---------------------------------------------------------
    # Plan enrichment
    # ---------------------------------------------------------
    if subscriber_status == MATCHED:
        plan_id = subscriber.get("plan_id")

        plan, plan_status, plan_reason = (
            lookup_catalog_record(
                PLANS_BY_ID,
                plan_id,
                "plans",
            )
        )

        if plan_status == MATCHED:
            plan_fields = {
                "plan_name": plan["plan_name"],
                "plan_type": plan["plan_type"],
                "monthly_data_allowance_gb": plan[
                    "monthly_data_allowance_gb"
                ],
                "max_download_mbps": plan[
                    "max_download_mbps"
                ],
                "max_upload_mbps": plan[
                    "max_upload_mbps"
                ],
                "technology_access": plan[
                    "technology_access"
                ],
            }
        else:
            plan_fields = build_plan_defaults(plan_status)

    else:
        plan_status = NOT_EVALUATED
        plan_reason = (
            "Plan lookup was not evaluated because subscriber "
            "enrichment was unsuccessful"
        )
        plan_fields = build_plan_defaults(plan_status)

    enriched_event.update(plan_fields)
    enriched_event["plan_enrichment_status"] = plan_status
    enriched_event["plan_enrichment_reason"] = plan_reason

    # ---------------------------------------------------------
    # Device enrichment
    # ---------------------------------------------------------
    device, device_status, device_reason = (
        lookup_catalog_record(
            DEVICES_BY_TAC,
            tac,
            "devices",
        )
    )

    if device_status == MATCHED:
        device_fields = {
            "device_vendor": device["device_vendor"],
            "device_model": device["device_model"],
            "device_os": device["device_os"],
            "max_supported_technology": device[
                "max_supported_technology"
            ],
        }
    else:
        device_fields = build_device_defaults(device_status)

    enriched_event.update(device_fields)
    enriched_event["device_enrichment_status"] = device_status
    enriched_event["device_enrichment_reason"] = device_reason

    # ---------------------------------------------------------
    # Network and location enrichment
    # ---------------------------------------------------------
    network_cell, network_status, network_reason = (
        lookup_catalog_record(
            NETWORK_CELLS_BY_ID,
            cell_id,
            "network_cells",
        )
    )

    if network_status == MATCHED:
        network_fields = {
            "city": network_cell["city"],
            "state": network_cell["state"],
            "network_technology": network_cell[
                "technology"
            ],
        }
    else:
        network_fields = build_network_defaults(
            network_status
        )

    enriched_event.update(network_fields)
    enriched_event["network_enrichment_status"] = (
        network_status
    )
    enriched_event["network_enrichment_reason"] = (
        network_reason
    )

    # ---------------------------------------------------------
    # Application enrichment
    # ---------------------------------------------------------
    application, application_status, application_reason = (
        lookup_catalog_record(
            APPLICATIONS_BY_ID,
            application_id,
            "applications",
        )
    )

    if application_status == MATCHED:
        application_fields = {
            "application_name": application[
                "application_name"
            ],
            "application_category": application[
                "category"
            ],
            "application_traffic_profile": application[
                "traffic_profile"
            ],
            "application_latency_sensitivity": application[
                "latency_sensitivity"
            ],
            "application_packet_loss_sensitivity": application[
                "packet_loss_sensitivity"
            ],
        }
    else:
        application_fields = build_application_defaults(
            application_status
        )

    enriched_event.update(application_fields)
    enriched_event["application_enrichment_status"] = (
        application_status
    )
    enriched_event["application_enrichment_reason"] = (
        application_reason
    )

    return enriched_event