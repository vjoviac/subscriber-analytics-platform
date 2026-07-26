from analytics.subscriber_profiles import (
    build_current_subscriber_profiles_snapshot,
)
from config.settings import (
    DAILY_ACTIVITY_DIRECTORY,
    SUBSCRIBER_PROFILES_CURRENT_DIRECTORY,
)


def main() -> None:
    output_file = (
        build_current_subscriber_profiles_snapshot(
            daily_activity_directory=(
                DAILY_ACTIVITY_DIRECTORY
            ),
            output_directory=(
                SUBSCRIBER_PROFILES_CURRENT_DIRECTORY
            ),
        )
    )

    print(
        "Current subscriber profiles created: "
        f"{output_file}"
    )


if __name__ == "__main__":
    main()