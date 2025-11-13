import argparse
import asyncio
import json
import logging
from pathlib import Path

from CloseApiWrapper import CloseApiWrapper
from utils.get_api_key import get_api_key

parser = argparse.ArgumentParser(
    description="Export Close custom activity instances within a date range into a JSON file"
)
parser.add_argument("-p", "--prod", action="store_true", help="production environment")
parser.add_argument(
    "--custom-activity-type",
    "-t",
    choices=[
        "Lead Qualification",
        "Receptionist Note",
    ],
    required=True,
    help="The name of custom activity you'd like to export to JSON",
)
parser.add_argument(
    "--date-start",
    "-s",
    help="The yyyy-mm-dd you want to start looking for activities",
)
parser.add_argument(
    "--date-end",
    "-d",
    help="The yyyy-mm-dd you want to end looking for activities",
)
args = parser.parse_args()

env = "prod" if args.prod else "dev"

api_key = get_api_key("api.close.com", f"{env}_admin")
api = CloseApiWrapper(api_key)


async def main():
    custom_activity_type_id = api.get_custom_activity_type_id(args.custom_activity_type)
    if not custom_activity_type_id:
        logging.error(f"Custom activity '{args.custom_activity_type}' not found.")
        return

    custom_field_id_name_mapping = api.get_custom_field_id_name_mapping(
        f"activity/{custom_activity_type_id}"
    )
    # TODO: Specify fields since this now returns bare minimum fields
    custom_activity_instances = await api.get_custom_activity_instances(
        custom_activity_type_id
    )

    # Replace object keys in custom_activity_instances using custom_field_id_name_mapping
    for instance in custom_activity_instances:
        keys_to_replace = [key for key in instance.keys() if key.startswith("custom.")]
        for key in keys_to_replace:
            field_id = key.split("custom.")[1]
            human_readable_field_name = custom_field_id_name_mapping.get(field_id)
            if human_readable_field_name:
                instance[human_readable_field_name] = instance.pop(key)

    if custom_activity_instances:
        logging.info(
            f"{len(custom_activity_instances)} {args.custom_activity_type} instances"
        )
        fp = Path(f"output/custom_activity-{args.custom_activity_type}-{env}.json")
        fp.parent.mkdir(parents=True, exist_ok=True)
        with fp.open("w") as f:
            json.dump(custom_activity_instances, f)
    else:
        logging.info(f"No {args.custom_activity_type} instances were found.")


if __name__ == "__main__":
    asyncio.run(main())
