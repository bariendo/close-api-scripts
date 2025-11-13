# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Collection of Python scripts for automating operations with the Close CRM API. This is a forked repository on the `additional-scripts` branch with significant divergence from upstream, featuring scripts for lead management, opportunity handling, workflow automation, data synchronization with external systems (Zendesk/Base CRM, CallTrackingMetrics, BigQuery), and reporting.

## Setup & Development

### Environment Setup

```bash
# Install dependencies using uv package manager
uv sync
```

### Authentication

Scripts use macOS Keychain for API key storage (not command-line arguments):

Access keys in scripts via:
```python
from utils.get_api_key import get_api_key

env = 'prod' if args.prod else 'dev'
api_key = get_api_key("api.close.com", f"{env}_admin")
```

### Running Scripts

```bash
# Execute any script with uv
uv run scripts/<script_name>.py [arguments]

# Common flags
-p, --prod      # Use production (defaults to dev)
-v, --verbose   # Enable verbose logging
-d, --dry-run   # Preview changes without executing
```

### Code Quality

```bash
# Format code
uvx ruff format scripts/

# Lint code
uvx ruff check scripts/
```

## Architecture

### Core API Wrappers

**CloseApiWrapper** (`scripts/CloseApiWrapper.py`)
- Extends `closeio_api.Client` with pagination and convenience methods
- **Pagination**: `get_all(endpoint, params)` - automatically handles pagination for any endpoint
- **Async batch operations**: `post_all()`, `put_all()`, `delete_all()` - process multiple requests concurrently with automatic error handling
- **Search API**: `search(query, sort, fields, object_type)` - simplified interface to Close's data search API with automatic pagination
- **Custom fields**: `get_custom_field_id()`, `get_prefixed_custom_field_id()`, `get_custom_field_name_prefixed_id_mapping()` - resolve custom field IDs by name
- **Custom activities**: `get_custom_activity_type_id()`, `get_custom_activity_instances()`, `get_leads_with_custom_activity_instances()` - fetch custom activity data
- **Query builders**: `build_lead_email_query()`, `build_date_range_query()`, `build_has_related_custom_activity_query()` - construct complex search queries
- **Organization helpers**: `get_lead_statuses()`, `get_opportunity_statuses()`, `get_opportunity_pipelines()`
- Use this wrapper for ALL Close API interactions (preferred over raw `closeio_api.Client`)

**ZendeskApiWrapper** (`scripts/ZendeskApiWrapper.py`)
- Extends `basecrm.Client` for Zendesk Sell (Base CRM) API
- **Pagination**: `get_all(object_type, since_date)` - fetches leads, contacts, deals, notes, tasks with date filtering
- **Search API**: `search()`, `filter_contacts()` - async search with pagination
- **Async operations**: Methods use `asyncio.to_thread()` for concurrent fetching

**CallTrackingMetricsAPIClient** (`scripts/CallTrackingMetricsAPIClient.py`)
- Async-only client with `aiohttp` for CallTrackingMetrics API
- Automatic retry logic with rate limit handling (429 responses)
- `get_all()` - paginated fetching following `next_page` links

**BigQueryClientWrapper** (`scripts/BigQueryClientWrapper.py`)
- Wrapper around Google Cloud BigQuery client
- Schema management and JSON data loading
- Used primarily for syncing call data to BigQuery for analytics

### Utility Modules

**`scripts/utils/get_api_key.py`**
- `get_api_key(keychain_item_name, account_name)` - retrieves API keys from macOS Keychain via `security find-internet-password`

**`scripts/utils/formatters.py`**
- `get_full_name(first_name, last_name)` - combines name parts
- `convert_utc_z_to_offset_format(timestamp)` - converts `Z` to `+00:00` for ISO format compatibility
- `format_phone_number(phone_number)` - standardizes phone numbers to E.164 format

**`scripts/utils/get_lead_id.py`**
- Resolves lead identifiers (URLs, IDs) to lead IDs

**`scripts/utils/prompt_user_for_choice.py`**
- Interactive CLI prompts for user selection

### Script Patterns

