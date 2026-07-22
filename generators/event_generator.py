from faker import Faker
import random
from datetime import datetime, UTC
from generators.catalogs.applications import APPLICATIONS
from generators.catalogs.devices import DEVICES
from generators.catalogs.locations import NETWORK_CELLS
from generators.catalogs.plans import PLANS
from generators.catalogs.subscribers import SUBSCRIBERS

NETWORK_QUALITY_PROFILES = {
    "4G": {
        "latency_ms_range": (30, 100),
        "packet_loss_pct_range": (0.1, 2.0),
    },
    "5G": {
        "latency_ms_range": (10, 50),
        "packet_loss_pct_range": (0.0, 1.0),
    },
}

APPLICATION_TRAFFIC_PROFILES = {
    "video_streaming": {
        "bytes_dl_range": (5_000_000, 80_000_000),
        "bytes_ul_range": (100_000, 2_000_000),
    },

    "social_media": {
        "bytes_dl_range": (1_000_000, 30_000_000),
        "bytes_ul_range": (200_000, 4_000_000),
    },

    "messaging": {
        "bytes_dl_range": (50_000, 2_000_000),
        "bytes_ul_range": (50_000, 1_500_000),
    },

    "audio_streaming": {
        "bytes_dl_range": (500_000, 8_000_000),
        "bytes_ul_range": (50_000, 500_000),
    },

    "real_time": {
        "bytes_dl_range": (1_000_000, 15_000_000),
        "bytes_ul_range": (1_000_000, 12_000_000),
    },
}

fake = Faker()

def get_plan_by_id(plan_id: str) -> dict:
    for plan in PLANS:
        if plan["plan_id"] == plan_id:
            return plan

    raise ValueError(
        f"Plan not found: {plan_id}"
    )

def get_device_supported_technologies(
    device: dict[str, str],
) -> set[str]:
    max_supported_technology = device[
        "max_supported_technology"
    ]

    if max_supported_technology == "5G":
        return {"4G", "5G"}

    if max_supported_technology == "4G":
        return {"4G"}

    raise ValueError(
        "Unsupported maximum device technology: "
        f"{max_supported_technology}"
    )

def get_compatible_network_cells(
    device: dict[str, str],
    plan: dict,
) -> list[dict[str, str]]:
    device_technologies = (
        get_device_supported_technologies(device)
    )

    plan_technologies = set(
        plan["technology_access"]
    )

    allowed_technologies = (
        device_technologies
        & plan_technologies
    )

    compatible_cells = [
        cell
        for cell in NETWORK_CELLS
        if cell["technology"] in allowed_technologies
    ]

    if not compatible_cells:
        raise ValueError(
            "No compatible network cells found "
            f"for device TAC {device['tac']} "
            f"and plan {plan['plan_id']}"
        )

    return compatible_cells

def generate_session(
    application: dict[str, str],
    network: dict[str, str],
) -> dict[str, int | float]:

    technology = network["technology"]

    traffic_profile = APPLICATION_TRAFFIC_PROFILES[application["traffic_profile"]]
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

def generate_event(event_time: datetime | None = None,) -> dict:
    application = random.choice(APPLICATIONS)

    subscriber = random.choice(SUBSCRIBERS)
    plan = get_plan_by_id(
        subscriber["plan_id"]
    )

    device = random.choice(DEVICES)

    compatible_cells = get_compatible_network_cells(
        device=device,
        plan=plan,
    )

    location = random.choice(compatible_cells)

    session = generate_session(
        application=application,
        network=location,
    )

    timestamp = event_time or datetime.now(UTC)

    return {
        "event_id": fake.uuid4(),
        "timestamp": timestamp.isoformat(),
        "imsi": subscriber["imsi"],
        "msisdn": subscriber["msisdn"],
        "tac": device["tac"],
        "cell_id": location["cell_id"],
        "application_id": application["application_id"],
        **session,
    }

def generate_events(total_events: int,event_time: datetime | None = None,) -> list[dict]:
    if total_events <= 0:
        raise ValueError(
            "total_events must be greater than zero"
        )

    return [
        generate_event(event_time)
        for _ in range(total_events)
    ]