# Close API scripts

Collection of Python scripts for interacting with [Close](http://close.com/) through its [API](http://developer.close.com/) using the [closeio_api Python client](https://github.com/closeio/closeio-api).

## Prerequisites

- macOS (for Keychain authentication)
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Close API key stored in macOS Keychain

## Setup

### 1. Install uv

If you don't have `uv` installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and set up the repository

```bash
git clone git@github.com:bariendo/close-api-scripts.git
cd close-api-scripts
git switch additional-scripts
uv sync
```

### 3. Configure API key in macOS Keychain

Scripts authenticate via macOS Keychain instead of command-line arguments. Add your Close API key(s):

```bash
# For production environment
security add-internet-password -a 'prod_admin' -s 'api.close.com' -w 'your_api_key_here'

# For development environment (if applicable)
security add-internet-password -a 'dev_admin' -s 'api.close.com' -w 'your_dev_api_key_here'
```

**Note:** This authentication method will eventually be replaced with [Proton Pass CLI](<https://proton.me/blog/pass-roadmap-summer-2025#:~:text=Command%2Dline%20interface%20(CLI)>) once available.

## Authentication

### macOS Keychain (preferred)

All actively maintained scripts call `utils.get_api_key` and expect macOS Keychain entries (Proton Pass CLI once it launches). Create entries for:

- `api.close.com` accounts `dev_admin` and `prod_admin` (Close API keys)
- `api.gethealthie.com` (Healthie appointments)
- `api.calltrackingmetrics.com` (CallTrackingMetrics)
- `api.getbase.com` (Zendesk/Base CRM)
- `api.stripe.com` (Stripe metadata updates)

### `-k/--api-key` argument

A few older scripts still take `--api-key YOUR_CLOSE_KEY` because they have not been migrated to Keychain.

## Running scripts

Use `uv run` to execute scripts:

```bash
uv run scripts/<script_name>.py [arguments]
```

Many scripts support common arguments:

- `-p` or `--prod`: Use production environment (defaults to `dev` if not specified)
- `-v` or `--verbose`: Enable detailed logging
- `-d` or `--dry-run`: Preview changes without executing them (when available)

Check individual script help for specific options:

```bash
uv run scripts/<script_name>.py --help
```

## Frequently used scripts

### Link custom activities to opportunities

Remap custom activity instances (e.g., clinical consultations) to relevant opportunities after the original opportunities are deleted (e.g., due to cleanup work) so future syncs and analytics (e.g., post-consultation conversion rate calculation) stay accurate.

```bash
uv run scripts/link_custom_activities_and_opportunities.py --prod 'Clinical Consultation'
```

### Mark stale opportunities as lost

Enforce the six-month freshness rule by marking untouched opportunities (and their leads) as lost so returning leads generate a fresh, accurately-credited (e.g., self-serve) opportunity.

```bash
uv run scripts/mark_stale_opportunities_as_lost.py --prod
```

### Update custom field values

Standardize dropdown options by swapping old entries for new ones. Use `update_custom_field_value.py` for any object type and `update_opportunity_field_value.py` when you need the extra status/date filters. (These may be consolidated in the future.)

```bash
uv run scripts/update_custom_field_value.py --prod opportunity Services 'Revision of A' 'Revision of B'
uv run scripts/update_opportunity_field_value.py --prod --custom-field "Services" --old-value "Revision of A" --new-value "Revision of B" --status-label Active --end-date 2024-12-31
```

### Toggle opportunity discounts

Trigger an outstanding-balance recalculation by briefly removing or adding the “Consultation Fee Credit” discount across a batch of opportunities.

```bash
uv run scripts/toggle_opportunity_discounts.py --prod
uv run scripts/toggle_opportunity_discounts.py --prod -n 100 --updated-before-minutes 30
```

### Reassign or delete opportunities

Interactively reassign or delete opportunities, e.g., to clean up opportunities created from erroneously typed Healthie appointments.

```bash
uv run scripts/reassign_or_delete_opportunities.py --prod bot@example.com
```

### Update workflow schedules

Turn weekdays on or off across active workflows when holidays need to be observed.

```bash
uv run scripts/update_workflow_schedules.py --prod Mon on
uv run scripts/update_workflow_schedules.py --prod Wed,Thu,Fri off
uv run scripts/update_workflow_schedules.py --prod Mon,Wed off --include "D:" --exclude "A:"
```

### Export refunded opportunities

Export a CSV of refunded opportunities with loss reasons and lead metadata for the exact won-date window under review.

```bash
uv run scripts/export_refunded_opportunities.py -f 2025-01-01 -t 2025-01-31 --prod
uv run scripts/export_refunded_opportunities.py --won-from 2025-01-01 --prod
```

## Script catalog

### Lead & contact management

| Script                                      | Purpose                                                                                                                 |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `assign_leads_from_deal_users.py`           | Fill the "Patient Navigator" custom field for unassigned leads using opp owners, task assignees, or note/email authors. |
| `bulk_update_address_countries.py`          | Swap one ISO country code for another across all lead addresses (requires `--api-key`).                                 |
| `bulk_update_leads_info.py`                 | CSV importer that maps columns into leads, contacts, and opportunities (requires `--api-key`).                          |
| `create_receptionist_notes.py`              | Convert AnswerConnect CSV exports into Close "Receptionist Note" custom activities.                                     |
| `csv_to_cio.py`                             | CSV importer that groups rows by company before creating leads (requires `--api-key`).                                  |
| `delete_duplicate_contact_details.py`       | Remove duplicate email/phone/url entries per contact.                                                                   |
| `delete_emails_from_contacts.py`            | Strip specific email addresses listed in a CSV from their contacts (requires `--api-key`).                              |
| `delete_leads.py`                           | Delete leads by explicit list, file, or "last N minutes" query (writes backups to `output/`).                           |
| `delete_secondary_addresses.py`             | Remove all but the primary address from leads (requires `--api-key`).                                                   |
| `find_contact_duplicates_on_single_lead.py` | Identify duplicate contacts (name/email/phone) within a single lead (requires `--api-key`).                             |
| `find_duplicate_leads.py`                   | Flag duplicate leads by name, contact info, or hostname and export CSVs (requires `--api-key`).                         |
| `import_leads_from_csv.py`                  | Create leads/contacts with navigator, language, and note metadata from CSV.                                             |
| `import_leads_from_close_json.py`           | Re-create leads from a Close JSON export inside another org (requires `--api-key`).                                     |
| `move_custom_field_to_contact_info.py`      | Move phone/email values stored in custom fields into contact records (requires `--api-key`).                            |
| `restore_deleted_leads.py`                  | Rebuild deleted leads (contacts, opps, tasks, notes, SMS) from the event log (requires `--api-key`).                    |
| `update_lead_status.py`                     | Move leads to a new status if their opportunities contain a specific loss reason.                                       |

### Opportunity & custom activity management

| Script                                                | Purpose                                                                                              |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `create_lead_qualification_and_opportunity.py`        | Build a Lead Qualification custom activity and optional opportunity from an existing activity URL.   |
| `delete_duplicate_custom_activity_instances.py`       | Remove duplicate custom activity instances (e.g., double-synced procedures).                         |
| `delete_opportunities_in_status.py`                   | Delete every opportunity in a given status label after exporting a CSV backup.                       |
| `link_custom_activities_and_opportunities.py`         | Backfill links between a custom activity type and its corresponding opportunities.                   |
| `link_stripe_payments_to_close_opportunities.py`      | Match Stripe charges to won opportunities and stamp the charge metadata.                             |
| `mark_stale_opportunities_as_lost.py`                 | Mark opportunities as Lost/Unresponsive if they and their leads have been idle for N months.         |
| `remove_opportunity_notes.py`                         | Strip duplicate notes and optionally move Lead Source info out of opportunity notes.                 |
| `replace_lost_opportunity_with_lead_qualification.py` | Promote information from a lost opportunity back into the lead qualification form.                   |
| `reassign_or_delete_opportunities.py`                 | Interactive CLI to reassign/delete active opportunities owned by a specific user.                    |
| `toggle_opportunity_discounts.py`                     | Add or remove the "Consultation Fee Credit" multi-select value to trigger remaining balance recalcs. |
| `update_custom_field_value.py`                        | Replace one custom field value with another across leads, contacts, or opportunities.                |
| `update_opportunity_field_value.py`                   | Replace a custom field value (string or multi-select) across filtered opportunities.                 |
| `update_opportunities.py`                             | Change the status of every opportunity returned by a lead search query (requires `--api-key`).       |
| `user_reassign.py`                                    | Reassign tasks/opportunities from one user to another using IDs or emails (requires `--api-key`).    |

### Task/note management

| Script                               | Purpose                                                                                             |
| ------------------------------------ | --------------------------------------------------------------------------------------------------- |
| `delete_incomplete_tasks.py`         | Export and delete auto-generated incomplete tasks, optionally filtered by creator/assignee.         |
| `delete_tasks_for_inactive_users.py` | Delete every task assigned to inactive members (requires `--api-key`).                              |
| `restore_deleted_tasks.py`           | Recreate deleted tasks from the event log using a list of task IDs (requires `--api-key`).          |
| `update_note_users.py`               | Experimental tool that rewrites notes so `user_id` matches `created_by` (never used in production). |

### Workflow & automation

| Script                                 | Purpose                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `change_sequence_sender.py`            | Swap the sender email/account for workflow subscriptions tied to a user (requires `--api-key`).  |
| `change_workflow_call_assignee.py`     | Reassign workflow call steps from one user to another or to each lead's Patient Navigator.       |
| `enroll_lead_in-follow-up_workflow.py` | Enroll a contact into the correct follow-up workflow based on Lead Qualification data.           |
| `re-enroll_contacts_in_workflows.py`   | Unenroll and immediately re-enroll untouched contacts in workflows filtered by name prefix/date. |
| `update_workflow_schedules.py`         | Enable or disable specific weekdays in workflow schedules across selected sequences.             |

### Reporting & auditing

| Script                                    | Purpose                                                                                                           |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `bulk_download_call_recordings.py`        | Download every call/voicemail recording in a date range to disk (requires `--api-key`).                           |
| `custom_field_change_report.py`           | Export every change to a specific custom field over a date range (requires `--api-key`).                          |
| `events_by_request_id.py`                 | Dump all events tied to a specific Close request ID into JSON (requires `--api-key`).                             |
| `export_activities_to_json.py`            | Export specific Close activity types (call, email, status change, etc.) between two dates (requires `--api-key`). |
| `export_calls.py`                         | Export calls filtered by date, user, number, or direction to CSV (requires `--api-key`).                          |
| `export_custom_activity_instances.py`     | Dump Lead Qualification or Receptionist Note instances with human-readable field names.                           |
| `export_refunded_opportunities.py`        | Export refunded opportunities plus lead/user metadata between two won dates.                                      |
| `export_sequence_subscriptions_public.py` | Export workflow subscriptions (optionally filtered by sequence) to CSV (requires `--api-key`).                    |
| `export_sequences_data.py`                | Export sequence metadata and subscription counts (requires `--api-key`).                                          |
| `export_sms.py`                           | Export SMS messages filtered by direction/status/user/dates (requires `--api-key`).                               |
| `run_leads_deleted_report.py`             | Report on deleted leads from the last 30 days and how they were removed (requires `--api-key`).                   |
| `run_leads_merged_report.py`              | Export lead merge events from the last 30 days (requires `--api-key`).                                            |
| `time_to_respond_report.py`               | Calculate response-time metrics for calls/emails/SMS per user or org (requires `--api-key`).                      |

### Organization management

| Script                                   | Purpose                                                                         |
| ---------------------------------------- | ------------------------------------------------------------------------------- |
| `clone_organization.py`                  | Duplicate organization configuration to a new organization.                     |
| `merge_opportunity_statuses.py`          | Merge one lost status into another while stamping a standard loss reason.       |
| `toggle_webhook_subscription.py`         | List webhook subscriptions, select them interactively, and toggle their status. |
| `update_template_and_workflow_prefix.py` | Rename email/SMS templates and sequences by swapping prefixes.                  |

### Data sync & integrations

| Script                                    | Purpose                                                                                             |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `check_synced_appointments.py`            | Cross-check Healthie appointments against Close Procedure activities to find missing syncs.         |
| `sync_calltrackingmetrics_to_bigquery.py` | Fetch CallTrackingMetrics call data and load it into BigQuery (CTM token + GCP creds required).     |
| `sync_calltrackingmetrics_to_close.py`    | Import CallTrackingMetrics call/SMS JSON exports into Close activities.                             |
| `sync_healthie_user_ids.py`               | Copy Healthie user IDs stored in Zendesk Sell contacts into Close leads.                            |
| `sync_zendesk_leads.py`                   | Sync Zendesk Sell (Base CRM) contacts and leads into Close, de-duplicating by name/email/phone.     |
| `sync_zendesk_line_items.py`              | Push Zendesk Sell deal line items into a Close opportunity custom field.                            |
| `sync_zendesk_records_to_close.py`        | Mirror Zendesk Sell notes & tasks into Close while preserving timestamps.                           |
| `sync_zendesk_secondary_emails.py`        | Append Zendesk Sell secondary emails into Close contacts when they differ from the primary address. |
| `validate_appointments.py`                | Sanity-check Healthie appointments (contact type, location, blockers) and output CSV findings.      |

## Development

### Code formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for code formatting:

```bash
uvx ruff format scripts/ # or: uv format -- scripts/
uvx ruff check scripts/CloseApiWrapper.py # or: uv format --check -- scripts/CloseApiWrapper.py
```

### Adding new scripts

1. Create your script in the `scripts/` directory
2. Use `CloseApiWrapper` for Close API interactions (preferred over raw `closeio_api` client)
3. Import `get_api_key` for authentication (defaults to dev environment):

   ```python
   import argparse

   from CloseApiWrapper import CloseApiWrapper
   from utils.get_api_key import get_api_key

   parser = argparse.ArgumentParser(description='Your script description')
   parser.add_argument('-p', '--prod', action='store_true', help='production environment')
   args = parser.parse_args()

   env = 'prod' if args.prod else 'dev'
   api_key = get_api_key("api.close.com", f"{env}_admin")
   close = CloseApiWrapper(api_key)
   ```

4. Follow existing patterns for argument parsing and error handling

## Support

If you have any questions, please contact [support@close.com](mailto:support@close.com?Subject=Close%20API%20Scripts).
