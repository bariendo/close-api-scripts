import argparse
import asyncio
import sys

from CloseApiWrapper import CloseApiWrapper
from utils.get_api_key import get_api_key


async def update_stale_opportunities(
    months_ago: int,
    env: str,
    dry_run: bool = False,
    verbose: bool = False,
    unresponsive_lead_status_label="Unresponsive",
    lost_opportunity_status_label="Lost",
):
    api_key = get_api_key("api.close.com", f"{env}_admin")
    api = CloseApiWrapper(api_key)

    # Get lead status and opportunity status mappings
    lead_statuses = api.get_lead_statuses()
    opportunity_statuses = api.get_opportunity_statuses()

    # Find the "Unresponsive" lead status ID
    unresponsive_status_id = next(
        (
            status["id"]
            for status in lead_statuses
            if status["label"] == unresponsive_lead_status_label
        ),
        None,
    )

    if not unresponsive_status_id:
        raise ValueError(
            f"Could not find an '{unresponsive_lead_status_label}' lead status"
        )

    # Find the "Lost" opportunity status ID
    lost_opportunity_status_id = next(
        (
            status["id"]
            for status in opportunity_statuses
            if status["label"] == lost_opportunity_status_label
            and status["type"] == "lost"
        ),
        None,
    )

    if not lost_opportunity_status_id:
        raise ValueError(
            f"Could not find a '{lost_opportunity_status_label}' opportunity status"
        )

    # Find the "Payment" custom object type ID
    payment_custom_object_type_id = api.get_custom_object_type_id("Payment")

    if not payment_custom_object_type_id:
        raise ValueError("Could not find a 'Payment' custom object type")

    if verbose:
        print(f"Using 'Lost' opportunity status ID: {lost_opportunity_status_id}")
        print(f"Using 'Unresponsive' lead status ID: {unresponsive_status_id}")
        print(f"Using 'Payment' custom object type ID: {payment_custom_object_type_id}")

    # Build the query to find stale opportunities
    query = {
        "type": "and",
        "queries": [
            {"type": "object_type", "object_type": "opportunity"},
            {
                "type": "field_condition",
                "field": {
                    "type": "regular_field",
                    "object_type": "opportunity",
                    "field_name": "status_type",
                },
                "condition": {"type": "term", "values": ["active"]},
            },
            {
                "type": "field_condition",
                "field": {
                    "type": "regular_field",
                    "object_type": "opportunity",
                    "field_name": "date_updated",
                },
                "condition": {
                    "type": "moment_range",
                    "before": {
                        "type": "offset",
                        "direction": "past",
                        "moment": {"type": "now"},
                        "offset": {
                            "years": 0,
                            "months": months_ago,
                            "weeks": 0,
                            "days": 0,
                            "hours": 0,
                            "minutes": 0,
                            "seconds": 0,
                        },
                        "which_day_end": "start",
                    },
                    "on_or_after": None,
                },
            },
            {
                "type": "has_related",
                "this_object_type": "opportunity",
                "related_object_type": "lead",
                "related_query": {
                    "type": "and",
                    "queries": [
                        {
                            "type": "field_condition",
                            "field": {
                                "type": "regular_field",
                                "object_type": "lead",
                                "field_name": "last_communication_date",
                            },
                            "condition": {
                                "type": "moment_range",
                                "before": {
                                    "type": "offset",
                                    "direction": "past",
                                    "moment": {"type": "now"},
                                    "offset": {
                                        "years": 0,
                                        "months": months_ago,
                                        "weeks": 0,
                                        "days": 0,
                                        "hours": 0,
                                        "minutes": 0,
                                        "seconds": 0,
                                    },
                                    "which_day_end": "start",
                                },
                                "on_or_after": None,
                            },
                        },
                        {
                            "type": "has_related",
                            "negate": True,
                            "this_object_type": "lead",
                            "related_object_type": "custom_object",
                            "related_query": {
                                "type": "and",
                                "queries": [
                                    {"type": "match_all"},
                                    {
                                        "type": "field_condition",
                                        "field": {
                                            "type": "regular_field",
                                            "object_type": "custom_object",
                                            "field_name": "custom_object_type_id",
                                        },
                                        "condition": {
                                            "type": "term",
                                            "values": [payment_custom_object_type_id],
                                        },
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        ],
    }

    sort = [
        {
            "field": {
                "object_type": "opportunity",
                "type": "regular_field",
                "field_name": "date_updated",
            },
            "direction": "asc",
        }
    ]

    # Search for stale opportunities
    stale_opportunities = api.search(
        query=query,
        sort=sort,
        fields=[
            "id",
            "lead_id",
            "lead_name",
            "value_formatted",
            "date_updated",
            "note",
        ],
        object_type="opportunity",
    )

    if verbose:
        print(f"Found {len(stale_opportunities)} stale opportunities")

    if not stale_opportunities:
        print("No stale opportunities found")
        return

    # Group opportunities by lead_id
    opportunities_by_lead = {}
    for opp in stale_opportunities:
        opportunities_by_lead.setdefault(opp["lead_id"], []).append(opp)

    lead_ids = list(opportunities_by_lead.keys())

    if verbose:
        print(f"Found {len(lead_ids)} leads with stale opportunities")

    if dry_run:
        print(
            f"DRY RUN: Would update {len(stale_opportunities)} opportunities and {len(lead_ids)} leads"
        )
        for lead_id, opps in opportunities_by_lead.items():
            print(
                f"Lead {lead_id} ({opps[0]['lead_name']}) has {len(opps)} stale {'opportunity' if len(opps) == 1 else 'opportunities'}"
            )
            for opp in opps:
                print(
                    f"  - Opportunity {opp['id']}: Last updated {opp['date_updated']} ({opp['value_formatted']})"
                )
                if opp["note"]:
                    print(opp["note"])
        return

    # Prepare the updates
    opportunity_updates = []
    for opp in stale_opportunities:
        opportunity_updates.append(
            (
                f"opportunity/{opp['id']}",
                {
                    "status_id": lost_opportunity_status_id,
                    "note": f"Automatically marked as {lost_opportunity_status_label} due to inactivity for {months_ago} months."
                    + (f"\n\n{opp['note']}" if opp.get("note") else ""),
                },
            )
        )

    lead_updates = []
    for lead_id in lead_ids:
        lead_updates.append(
            (
                f"lead/{lead_id}",
                {
                    "status_id": unresponsive_status_id,
                    "description": f"Automatically marked as {unresponsive_lead_status_label} due to inactivity for {months_ago} months.",
                },
            )
        )

    # Perform the updates
    opp_results, opp_errors = await api.put_all(
        opportunity_updates, slice_size=10, verbose=verbose
    )
    if verbose:
        print(
            f"Updated {len(opp_results)} opportunities, encountered {len(opp_errors)} errors"
        )

    lead_results, lead_errors = await api.put_all(
        lead_updates, slice_size=10, verbose=verbose
    )
    if verbose:
        print(
            f"Updated {len(lead_results)} leads, encountered {len(lead_errors)} errors"
        )

    # Summary
    print(
        f"Successfully updated {len(opp_results)} out of {len(stale_opportunities)} opportunities to 'Lost'"
    )
    print(
        f"Successfully updated {len(lead_results)} out of {len(lead_ids)} leads to 'Unresponsive'"
    )

    if opp_errors:
        print(f"Encountered {len(opp_errors)} errors updating opportunities")
    if lead_errors:
        print(f"Encountered {len(lead_errors)} errors updating leads")


def main():
    parser = argparse.ArgumentParser(
        description="Mark stale opportunities as Lost and their leads as Unresponsive"
    )
    parser.add_argument(
        "months", type=int, help="Update opportunities not updated in this many months"
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Perform a dry run without making any changes",
    )
    parser.add_argument(
        "-p", "--prod", action="store_true", help="production environment"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )

    args = parser.parse_args()

    if args.months <= 0:
        parser.error("Months must be a positive integer")

    env = "prod" if args.prod else "dev"

    try:
        asyncio.run(
            update_stale_opportunities(args.months, env, args.dry_run, args.verbose)
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
