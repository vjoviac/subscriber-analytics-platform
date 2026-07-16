from faker import Faker
import random
from datetime import datetime, UTC

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

def generate_event() -> dict:

    return {
        "event_id": fake.uuid4(),
        "timestamp": datetime.now(UTC).isoformat(),

        "subscriber": {
            "imsi": generate_imsi(),
            "msisdn": generate_msisdn(),
            "plan": random.choice(
                ["Unlimited", "Premium", "Standard", "Prepaid"]
            ),
        },
    }