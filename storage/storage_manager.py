import json
from pathlib import Path
from typing import Any


def save_events_to_jsonl(
    events: list[dict[str, Any]],
    output_file: Path,
) -> None:
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        for event in events:
            json_line = json.dumps(
                event,
                ensure_ascii=False,
            )

            file.write(json_line + "\n")