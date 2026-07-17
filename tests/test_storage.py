import json
from pathlib import Path

from storage.storage_manager import save_events_to_jsonl


def test_save_events_to_jsonl(
    tmp_path: Path,
) -> None:
    events = [
        {"event_id": "evt-1"},
        {"event_id": "evt-2"},
    ]

    output_file = tmp_path / "events.jsonl"

    save_events_to_jsonl(
        events=events,
        output_file=output_file,
    )

    lines = output_file.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["event_id"] == "evt-1"