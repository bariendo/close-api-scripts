#!/usr/bin/env python3
import argparse
import asyncio
from typing import Any
from CloseApiWrapper import CloseApiWrapper
from utils.get_api_key import get_api_key


async def toggle_discounts_field(
    api: CloseApiWrapper,
    opportunities: list[dict[str, Any]],
    discounts_field_id: str,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Toggle the "Consultation Fee Credit" value in the Discounts field for opportunities.

    Args:
        api: CloseApiWrapper instance
        opportunities: list of opportunity dictionaries
        discounts_field_id: The prefixed custom field ID (e.g., "custom.cf_xxx")
        verbose: Whether to print verbose output

    Returns:
        tuple of (successful_updates, failed_updates)
    """
    endpoint_and_data_list = []

    for opp in opportunities:
        current_discounts = opp.get(discounts_field_id, [])

        # Toggle "Consultation Fee Credit"
        if "Consultation Fee Credit" in current_discounts:
            # Remove it
            new_discounts = [
                d for d in current_discounts if d != "Consultation Fee Credit"
            ]
            action = "Removed"
        else:
            # Add it
            new_discounts = current_discounts + ["Consultation Fee Credit"]
            action = "Added"

        if verbose:
            print(f"{action} 'Consultation Fee Credit' for opportunity {opp['id']}")

        update_data = {discounts_field_id: new_discounts}

        endpoint_and_data_list.append((f"opportunity/{opp['id']}", update_data))

    # Perform concurrent updates
    successful_updates, failed_updates = await api.put_all(
        endpoint_and_data_list, slice_size=10, verbose=verbose
    )

    return successful_updates, failed_updates


async def main():
    parser = argparse.ArgumentParser(
        description="Toggle the 'Consultation Fee Credit' value in the Discounts field for opportunities"
    )
    parser.add_argument(
        "-p", "--prod", action="store_true", help="production environment"
    )
    parser.add_argument(
        "-n",
        "--max-opportunities",
        type=int,
        default=10,
        help="Maximum number of opportunities to fetch and update (default: 10)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making actual updates",
    )
    parser.add_argument(
        "--updated-before-minutes",
        type=int,
        default=5,
        help="Fetch opportunities not updated since N minutes ago (default: 5)",
    )

    args = parser.parse_args()

    # Initialize API wrapper
    env = "prod" if args.prod else "dev"
    # api_key = get_api_key("api.close.com", f"{env}_admin")
    
    if not api_key:
        raise SystemExit(
            "Missing API key. Add a Keychain item for api.close.com with account {env}_admin.".format(
                env=env
            )
        )
    api = CloseApiWrapper(api_key=api_key)

    # Get the necessary opportunity custom field IDs
    services_custom_field_id = api.get_custom_field_id("opportunity", "Services")
    discounts_field_id = api.get_prefixed_custom_field_id("opportunity", "Discounts")
    if not discounts_field_id:
        print("Error: Could not find 'Discounts' custom field for opportunities")
        return

    if args.verbose:
        print(f"Discounts field ID: {discounts_field_id}")

    # Opportunity search query
    query = {
        "type": "and",
        "queries": [
            {"type": "object_type", "object_type": "opportunity"},
            {
                "type": "field_condition",
                "field": {
                    "type": "custom_field",
                    "custom_field_id": services_custom_field_id,
                },
                "condition": {"type": "exists"},
            },
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
                            "days": 0,
                            "hours": 0,
                            "minutes": args.updated_before_minutes,
                            "months": 0,
                            "seconds": 0,
                            "weeks": 0,
                            "years": 0,
                        },
                        "which_day_end": "start",
                    },
                    "on_or_after": None,
                },
            },
        ],
    }

    # Search for opportunities
    print(f"Searching for opportunities not updated in the last {args.updated_before_minutes} minutes (max: {args.max_opportunities})...")
    opportunities = api.search(
        query=query,
        object_type="opportunity",
        results_limit=args.max_opportunities,
        fields=["id", "lead_id", "value", discounts_field_id],
    )

    if not opportunities:
        print("No opportunities found matching the search criteria")
        return

    print(f"Found {len(opportunities)} opportunities")

    if args.dry_run:
        print("\n--- DRY RUN MODE ---")
        for opp in opportunities:
            current_discounts = opp.get(discounts_field_id, [])
            if "Consultation Fee Credit" in current_discounts:
                action = "Would remove"
            else:
                action = "Would add"

            lead_url = f"https://app.close.com/lead/{opp['lead_id']}"
            print(f"{action} 'Consultation Fee Credit' for opportunity {opp['id']}")
            print(f"  Lead: {lead_url}")
            print(f"  Current discounts: {current_discounts}")
        print("\nNo actual updates were made (dry run)")
        return

    # Toggle the discounts field for all opportunities
    print("\nUpdating opportunities...")
    successful_updates, failed_updates = await toggle_discounts_field(
        api, opportunities, discounts_field_id, verbose=args.verbose
    )

    # Print results
    print(f"\n--- Update Results ---")
    print(f"Successfully updated: {len(successful_updates)} opportunities")
    print(f"Failed updates: {len(failed_updates)} opportunities")

    if successful_updates:
        print("\nSuccessfully updated opportunities:")
        for i, result in enumerate(successful_updates):
            opp = opportunities[i]  # Assuming order is preserved
            lead_url = f"https://app.close.com/lead/{opp['lead_id']}"
            print(f"  ✓ Opportunity {result['id']}")
            print(f"    Lead: {lead_url}")

    if failed_updates:
        print("\nFailed updates:")
        for failure in failed_updates:
            if isinstance(failure, dict) and "data" in failure:
                endpoint, _ = failure["data"]
                opp_id = endpoint.split("/")[-1]
                # Find the corresponding opportunity
                failed_opp = next((o for o in opportunities if o["id"] == opp_id), None)
                if failed_opp:
                    lead_url = f"https://app.close.com/lead/{failed_opp['lead_id']}"
                    print(f"  ✗ Opportunity {opp_id}")
                    print(f"    Lead: {lead_url}")
                    if "errors" in failure:
                        print(f"    Error: {failure['errors']}")
            else:
                print(f"  ✗ Error: {failure}")

    print(f"\nTotal opportunities processed: {len(opportunities)}")


if __name__ == "__main__":
    asyncio.run(main())
