import argparse
import asyncio
import sys
from typing import Any

from CloseApiWrapper import APIError, CloseApiWrapper
from utils.get_api_key import get_api_key

# --- Configuration ---
# Exact name of the Lead Custom Field containing the target User ID
PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME = "Patient Navigator"
# ---------------------


async def reassign_or_delete_opportunities(
    current_owner_identifier: str,
    env: str,
    dry_run: bool = False,
    verbose: bool = False,
):
    """
    Fetches opportunities for a user and interactively prompts to reassign them
    based on a Lead custom field.
    """
    print(
        f"--- Starting Opportunity Reassignment for '{current_owner_identifier}' in {env.upper()} environment ---"
    )
    if dry_run:
        print("--- DRY RUN MODE ENABLED: No changes will be made. ---")

    try:
        api_key = get_api_key("api.close.com", f"{env}_admin")
        api = CloseApiWrapper(api_key)

        # 1. Get all users
        print("Fetching all users...")
        users = await api.get_all_async("user")
        print(f"{len(users)} users found.")

        # 2. Get the Current Owner User ID
        current_owner = next(
            iter(
                u
                for u in users
                if u["id"] == current_owner_identifier
                or u["email"] == current_owner_identifier
                or (
                    current_owner_identifier.startswith(u["first_name"])
                    and current_owner_identifier.endswith(u["last_name"])
                )
            ),
            None,
        )

        if not current_owner:
            print(
                f"Error: Could not find user matching identifier '{current_owner_identifier}'. Exiting."
            )
            return 1
        current_owner_id = current_owner["id"]
        current_owner_name = f"{current_owner['first_name']} {current_owner['last_name']} ({current_owner['email']})"
        print(f"Found Current Owner: {current_owner_name} (ID: {current_owner_id})")

        # 3. Build dictionary of user IDs mapped to user objects for easier lookup
        user_dict = {user["id"]: user for user in users}
        if verbose:
            print(f"Created lookup dictionary with {len(user_dict)} users.")

        # 4. Get the "Patient Navigator" Custom Field ID (prefixed)
        print(
            f"Fetching Custom Field ID for '{PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME}' (Lead)..."
        )
        pn_custom_field_id_prefixed = api.get_prefixed_custom_field_id(
            "lead", PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME
        )
        if not pn_custom_field_id_prefixed:
            print(
                f"Error: Could not find Lead Custom Field named '{PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME}'. Exiting."
            )
            return 1
        print(f"Found Custom Field ID: {pn_custom_field_id_prefixed}")

        # 3. Fetch Opportunities for the Current Owner
        print(f"\nFetching active opportunities owned by {current_owner_name}...")
        query = {
            "type": "has_related",
            "this_object_type": "lead",
            "related_object_type": "opportunity",
            "related_query": {
                "type": "and",
                "queries": [
                    # Filter by current owner
                    {
                        "type": "field_condition",
                        "field": {
                            "type": "regular_field",
                            "object_type": "opportunity",
                            "field_name": "user_id",  # user_id is the owner field
                        },
                        "condition": {
                            "type": "reference",
                            "reference_type": "user_or_group",
                            "object_ids": [current_owner_id],
                        },
                    },
                    # Only consider active opportunities
                    {
                        "type": "field_condition",
                        "field": {
                            "type": "regular_field",
                            "object_type": "opportunity",
                            "field_name": "status_type",
                        },
                        "condition": {"type": "term", "values": ["active"]},
                    },
                ],
            },
        }

        sort = [
            {
                "field": {
                    "object_type": "lead",
                    "type": "regular_field",
                    "field_name": "last_opportunity_won_date_won",
                },
                "direction": "asc",
            }
        ]

        # Request opportunity fields and the related lead's custom field
        fields_to_request = [
            "id",
            "display_name",
            "opportunities",
            pn_custom_field_id_prefixed,
        ]

        leads = api.search(
            query=query,
            sort=sort,
            fields=fields_to_request,
        )

        print(
            f"Found {len(leads)} leads with active opportunities owned by {current_owner_name}."
        )

        if not leads:
            print("No leads require processing.")
            return 0

        # 4. Interactive Decision Loop
        updates_to_make: list[tuple[str, dict[str, Any]]] = []
        deletions_to_make: list[str] = []
        print("\n--- Review Opportunities for Reassignment ---")

        for index, lead in enumerate(leads):
            # Filter active opportunities belonging to the current owner
            owner_opportunities = [
                opp
                for opp in lead["opportunities"]
                if opp.get("user_id") == current_owner_id
                and opp.get("status_type") == "active"
            ]

            if not owner_opportunities:
                if verbose:
                    print(
                        f"  No active opportunities owned by {current_owner_name} found for this lead."
                    )
                continue

            print("-" * 80)
            print(f"Lead {index + 1} of {len(leads)}")
            print(f"  Name: {lead.get('display_name', 'N/A')}")
            print(f"  URL: https://app.close.com/lead/{lead['id']}/")

            potential_new_owner_id = lead.get(pn_custom_field_id_prefixed)

            if not potential_new_owner_id:
                print(
                    f"  Status: Skipping - Lead custom field '{PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME}' is empty or missing."
                )
                continue

            if not isinstance(
                potential_new_owner_id, str
            ) or not potential_new_owner_id.startswith("user_"):
                print(
                    f"  Status: Skipping - Custom field value '{potential_new_owner_id}' is not a valid User ID."
                )
                continue

            if potential_new_owner_id == current_owner_id:
                print(
                    "  Status: Skipping - Potential new owner is the same as the current owner."
                )
                continue

            # Fetch potential new owner details (use cache)
            new_owner_details = user_dict.get(potential_new_owner_id)
            if not new_owner_details:
                print(
                    f"  Status: Skipping - Could not find user for ID '{potential_new_owner_id}'."
                )
                continue

            new_owner_name = f"{new_owner_details['first_name']} {new_owner_details['last_name']} ({new_owner_details['email']})"
            print(f"  {PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME}: {new_owner_name}")

            for opp_index, opp in enumerate(owner_opportunities):
                print(f"  Opportunity {opp_index + 1} of {len(owner_opportunities)}")
                print(f"    ID: {opp['id']}")
                print(f"    Value: {opp.get('value_formatted', 'N/A')}")
                print(f"    Note: {opp.get('note', 'N/A')}")

                # Prompt user
                while True:
                    decision = input(
                        f"    Change owner to {new_owner_name}? (y/n/DELETE): "
                    ).strip()
                    if decision == "y":
                        updates_to_make.append(
                            (
                                f"opportunity/{opp['id']}/",
                                {"user_id": new_owner_details["id"]},
                            )
                        )
                        print(
                            f"    Action: Marked for owner change to {new_owner_name}."
                        )
                        break
                    elif decision == "n":
                        print("    Action: Owner will not be changed.")
                        break
                    elif decision == "DELETE":
                        deletions_to_make.append(f"opportunity/{opp['id']}/")
                        print("    Action: Marked for deletion.")
                        break
                    else:
                        print(decision)
                        print("    Invalid input. Please enter 'y', 'n', or 'DELETE'.")

        # 5. Show dry run results
        if dry_run:
            print("\n--- DRY RUN: Showing updates that WOULD be made ---")
            for endpoint, data in updates_to_make:
                opp_id = endpoint.split("/")[-1]
                new_owner_id = data["user_id"]
                new_owner_email = user_dict.get(new_owner_id, {}).get(
                    "email", "Unknown"
                )
                print(
                    f"  - Would update Opportunity {opp_id} owner to {new_owner_email} ({new_owner_id})"
                )
            for endpoint in deletions_to_make:
                opp_id = endpoint.split("/")[-1]
                print(f"  - Would delete Opportunity {opp_id}")
            print("--- End of Dry Run ---")
            return 0

        # 6. Perform Updates
        print("-" * 80)

        if updates_to_make:
            print("\n--- Opportunity Updates ---")
            confirm = (
                input(f"Proceed with {len(updates_to_make)} updates? (y/n): ")
                .lower()
                .strip()
            )
            if confirm == "y":
                print("Applying updates concurrently...")
                successful_results, failed_results = await api.put_all(
                    endpoint_and_data_list=updates_to_make,
                    slice_size=10,
                    verbose=verbose,
                )
                if successful_results:
                    print(
                        f"Successfully updated {len(successful_results)} opportunities."
                    )
                if failed_results:
                    print(f"Failed to delete {len(failed_results)} opportunities:")
                    for fail in failed_results:
                        if (
                            isinstance(fail, dict) and "error_type" in fail
                        ):  # Validation Error from wrapper
                            original_endpoint, original_data = fail["data"]
                            print(
                                f"  - Opportunity {original_endpoint}: Validation Error"
                            )
                            if fail.get("errors"):
                                print(f"    General Errors: {fail['errors']}")
                            if fail.get("field_errors"):
                                print(f"    Field Errors: {fail['field_errors']}")
                        elif isinstance(fail, Exception):
                            print(
                                f"  - Update failed with Exception: {fail}"
                            )  # General APIError or other
                        else:
                            print(f"  - Unknown failure format: {fail}")
        else:
            print("\nNo opportunities were marked for owner change.")

        if deletions_to_make:
            print("\n--- Opportunity Deletions ---")
            confirm = (
                input(
                    f"Proceed with deletion of {len(deletions_to_make)} opportunities? (y/n): "
                )
                .lower()
                .strip()
            )
            if confirm == "y":
                print("Deleting opportunities...")
                successful_results, failed_results = await api.delete_all(
                    endpoints=deletions_to_make,
                    slice_size=10,
                    verbose=verbose,
                )
                if successful_results:
                    print(
                        f"Successfully deleted {len(successful_results)} opportunities."
                    )
                if failed_results:
                    print(f"Failed to delete {len(failed_results)} opportunities:")
                    for fail in failed_results:
                        if (
                            isinstance(fail, dict) and "error_type" in fail
                        ):  # Validation Error from wrapper
                            original_endpoint, original_data = fail["data"]
                            print(
                                f"  - Opportunity {original_endpoint}: Validation Error"
                            )
                            if fail.get("errors"):
                                print(f"    General Errors: {fail['errors']}")
                            if fail.get("field_errors"):
                                print(f"    Field Errors: {fail['field_errors']}")
                        elif isinstance(fail, Exception):
                            print(
                                f"  - Deletion failed with Exception: {fail}"
                            )  # General APIError or other
                        else:
                            print(f"  - Unknown failure format: {fail}")
        else:
            print("\nNo opportunities were marked for deletion.")

        print("--- Reassignment Process Complete ---")
        return 0

    except APIError as e:
        print(f"\nFATAL API Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                print(f"Response Body: {e.response.json()}")
            except Exception:
                print(f"Response Text: {e.response.text}")
        return 1
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description=f"Interactively reassign opportunities from one user to another based on the '{PATIENT_NAVIGATOR_CUSTOM_FIELD_NAME}' Lead Custom Field."
    )
    parser.add_argument(
        "owner_identifier",
        type=str,
        help="Identifier for the current opportunity owner (e.g., email address, user ID, or first/last name)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Perform a dry run: show opportunities and potential changes without making updates.",
    )
    parser.add_argument(
        "--prod",
        "-p",
        action="store_true",
        help="Run against the production environment (default is dev).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information during processing.",
    )

    args = parser.parse_args()

    env = "prod" if args.prod else "dev"

    try:
        exit_code = asyncio.run(
            reassign_or_delete_opportunities(
                args.owner_identifier, env, args.dry_run, args.verbose
            )
        )
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
