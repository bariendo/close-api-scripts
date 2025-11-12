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

## Running scripts

Use `uv run` to execute scripts:

```bash
uv run scripts/<script_name>.py [arguments]
```

## Available scripts

### Lead management

**Update leads in bulk based on CSV input or criteria:**

```bash
uv run scripts/bulk_update_leads_info.py
```

**Export CSV of potential duplicate leads:**

```bash
uv run scripts/find_duplicate_leads.py
```

**Restore deleted leads:**

```bash
uv run scripts/restore_deleted_leads.py
```

### Contact management

**Export CSV of duplicate contacts on the same lead:**

```bash
uv run scripts/find_contact_duplicates_on_single_lead.py
```

**Delete duplicate email addresses and phone numbers from contacts:**

```bash
uv run scripts/delete_duplicate_contact_details.py
```

**Delete emails from contacts:**

```bash
uv run scripts/delete_emails_from_contacts.py
```

**Move custom field data to contact info:**

Transfer email/phone data from lead custom fields to contact records (post-migration cleanup).

```bash
uv run scripts/move_custom_field_to_contact_info.py
```

### Opportunity management

**Create lead qualification form and opportunity:**

```bash
uv run scripts/create_lead_qualification_and_opportunity.py
```

**Link custom activities and opportunities:**

Associate custom activity instances with their corresponding opportunities.

```bash
uv run scripts/link_custom_activities_and_opportunities.py --prod 'Clinical Consultation'
```

**Mark stale opportunities as lost:**

Automatically mark opportunities that haven't been updated in a specified timeframe as lost.

```bash
uv run scripts/mark_stale_opportunities_as_lost.py --prod
```

**Delete lost opportunity and transfer loss reason data to lead qualification form:**

```bash
uv run scripts/replace_lost_opportunity_with_lead_qualification.py
```

**Update opportunity field value:**

Bulk update a specific custom field value for opportunities matching criteria.

```bash
uv run scripts/update_opportunity_field_value.py
```

**Update custom field value:**

Bulk update a specific custom field across multiple leads or opportunities.

```bash
uv run scripts/update_custom_field_value.py --prod opportunity Services 'Revision of A' 'Revision of B'
```

**Toggle opportunity discounts:**

Toggle the 'Consultation Fee Credit' value in the Discounts field for opportunities in order to trigger remaining balance recalculation.

```bash
uv run scripts/toggle_opportunity_discounts.py --prod
uv run scripts/toggle_opportunity_discounts.py --prod -n 100 --updated-before-minutes 30
```

**Remove opportunity notes:**

Remove opportunity notes that duplicate lead names or extract lead source values from notes.

```bash
uv run scripts/remove_opportunity_notes.py
```

**Reassign or delete opportunities:**

Bulk reassign opportunities to different users or delete them based on criteria.

```bash
uv run scripts/reassign_or_delete_opportunities.py --prod example@example.com
```

**User reassignment:**

Reassign leads, opportunities, and activities from one user to another.

```bash
uv run scripts/user_reassign.py
```

### Workflow (sequence) management

**Update workflow schedules:**

Enable or disable specific weekdays in workflow schedules for active workflows.

```bash
uv run scripts/update_workflow_schedules.py --prod Mon on
uv run scripts/update_workflow_schedules.py --prod Wed,Thu,Fri off
```

**Change workflow call assignee:**

Reassign workflow call tasks from one user to another or to the lead's Patient Navigator.

```bash
uv run scripts/change_workflow_call_assignee.py
```

**Enroll lead in follow-up workflow:**

Enroll a contact in a follow-up workflow using the date/time from their Lead Qualification form.

```bash
uv run scripts/enroll_lead_in_follow-up_workflow.py
```

**Re-enroll contacts in workflows:**

```bash
uv run scripts/re-enroll_contacts_in_workflows.py
```

**Update the sender for workflow email steps:**

```bash
uv run scripts/change_sequence_sender.py
```

### Data export

Export various data types from Close to CSV/JSON format.

**Export refunded opportunities:**

```bash
uv run scripts/export_refunded_opportunities.py -f 2025-01-01 -t 2025-01-31 --prod
uv run scripts/export_refunded_opportunities.py --won-from 2025-01-01 --prod
```

**Export calls to CSV:**

```bash
uv run scripts/export_calls.py
```

**Export SMS messages:**

```bash
uv run scripts/export_sms.py
```

**Export workflow subscriptions:**

Export workflow (sequence) subscription data for public sharing.

```bash
uv run scripts/export_sequence_subscriptions_public.py
```

**Export workflow configuration and statistics:**

```bash
uv run scripts/export_sequences_data.py
```

**Export custom activity instances:**

```bash
uv run scripts/export_custom_activity_instances.py
```

### Data synchronization

Sync data between Close and external systems.
**Sync Zendesk leads:**

Sync leads and contacts from Zendesk (Base CRM) to Close.

```bash
uv run scripts/sync_zendesk_leads.py --prod
```

**Sync Zendesk records to Close:**

Sync notes and tasks from Zendesk (Base CRM) to Close.

```bash
uv run scripts/sync_zendesk_records_to_close.py --prod
```

**Sync CallTrackingMetrics to BigQuery:**

Sync call log from CallTrackingMetrics to Google BigQuery for analytics.

```bash
uv run scripts/sync_calltrackingmetrics_to_bigquery.py
```

### Reports

Generate analytics and audit reports.

**Generate report of recently deleted leads:**

```bash
uv run scripts/run_leads_deleted_report.py
```

**Generate report of recently merged leads:**

```bash
uv run scripts/run_leads_merged_report.py
```

**Analyze response time metrics for communication activities:**

```bash
uv run scripts/time_to_respond_report.py
```

**Track changes to custom field values over time for auditing:**

```bash
uv run scripts/custom_field_change_report.py
```

### Organization management

**Clone organization:**

Duplicate organization configuration to a new organization (templates, workflows, custom fields).

```bash
uv run scripts/clone_organization.py
```

**Update template and workflow prefix:**

```bash
uv run scripts/update_template_and_workflow_prefix.py
```

**Merge opportunity statuses:**

```bash
uv run scripts/merge_opportunity_statuses.py
```

**Enable or disable webhook subscriptions:**

```bash
uv run scripts/toggle_webhook_subscription.py
```

## Script arguments

Many scripts support common arguments:

- `-p` or `--prod`: Use production environment (defaults to `dev` if not specified)
- `-v` or `--verbose`: Enable detailed logging
- `-d` or `--dry-run`: Preview changes without executing them (when available)

Check individual script help for specific options:

```bash
uv run scripts/<script_name>.py --help
```

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
