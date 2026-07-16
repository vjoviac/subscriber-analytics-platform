from faker import Faker
import random
from datetime import datetime, UTC
from generators.catalogs import (
    APPLICATION_CATALOG,
    APPLICATION_TRAFFIC_PROFILES,
    DEVICE_CATALOG,
    NETWORK_CELLS,
    NETWORK_QUALITY_PROFILES,
    PLANS,
)

fake = Faker()

def generate_msisdn() -> str:
    country_code = "52"
    national_number = "".join(
        str(random.randint(0, 9))
        for _ in range(10)
    )

    return f"+{country_code}{national_number}"

def generate_imsi() -> str:
    mcc = "334"
    mnc = random.choice(["020", "030", "050"])
    subscriber_id = "".join(
        str(random.randint(0, 9))
        for _ in range(15 - len(mcc) - len(mnc))
    )

    return f"{mcc}{mnc}{subscriber_id}"

def generate_device() -> dict[str, str]:
    device = random.choice(DEVICE_CATALOG)

    return device.copy()

def generate_network() -> dict[str, str]:
    network = random.choice(NETWORK_CELLS)

    return network.copy()

def generate_application() -> dict[str, str]:
    application = random.choice(APPLICATION_CATALOG)

    return application.copy()

def generate_session(
    application: dict[str, str],
    network: dict[str, str],
) -> dict[str, int | float]:

    application_id = application["application_id"]
    technology = network["technology"]

    traffic_profile = APPLICATION_TRAFFIC_PROFILES[application_id]
    quality_profile = NETWORK_QUALITY_PROFILES[technology]

    bytes_dl = random.randint(
        *traffic_profile["bytes_dl_range"]
    )

    bytes_ul = random.randint(
        *traffic_profile["bytes_ul_range"]
    )

    latency_ms = random.randint(
        *quality_profile["latency_ms_range"]
    )

    packet_loss_pct = round(
        random.uniform(
            *quality_profile["packet_loss_pct_range"]
        ),
        2,
    )

    return {
        "bytes_dl": bytes_dl,
        "bytes_ul": bytes_ul,
        "total_bytes": bytes_dl + bytes_ul,
        "latency_ms": latency_ms,
        "packet_loss_pct": packet_loss_pct,
    }

def generate_event() -> dict:
    application = generate_application()
    network = generate_network()

    return {
        "event_id": fake.uuid4(),
        "timestamp": datetime.now(UTC).isoformat(),

        "subscriber": {
            "imsi": generate_imsi(),
            "msisdn": generate_msisdn(),
            "plan": random.choice(PLANS),
        },
        "device": generate_device(),
        "network": network,
        "application": application,
        "session": generate_session(application=application, network=network),
    }

def generate_events(total_events: int) -> list[dict]:
    if total_events <= 0:
        raise ValueError(
            "total_events must be greater than zero"
        )

    return [
        generate_event()
        for _ in range(total_events)
    ]