All scripts follow a standard pattern:

```python
import argparse

from CloseApiWrapper import CloseApiWrapper
from utils.get_api_key import get_api_key

# Argument parsing with -p/--prod flag
parser = argparse.ArgumentParser(description='Script description')
parser.add_argument('-p', '--prod', action='store_true', help='production environment')
parser.add_argument('-v', '--verbose', action='store_true', help='verbose logging')
args = parser.parse_args()

# Environment-based API key retrieval
env = 'prod' if args.prod else 'dev'
api_key = get_api_key("api.close.com", f"{env}_admin")
close = CloseApiWrapper(api_key)

# Main script logic...
```

For async operations:
```python
async def main():
    # Async logic using await close.get_all_async(), close.post_all(), etc.
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

### Environment-Specific Custom Field IDs

Some scripts contain hard-coded custom field IDs that differ between dev and prod:

```python
if env == "dev":
    field_id = "cf_DevFieldId..."
elif env == "prod":
    field_id = "cf_ProdFieldId..."
```

When working with custom fields, prefer using `CloseApiWrapper.get_custom_field_id()` or `get_prefixed_custom_field_id()` to resolve by name dynamically.

### Output Patterns

Scripts commonly write results to `output/` directory (not tracked in git):
```python
with open(f"output/{obj_type}_{action_performed}-{env}.json", "w") as f:
    json.dump(results, f)
```

## Key Script Categories

### Workflow Management
- **Sequence subscriptions** - Close's term for workflow enrollments
- Delete-and-recreate pattern: To modify subscriptions, delete old subscription and create new one (no PUT endpoint)
- Schedule management: Workflows have `schedule.ranges[]` with `weekday` (1-7), `start`, `end` times

### Custom Activities
- Custom activity instances require `custom_activity_type_id`
- Use `get_custom_activity_type_id(name)` to resolve type by name
- Custom field IDs for custom activities use format: `custom_field_schema/activity/{type_id}`

### Opportunity Management
- Opportunities belong to pipelines with statuses
- Status types: `active`, `won`, `lost`
- Loss reasons and details are often stored in custom fields

### Data Synchronization
- **Zendesk sync scripts** - Use both `CloseApiWrapper` and `ZendeskApiWrapper` to map and transfer data between systems
- User ID mapping pattern: Map Zendesk user IDs to Close user IDs via email addresses for consistent ownership
- Custom field mapping: Environment-specific field IDs must be defined for both systems

## Common Patterns

### Searching for leads by email
```python
leads = close.search_leads_by_email("user@example.com")
# Or check existence
if close.email_exists("user@example.com"):
    # ...
```

### Fetching all items with pagination
```python
# Synchronous
items = close.get_all("opportunity", params={"status_type": "won"})

# Asynchronous
items = await close.get_all_async("sequence", params={"_fields": "id,name"})
```

### Batch operations with error handling
```python
endpoint_and_data_list = [
    ("opportunity", {"id": opp_id, "status": "won"})
    for opp_id in opportunity_ids
]
updated, failed = await close.put_all(endpoint_and_data_list, slice_size=5, verbose=True)
```

### Custom field operations
```python
# Get field ID by name
field_id = close.get_custom_field_id("lead", "Patient Navigator")
prefixed_id = close.get_prefixed_custom_field_id("lead", "Patient Navigator")

# Get all field mappings
field_mapping = close.get_custom_field_name_prefixed_id_mapping("opportunity")
loss_reason_field = field_mapping["Loss Reason"]  # Returns "custom.cf_..."
```

## Testing & Production

- **Default environment**: Scripts default to `dev` unless `-p/--prod` flag is provided
- **Dry-run capability**: Some scripts support `--dry-run` to preview changes
- **Verbose logging**: Use `-v/--verbose` to see detailed operation logs
- **Output files**: Check `output/` directory for operation results and debugging data

## Important Notes

- Custom field IDs are environment-specific and hard-coded in some scripts
- Always test in dev environment before running in production
- Close API rate limits apply - async batch operations handle retries automatically via `CloseApiWrapper`
