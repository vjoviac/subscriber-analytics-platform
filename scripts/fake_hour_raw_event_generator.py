from datetime import datetime, UTC

from generators.event_generator import generate_events
from main import build_output_file
from storage.storage_manager import save_events_to_jsonl

hours = [8, 9, 10, 11]

for hour in hours:

    processing_time = datetime(
        2026,
        7,
        22,
        hour,
        0,
        tzinfo=UTC,
    )

    events = generate_events(
        total_events=500,
        event_time=processing_time,
    )

    output_file = build_output_file(
        processing_time,
    )

    save_events_to_jsonl(
        events,
        output_file,
    )

    print(output_file)