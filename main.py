import json

from generators.event_generator import generate_event


def main():

    event = generate_event()

    print(
        json.dumps(
            event,
            indent=4,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()