# About TrackMe for Splunk Enterprise & Splunk Cloud

TrackMe for Splunk provides visibility and operational excellence to monitor at scale your Splunk data sources availability & quality, scheduled Splunk workload, metrics, and many more.

This application allows Splunk SOAR to interact with the TrackMe REST API, so you can automate TrackMe operations from playbooks: acknowledge and remediate entities, manage monitoring, maintenance windows, priorities and SLAs, run Machine Learning Outliers operations, manage tenants, and trigger TrackMe's AI advisors.

For more information about TrackMe for Splunk, refer to:

- [https://trackme-solutions.com](https://trackme-solutions.com)
- [https://docs.trackme-solutions.com](https://docs.trackme-solutions.com)

# Port Information

This application uses HTTPS to communicate with the TrackMe REST API endpoints exposed by Splunkd over HTTPS, generally on port 8089.

# Authentication to Splunkd API

Authentication to Splunkd is performed using a Splunk bearer token, which is associated with a Splunk user whose capabilities and permissions determine what the connector is allowed to do.

TrackMe REST endpoints are grouped into privilege tiers — read (user), write (power) and admin. The service account behind the bearer token must hold the TrackMe capability that matches the actions you intend to run (for example, write/admin actions such as managing entities, maintenance or tenants require the corresponding power/admin capabilities).

For the configuration of the Splunk service account, and its requirements in terms of capabilities, permissions and resources, consult:

- [https://docs.trackme-solutions.com/latest/admin_guide_configuration.html#service-account-and-permissions](https://docs.trackme-solutions.com/latest/admin_guide_configuration.html#service-account-and-permissions)

# Asset Configuration

Configure a TrackMe asset with the following parameters:

- **Splunk API URL** (`splunk_url`): the Splunkd management URL of your TrackMe deployment, e.g. `https://mysplunk.mydomain.com:8089`.
- **Splunk bearer token** (`splunk_token`): the bearer token of the TrackMe service account (stored as a sensitive value).
- **Verify Splunk API SSL certificate** (`verify_ssl`): whether to verify the Splunkd SSL certificate (disabled by default; enable it when Splunkd presents a certificate trusted by SOAR).

Use the **test connectivity** action to validate the URL, token and network path before running any other action.

# TrackMe REST API

This application leverages the TrackMe REST API endpoints to interact with TrackMe backends, allowing you to manage TrackMe entities and behaviours.

For more information about the TrackMe REST API, refer to:

- [https://docs.trackme-solutions.com/latest/admin_guide_rest.html](https://docs.trackme-solutions.com/latest/admin_guide_rest.html)

# TrackMe concepts used by the actions

Understanding a few TrackMe concepts makes the action parameters straightforward:

- **Tenant** (`tenant_id`): TrackMe is multi-tenant. Almost every action targets a specific tenant.
- **Component**: the TrackMe monitoring domain. Valid components are:
  - `dsm` — Data Source Monitoring (feeds)
  - `dhm` — Data Host Monitoring (hosts)
  - `mhm` — Metric Host Monitoring (metrics)
  - `flx` — Flex Objects (hybrid / custom trackers)
  - `fqm` — Field Quality Management
  - `wlk` — Splunk Workload (scheduled searches)
  - Some actions also accept the `splk-<component>` form for the `object_category` parameter (e.g. `splk-dsm`).
- **Entity**: a monitored object within a component. Entities are addressed either by their **name** (the `object` value) or by their KVstore key (`object_id` / a value in `keys_list`).
- **Entity targeting**: bulk actions accept **either** `object_list` (comma-separated entity names) **or** `keys_list` (comma-separated KVstore `_key` values) — provide exactly one. Where an action targets a single entity it takes `object_id` (and optionally `object` for readability). The one exception is the original **manage entities** action, which keeps its own `filter_object` / `filter_key` names for backward compatibility.

# Action groups

- **Acknowledgements**: get / manage acknowledgements.
- **Maintenance**: global maintenance (status / enable / disable) and per-entity maintenance windows (set / clear / list).
- **Entities**: get realtime data, get full status, toggle monitoring, update priority / SLA class, reset, delete, manage data sampling, set false positive, manual score influence, create notes, assign labels.
- **Machine Learning Outliers**: get models, train, monitor, reset, add exclusion period, set false positive, bulk actions.
- **Logical groups**: get associations, manage groups, remove objects from groups.
- **Tenants & operations**: enable / disable tenants, run trackers, components status, scheduler status, get alerts, blocklist, disruption tuning, variable delay, maintenance knowledge records.
- **AI advisors & routines**: asynchronous AI component-health advisors, and on-demand AI routines.

# Additional information about SOAR Actions

## Action: manage entities

This action manages and modifies TrackMe entities and their behaviours. The parameter **action** accepts several values, and most values are associated with a set of options provided as a JSON object in the parameter **extra_attributes**. Some actions apply to all components, while others apply to specific components only.

Entities are targeted with **filter_object** (entity names) or **filter_key** (KVstore keys) — provide exactly one.

> **Note:** `filter_object` / `filter_key` are this action's original parameter names and are kept unchanged so that existing playbooks keep working. They are specific to **manage entities**: the newer per-component actions (**entity toggle monitoring**, **entity update priority**, **entity delete** and so on) use `object_list` / `keys_list` for the same purpose, as described under *TrackMe concepts used by the actions*. Sending `object_list` to **manage entities**, or `filter_object` to a newer action, will fail.

The following section details the actions and their associated options.

### enable (all components)

Enables monitoring. Does not require any extra attributes.

### disable (all components)

Disables monitoring. Does not require any extra attributes.

### delete (all components)

Supports the following extra attributes:

_temporary entity deletion (can be re-discovered):_

```json
{"deletion_type": "temporary"}
```

_permanent entity deletion (prevented from being re-created):_

```json
{"deletion_type": "permanent"}
```

### manage_dsm_sampling (dsm only)

Manages the DSM data sampling feature. Supported values:

```json
{"action": "enable"}
{"action": "disable"}
{"action": "reset"}
{"action": "run"}
```

> Tip: the dedicated **entity manage data sampling** action provides the same enable/disable/reset/run capability as a first-class action.

### update_hours_ranges (dsm/dhm/mhm/flx/wlk/fqm)

Supports the following extra attributes:

_using a prefixed mode: all_ranges, manual:08h-to-20h_

```json
{"hours_ranges": "all_ranges"}
```

_using a list of hours ranges, where 0 means midnight:_

```json
{"hours_ranges": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]}
```

### update_wdays (dsm/dhm/mhm/flx/wlk/fqm)

Supports the following extra attributes:

_using a prefixed mode: all_days, manual:monday-to-friday, manual:monday-to-saturday_

```json
{"wdays": "all_days"}
```

_using a list of week days, where 0 means Sunday:_

```json
{"wdays": [1, 2, 3, 4, 5]}
```

### update_priority (all components)

Supports the following extra attributes (valid priorities: low, medium, high, critical, pending):

```json
{"priority": "high"}
```

### update_lag_policy (dsm/dhm)

Supports the following extra attributes; all are optional but at least one must be defined:

- allow_adaptive_delay: true/false
- data_lag_alert_kpis: all_kpis/lag_ingestion_kpi/lag_event_kpi
- data_max_delay_allowed: integer (value in seconds)
- data_max_lag_allowed: integer (value in seconds)
- data_override_lagging_class: true/false
- future_tolerance: integer (value in seconds)
- splk_dhm_alerting_policy: (dhm only) all_kpis / lag_ingestion_kpi / lag_event_kpi

_Example:_

```json
{
    "allow_adaptive_delay": true,
    "data_lag_alert_kpis": "all_kpis",
    "data_max_delay_allowed": 7200,
    "data_max_lag_allowed": 900,
    "data_override_lagging_class": true,
    "future_tolerance": 900
}
```

### update_dcount_host (dsm only)

Supports the following extra attributes:

- min_dcount_host: integer (minimum value) or the keyword "any"
- min_dcount_field: avg_dcount_host_5m / latest_dcount_host_5m / perc95_dcount_host_5m / stdev_dcount_host_5m / global_dcount_host

_Example:_

```json
{
    "min_dcount_host": 10,
    "min_dcount_field": "avg_dcount_host_5m"
}
```

### update_manual_tags (dsm only)

Supports the following extra attributes:

- tags_manual: a comma-separated string of manual tags (send an empty string to purge all manual tags)

_Example:_

```json
{"tags_manual": "tag1,tag2"}
```

## AI advisors & routines (asynchronous)

The AI advisor and routine actions are **asynchronous**: a start action launches an AI job and returns a **job_id**, which you then poll with the matching status action until the job reaches a terminal state (`complete`, `error` or `cancelled`). A cancel action is also provided. Both families (component health advisor, AI routine) share this pattern:

1. **Start** — e.g. **ai component health advisor** / **ai routine run now**. Returns `job_id` and `status: running`.
1. **Poll status** — e.g. **ai component health advisor status** — pass the `job_id`. While `status` is `running`, keep polling; when it is `complete`, the `result` field holds the advisor output; `error` is populated on failure.
1. **Cancel** (optional) — e.g. **ai component health advisor cancel** — pass the `job_id` to stop a running job.

Notes:

- Advisor runs can take up to a few minutes; size your playbook polling/timeout accordingly.
- The **provider_name** parameter selects the configured AI provider account on TrackMe; if omitted, the first configured provider is used.
- The **ai component health advisor** applies to the `wlk` and `mhm` components; **ai routine run now** fires a predefined AI routine by `routine_id`.
- TrackMe's AI concierge advisor is intentionally not exposed as an action: it is an interactive surface for the TrackMe UI and its AI chat, taking free-text user intent and returning proposals for a person to approve, so it does not map onto playbook automation.

A typical playbook pattern is: start the advisor, then loop on the status action (with a short delay) until the status is no longer `running`, and act on the returned `result`.

## Ingestion (on poll)

The connector can ingest TrackMe alert-surface events as SOAR containers. TrackMe generates two event types, each uniquely identified by an `event_id`:

- **Notable events** (`index=trackme_notable sourcetype=trackme:notable`) — ES-style notables.
- **Stateful events** (`index=trackme_summary sourcetype="trackme:stateful_alerts"`) — the stateful new/ongoing/closed alerting path.

On each poll the connector runs a Splunk search (using the asset's Splunk bearer token) over the selected event type(s), and creates one container per event with the event fields on an artifact. Each container's `source_data_identifier` is set to the event's `event_id`, so SOAR deduplicates natively — a repeated `event_id` updates the existing container instead of creating a duplicate, and overlapping poll windows are safe.

Ingestion is controlled by these asset options:

- **ingest_event_type**: `notable`, `stateful`, or `both` (default).
- **ingest_tenant**: optional comma-separated list of tenant identifiers to restrict ingestion to specific tenants (leave empty to ingest all tenants).
- **ingest_lookback**: the Splunk earliest-time window searched on every poll (default `-30m`).
- **ingest_max_events**: maximum total events per poll, across all selected event types.

Ingested containers take the asset's own ingest label, set under **Ingest Settings → Label to apply to objects from this source**.

### Recommended polling configuration

Every poll searches the full `ingest_lookback` window rather than a narrow
since-last-poll window. This is a deliberate trade of load for reliability:
`event_id` dedup means a repeated event never creates a duplicate container, so
overlapping the window makes it far less likely that a late-arriving or briefly
missed event is dropped. It is not free — each poll re-runs the whole lookback
search and the connector re-processes the rows it already saw, so a wider window
or a shorter interval costs more Splunk search and connector work.

Configure the asset's ingestion settings to poll **every 5 minutes** and leave
`ingest_lookback` at the default **`-30m`**. A 30-minute window polled every 5
minutes gives each event several opportunities to be picked up, with the repeats
absorbed by dedup. Note that `ingest_max_events` caps how many events a single
poll ingests, so a poll that hits the cap will not reach every event in the
window — raise the cap (or set it to `0` for no limit) in high-volume
environments. If your events arrive late, widen `ingest_lookback` rather than
lengthening the poll interval, and size the cap to match the volume the wider
window returns.

Configure the asset's ingest settings (polling interval, label) as usual, then use **poll now** to validate ingestion.
