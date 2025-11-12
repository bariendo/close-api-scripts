import argparse
import csv
import os
from datetime import date, datetime

from CloseApiWrapper import CloseApiWrapper
from utils.get_api_key import get_api_key

# Refunded opportunity status ID
REFUNDED_STATUS_ID = "stat_qsftsiOHpKUsGuoJ5Fdq6lRuWOxsdSBlXbIZvZkCHHi"

# Lead custom field names
USER_ID_CUSTOM_FIELD_NAME = "bariendo_user_id"
HEALTHIE_USER_ID_CUSTOM_FIELD_NAME = "healthie_user_id"
PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME = "Patient Navigator"

# Opportunity custom field names
LOSS_REASON_CUSTOM_FIELD_NAME = "Loss Reason"
LOSS_REASON_DETAILS_CUSTOM_FIELD_NAME = "Loss Reason Details"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export refunded opportunities (by status ID) within a date_won range, "
            "with lead-level fields, to CSV."
        )
    )
    parser.add_argument(
        "-f",
        "--won-from",
        required=True,
        help="Start date for date_won filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-t",
        "--won-to",
        help="End date for date_won filter (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "-p", "--prod", action="store_true", help="production environment"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output CSV path. Defaults to output/refunded_opportunities-ENV-START_END.csv",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Increase logging verbosity."
    )
    return parser.parse_args()


def parse_date(s: str) -> date:
    return datetime.fromisoformat(s).date()


def build_query(api: CloseApiWrapper, start_dt: date, end_dt: date) -> dict:
    # Build a has_related query for opportunities with refunded status and date_won in range
    date_range = api.build_date_range_query(
        object_type="opportunity",
        field_name="date_won",
        start_date=start_dt,
        end_date=end_dt,
    )

    return {
        "type": "has_related",
        "this_object_type": "lead",
        "related_object_type": "opportunity",
        "related_query": {
            "type": "and",
            "queries": [
                {
                    "type": "field_condition",
                    "field": {
                        "type": "regular_field",
                        "object_type": "opportunity",
                        "field_name": "status_id",
                    },
                    "condition": {
                        "type": "reference",
                        "reference_type": "status.opportunity",
                        "object_ids": [REFUNDED_STATUS_ID],
                    },
                },
                date_range,
            ],
        },
    }


def fetch_users_map(api: CloseApiWrapper) -> dict:
    # Map user_id -> user name
    try:
        users = api.get("user", params={"_fields": "id,name"})["data"]
        return {
            u["id"]: u.get("name") or u.get("full_name") or u.get("email")
            for u in users
        }
    except Exception:
        # Fallback to get_all if needed
        users = api.get_all("user")
        mapping = {}
        for u in users:
            name = (
                u.get("name")
                or (
                    (u.get("first_name") or "").strip()
                    + " "
                    + (u.get("last_name") or "").strip()
                ).strip()
            )
            mapping[u["id"]] = name or u.get("email") or u["id"]
        return mapping


def to_csv(
    leads: list[dict],
    users_map: dict,
    opportunity_custom_fields_map: dict,
    start_dt: date,
    end_dt: date,
    output_path: str,
    verbose: bool = False,
) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # CSV columns
    headers = [
        "lead_id",
        "lead_name",
        "lead_date_created",
        USER_ID_CUSTOM_FIELD_NAME,
        HEALTHIE_USER_ID_CUSTOM_FIELD_NAME,
        PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME,
        "opportunity_id",
        "opportunity_value_formatted",
        "opportunity_status_type",
        "opportunity_status_label",
        "opportunity_user_name",
        "opportunity_date_won",
        "opportunity_date_lost",
        "opportunity_loss_reason",
        "opportunity_loss_reason_details",
    ]

    loss_reason_custom_field_id = opportunity_custom_fields_map[
        LOSS_REASON_CUSTOM_FIELD_NAME
    ]
    loss_reason_details_custom_field_id = opportunity_custom_fields_map[
        LOSS_REASON_DETAILS_CUSTOM_FIELD_NAME
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        total_opps = 0
        for lead in leads:
            # Filter only refunded opps from the embedded opportunities list
            opportunities = lead.get("opportunities", [])
            for opp in opportunities:
                if opp.get("status_id") != REFUNDED_STATUS_ID:
                    continue
                # date_won filter (defensive, since the search should already restrict)
                dw = opp.get("date_won")
                if not dw:
                    continue
                try:
                    won_d = datetime.fromisoformat(dw).date()
                except Exception:
                    continue
                if not (start_dt <= won_d <= end_dt):
                    continue

                custom = lead.get("custom") or {}
                pn_id = custom.get(PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME)
                pn_name = users_map.get(pn_id) if isinstance(pn_id, str) else None

                row = {
                    "lead_id": lead.get("id"),
                    "lead_name": lead.get("name"),
                    "lead_date_created": lead.get("date_created"),
                    USER_ID_CUSTOM_FIELD_NAME: custom.get(USER_ID_CUSTOM_FIELD_NAME),
                    HEALTHIE_USER_ID_CUSTOM_FIELD_NAME: custom.get(
                        HEALTHIE_USER_ID_CUSTOM_FIELD_NAME
                    ),
                    PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME: pn_name,
                    "opportunity_id": opp.get("id"),
                    "opportunity_value_formatted": opp.get("value_formatted"),
                    "opportunity_status_type": opp.get("status_type"),
                    "opportunity_status_label": opp.get("status_label"),
                    "opportunity_user_name": opp.get("user_name"),
                    "opportunity_date_won": opp.get("date_won"),
                    "opportunity_date_lost": opp.get("date_lost"),
                    "opportunity_loss_reason": opp.get(loss_reason_custom_field_id),
                    "opportunity_loss_reason_details": opp.get(
                        loss_reason_details_custom_field_id
                    ),
                }
                writer.writerow(row)
                total_opps += 1

        if verbose:
            print(f"Wrote {total_opps} refunded opportunities to {output_path}")


def main() -> int:
    args = parse_args()

    # Parse dates
    start_dt = parse_date(args.won_from)
    end_dt = parse_date(args.won_to) if args.won_to else date.today()
    if end_dt < start_dt:
        raise ValueError("end date must be on or after start date")

    # Init API (prefer CLI flag, then env var, then Keychain)
    env = "prod" if args.prod else "dev"
    api_key = get_api_key("api.close.com", f"{env}_admin")
    if not api_key:
        raise SystemExit(
            "Missing API key. Add a Keychain item for api.close.com with account {env}_admin.".format(
                env=env
            )
        )
    api = CloseApiWrapper(api_key)

    # Build query and fetch leads
    query = build_query(api, start_dt, end_dt)
    sort = [
        {
            "direction": "asc",
            "field": {
                "type": "regular_field",
                "object_type": "lead",
                "field_name": "primary_opportunity_date_won",
            },
        }
    ]
    fields = [
        "id",
        "name",
        "opportunities",
        "custom",
        "date_created",
    ]

    if args.verbose:
        print(
            f"Searching refunded opportunities won between {start_dt.isoformat()} and {end_dt.isoformat()}..."
        )

    leads = api.search(query=query, sort=sort, fields=fields, object_type="lead")

    if args.verbose:
        print(f"Found {len(leads)} leads")

    # Fetch users and make ID->name mapping for Patient Navigator field
    users_map = fetch_users_map(api)

    # Fetch opportunity custom field name->ID mapping
    opportunity_custom_fields_map = api.get_custom_field_name_prefixed_id_mapping(
        "opportunity"
    )

    # Output path
    default_output = os.path.join(
        "output",
        f"refunded_opportunities-{env}-{start_dt.isoformat()}_{end_dt.isoformat()}.csv",
    )
    output_path = args.output or default_output

    # Write CSV
    to_csv(
        leads,
        users_map,
        opportunity_custom_fields_map,
        start_dt,
        end_dt,
        output_path,
        verbose=args.verbose,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
