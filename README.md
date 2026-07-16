# TrackMe for Splunk SOAR

Publisher: TrackMe Limited <br>
Connector Version: 2.0.0 <br>
Product Vendor: TrackMe Limited <br>
Product Name: TrackMe <br>
Minimum Product Version: 7.0.0

This application provides powerful capabilities to interact with TrackMe for Splunk Enterprise & Splunk Cloud

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

### Configuration variables

This table lists the configuration variables required to operate TrackMe for Splunk SOAR. These variables are specified when configuring a TrackMe asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**splunk_url** | required | string | Splunk API URL |
**splunk_token** | required | password | Splunk bearer token |
**verify_ssl** | optional | boolean | Verify Splunk API SSL certificate |
**timeout** | optional | numeric | Per-request timeout in seconds for TrackMe REST calls |
**ingest_event_type** | optional | string | Which TrackMe alert events to ingest on poll: notable, stateful, or both |
**ingest_tenant** | optional | string | Optional comma-separated list of tenant identifiers to restrict ingestion to specific TrackMe tenants (leave empty to ingest all tenants) |
**ingest_lookback** | optional | string | Splunk earliest-time window searched on every poll. Deliberately overlap the poll interval (event_id dedup makes overlap safe, and overlap avoids missing late-arriving events): the default -30m suits a 5 minute poll interval |
**ingest_max_events** | optional | numeric | Maximum total number of events to ingest per poll, across all selected event types (0 for no limit) |

### Supported Actions

[test connectivity](#action-test-connectivity) - test connectivity <br>
[ack_get](#action-ackget) - Get Ack status <br>
[ack_manage](#action-ackmanage) - Manage Ack <br>
[maintenance_status](#action-maintenancestatus) - Check and return the maintenance mode status <br>
[maintenance_enable](#action-maintenanceenable) - Enable global TrackMe maintenance mode <br>
[maintenance_disable](#action-maintenancedisable) - Disable global TrackMe maintenance mode <br>
[tenants_ops_status](#action-tenantsopsstatus) - Get TrackMe Tenants operation status <br>
[remote_accounts_check_connectivity](#action-remoteaccountscheckconnectivity) - Run a connectivity check for TrackMe remote accounts <br>
[ml_outliers_train_models](#action-mloutlierstrainmodels) - Requests Machine Learning models training for a given entity <br>
[ml_outliers_run_monitor](#action-mloutliersrunmonitor) - Runs Machine Learning Outliers monitor process for a given entity <br>
[ml_outliers_reset_models](#action-mloutliersresetmodels) - Reset all ML outliers models for a given entity <br>
[ml_outliers_get_models](#action-mloutliersgetmodels) - Get ML Outliers models information for a given entity <br>
[ml_outliers_add_period_exclusion](#action-mloutliersaddperiodexclusion) - Add an exclusion period to a given ML model <br>
[component_get_entity](#action-componentgetentity) - Get TrackMe entities realtime data and status <br>
[component_manage_entity](#action-componentmanageentity) - This action allows managing TrackMe entities <br>
[logical_group_get_group_for_entity](#action-logicalgroupgetgroupforentity) - Get TrackMe logical groups associations for a given TrackMe entity <br>
[logical_group_manage](#action-logicalgroupmanage) - Manage TrackMe logical groups <br>
[entity toggle monitoring](#action-entity-toggle-monitoring) - Enable or disable monitoring for TrackMe entities <br>
[entity update priority](#action-entity-update-priority) - Update the priority of TrackMe entities <br>
[entity update sla class](#action-entity-update-sla-class) - Update the SLA class of TrackMe entities <br>
[entity reset](#action-entity-reset) - Reset the learned knowledge of TrackMe entities <br>
[entity delete](#action-entity-delete) - Delete TrackMe entities <br>
[entity manage data sampling](#action-entity-manage-data-sampling) - Manage data sampling for TrackMe DSM entities <br>
[entity set false positive](#action-entity-set-false-positive) - Mark a TrackMe entity detection as a false positive <br>
[entity manual score influence](#action-entity-manual-score-influence) - Apply a manual score influence to a TrackMe entity <br>
[entity get status](#action-entity-get-status) - Get the full status of a single TrackMe entity <br>
[entity set maintenance](#action-entity-set-maintenance) - Place TrackMe entities into a timed maintenance window <br>
[entity clear maintenance](#action-entity-clear-maintenance) - Clear the maintenance window of TrackMe entities <br>
[entity list maintenance](#action-entity-list-maintenance) - List active and pending TrackMe entity maintenance windows <br>
[outliers set false positive](#action-outliers-set-false-positive) - Mark an ML outliers detection as a false positive <br>
[outliers bulk action](#action-outliers-bulk-action) - Run a bulk ML outliers action across multiple entities <br>
[ai component health advisor](#action-ai-component-health-advisor) - Start an AI component health advisor job <br>
[ai component health advisor status](#action-ai-component-health-advisor-status) - Get the status of an AI component health advisor job <br>
[ai component health advisor cancel](#action-ai-component-health-advisor-cancel) - Cancel an AI component health advisor job <br>
[ai routine run now](#action-ai-routine-run-now) - Run an AI routine on demand <br>
[ai routine job status](#action-ai-routine-job-status) - Get the status of an AI routine job <br>
[ai routine cancel job](#action-ai-routine-cancel-job) - Cancel an AI routine job <br>
[tenant disable](#action-tenant-disable) - Disable a TrackMe virtual tenant <br>
[tenant enable](#action-tenant-enable) - Enable a TrackMe virtual tenant <br>
[tenant run tracker](#action-tenant-run-tracker) - Run a TrackMe tenant tracker report on demand <br>
[tenant get components status](#action-tenant-get-components-status) - Get the per-component configuration status for a tenant <br>
[tenant get scheduler status](#action-tenant-get-scheduler-status) - Get the scheduled searches completion status <br>
[alerts get tenant](#action-alerts-get-tenant) - Get the current TrackMe alerts for a tenant <br>
[blocklist add](#action-blocklist-add) - Add a TrackMe blocklist rule <br>
[blocklist del](#action-blocklist-del) - Delete TrackMe blocklist rules <br>
[maintenance kdb add record](#action-maintenance-kdb-add-record) - Register a scheduled maintenance knowledge record <br>
[entity create note](#action-entity-create-note) - Create a note attached to a TrackMe entity <br>
[entity assign labels](#action-entity-assign-labels) - Assign labels to a TrackMe entity <br>
[logical group remove object](#action-logical-group-remove-object) - Remove entities from all TrackMe logical groups <br>
[logical group get](#action-logical-group-get) - Get a TrackMe logical group <br>
[logical group delete](#action-logical-group-delete) - Delete a TrackMe logical group <br>
[logical group update members](#action-logical-group-update-members) - Update the members of a TrackMe logical group <br>
[variable delay enable](#action-variable-delay-enable) - Enable variable delay for a TrackMe entity <br>
[variable delay disable](#action-variable-delay-disable) - Disable variable delay for a TrackMe entity <br>
[disruption update min time](#action-disruption-update-min-time) - Update the minimum disruption time for TrackMe entities <br>
[on poll](#action-on-poll) - Ingest TrackMe notable and/or stateful alert events as SOAR containers.

Events are deduplicated by their TrackMe event_id (mapped to the container
source_data_identifier), so overlapping poll windows never create duplicates.
The search window is therefore always the configured `ingest_lookback`
rather than the narrow since-last-poll window SOAR supplies: a deliberately
generous, overlapping window (the default pairs a 5 minute poll interval
with a -30m lookback) means a late-arriving or briefly missed event is still
picked up by a subsequent poll, and dedup absorbs the repeats.

## action: 'test connectivity'

test connectivity

Type: **test** <br>
Read only: **True**

Basic test for app.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ack_get'

Get Ack status

Type: **investigate** <br>
Read only: **True**

This action allows retrieving the acknowledgement status for a given TrackMe entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_category** | required | The object category (splk-dsm, splk-dhm, splk-mhm, splk-flx, splk-wlk) | string | |
**object_list** | required | List of entities, in a comma-separated format. Use * to target all objects | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_category | string | | |
action_result.parameter.object_list | string | | |
action_result.data.\*.object | string | | org_eu_linux:linux_secure |
action_result.data.\*.object_category | string | | splk-dsm |
action_result.data.\*.ack_state | string | | inactive active |
action_result.data.\*.ack_is_enabled | string | | 0 1 |
action_result.data.\*.ack_type | string | | N/A sticky unsticky |
action_result.data.\*.ack_source | string | | user_ack |
action_result.data.\*.ack_comment | string | | API update |
action_result.data.\*.ack_expiration | string | | 0 1712917577.727753 |
action_result.data.\*.ack_expiration_datetime | string | | N/A |
action_result.data.\*.ack_mtime | string | | 1712831177.7277536 |
action_result.data.\*.ack_mtime_datetime | string | | 15 Jul 2026 22:12 |
action_result.data.\*.anomaly_reason | string | | N/A lag_threshold_breached |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ack_manage'

Manage Ack

Type: **generic** <br>
Read only: **False**

This action allows managing Acknowledgments for TrackMe entities, such as enabling, disabling or extending Acknowledgments.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | The tenant Identifier | string | |
**object_category** | required | The object category (splk-dsm, splk-dhm, splk-mhm, splk-flx, splk-wlk) | string | |
**object_list** | required | List of entities, in a comma-separated format. If action=show and not set, will be defined to * to retrieve all Ack records, mandatory for action=enable/disable | string | |
**action** | required | The action to be performed, valid options are: enable | disable | show | string | |
**ack_comment** | optional | Relevant if action=enable but optional, the acknowlegment comment to be added to the records | string | |
**ack_period** | optional | Required if action=enable, the period for the acknowledgment in seconds | string | |
**ack_type** | optional | The type of Ack, valid options are sticky | unsticky, defaults to unsticky if not specified. Unsticky Ack are purged automatically when the entity goes back to a green state, while sticky Ack are purged only when the expiration is reached | string | |
**update_comment** | optional | A comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_category | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.action | string | | |
action_result.parameter.ack_comment | string | | |
action_result.parameter.ack_period | string | | |
action_result.parameter.ack_type | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.process_count | string | | 1 |
action_result.data.\*.success_count | string | | 1 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'maintenance_status'

Check and return the maintenance mode status

Type: **generic** <br>
Read only: **False**

This action allows retrieving the current TrackMe maintenance mode status.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.maintenance | string | | False True |
action_result.data.\*.maintenance_mode | string | | disabled enabled scheduled |
action_result.data.\*.maintenance_message | string | | The maintenance is currently disabled, all alerts from TrackMe are permitted |
action_result.data.\*.maintenance_comment | string | | API update |
action_result.data.\*.tenants_scope | string | | * |
action_result.data.\*.maintenance_countdown | string | | 86358 |
action_result.data.\*.maintenance_mode_start | string | | 1712834220 |
action_result.data.\*.maintenance_mode_end | string | | 1712920620 |
action_result.data.\*.knowledge_record_id | string | | example-record-id |
action_result.data.\*.src_user | string | | svc-trackme |
action_result.data.\*.time_started | string | | 2026-07-15 22:05 |
action_result.data.\*.time_updated | string | | 2026-07-15 22:05 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'maintenance_enable'

Enable global TrackMe maintenance mode

Type: **generic** <br>
Read only: **False**

This action enables the TrackMe global maintenance mode.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**add_knowledge_record** | optional | Boolean value to indicate if a knowledge record should be added to the knowledge database, defaults to true | string | |
**maintenance_duration** | optional | Duration of the maintenance window in seconds, if unspecified and maintenance_mode_end is not specified either, defaults to now plus 24 hours | numeric | |
**maintenance_mode_end** | optional | Date time in epochtime format for the end of the maintenance window, it is overriden by maintenance_duration if specified, defaults to now plus 24 hours if not specified and maintenance_duration is not specified | numeric | |
**maintenance_mode_start** | optional | Date time in epochtime format for the start of the maintennce window, defaults to now if not specified | numeric | |
**time_format** | optional | Time format when submitting start and end maintenance values, defaults to epochtime and can alternatively be set to datestring which expects YYYY-MM-DDTHH:MM as the input format | string | |
**update_comment** | optional | Comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.add_knowledge_record | string | | |
action_result.parameter.maintenance_duration | numeric | | |
action_result.parameter.maintenance_mode_end | numeric | | |
action_result.parameter.maintenance_mode_start | numeric | | |
action_result.parameter.time_format | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.knowledge_record_id | string | | example-record-id |
action_result.data.\*.maintenance | string | | 0 1 |
action_result.data.\*.maintenance_comment | string | | Maintenance enabled for operation ref: xxxx |
action_result.data.\*.maintenance_countdown | string | | 86358 |
action_result.data.\*.maintenance_message | string | | The global maintenance mode is currently enabled, alerts from TrackMe are not permitted |
action_result.data.\*.maintenance_mode | string | | enabled disabled |
action_result.data.\*.maintenance_mode_end | string | | TBC |
action_result.data.\*.maintenance_mode_start | string | | 1712920620 |
action_result.data.\*.src_user | string | | svc-trackme |
action_result.data.\*.time_started | string | | 2024-04-11 12:17 |
action_result.data.\*.time_updated | string | | 2024-04-11 12:32 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'maintenance_disable'

Disable global TrackMe maintenance mode

Type: **generic** <br>
Read only: **False**

This action disable the TrackMe global maintenance mode.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**update_comment** | optional | Comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.epoch_updated | string | | 1712835165 |
action_result.data.\*.maintenance | string | | 0 1 |
action_result.data.\*.maintenance_comment | string | | Maintenance enabled for operation ref: xxxx |
action_result.data.\*.maintenance_message | string | | The global maintenance mode is currently enabled, alerts from TrackMe are not permitted |
action_result.data.\*.maintenance_mode | string | | enabled disabled |
action_result.data.\*.src_user | string | | svc-trackme |
action_result.data.\*.time_updated | string | | 2024-04-11 12:37 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tenants_ops_status'

Get TrackMe Tenants operation status

Type: **generic** <br>
Read only: **False**

This action retrieves the current operational status of the TrackMe tenants.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | optional | Tenant identifier, do not specify a tenant identifier to retrieve the status of all tenants | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.data.\*.tenant_id | string | | mytenant |
action_result.data.\*.status | string | | OPERATIONAL DEGRADED |
action_result.data.\*.overall_ops_pct | string | | 100 |
action_result.data.\*.job_component_register | string | | JSON object with jobs operation details |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remote_accounts_check_connectivity'

Run a connectivity check for TrackMe remote accounts

Type: **generic** <br>
Read only: **False**

This action runs a connectivity check for TrackMe remote accounts which validates both network connectivity and authentication to the remote Splunk deployment.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** | optional | TrackMe remote account name, do not specify any account to verify all configured accounts | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.account | string | | |
action_result.data.\*.status | string | | success failed |
action_result.data.\*.host | string | `host name` `ip` | mysplunk.mydomain.com |
action_result.data.\*.port | string | | 8089 |
action_result.data.\*.account | string | | my_remote_account |
action_result.data.\*.message | string | | remote search connectivity check was successful, service was established |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ml_outliers_train_models'

Requests Machine Learning models training for a given entity

Type: **generic** <br>
Read only: **False**

Programmatically train ML models for a given entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk | string | |
**object** | required | TrackMe entity name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ml_outliers_run_monitor'

Runs Machine Learning Outliers monitor process for a given entity

Type: **generic** <br>
Read only: **False**

This actions runs TrackMe Learning Outliers monitor for a given entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk | string | |
**object** | required | TrackMe entity name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ml_outliers_reset_models'

Reset all ML outliers models for a given entity

Type: **generic** <br>
Read only: **False**

This actions resets ML models rules for a given entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk | string | |
**object** | required | TrackMe entity name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ml_outliers_get_models'

Get ML Outliers models information for a given entity

Type: **generic** <br>
Read only: **False**

This action retrieves the key information for Machine Learning Outliers for a given entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk | string | |
**object** | required | TrackMe entity name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.data.\*.object | string | | org_eu_linux:linux_secure |
action_result.data.\*.object_category | string | | splk-flx |
action_result.data.\*.model_id | string | | model_123456789012345 |
action_result.data.\*.kpi_metric | string | | splk.flx.dcount_hosts |
action_result.data.\*.algorithm | string | | TrackMeNativeDensityFunction |
action_result.data.\*.kpi_span | string | | 10m |
action_result.data.\*.is_disabled | string | | 0 1 |
action_result.data.\*.confidence | string | | normal low high |
action_result.data.\*.confidence_reason | string | | ML has sufficient historical metrics to proceed |
action_result.data.\*.score | string | | 36 |
action_result.data.\*.method_calculation | string | | avg |
action_result.data.\*.density_lowerthreshold | string | | 0.005 |
action_result.data.\*.density_upperthreshold | string | | 0.005 |
action_result.data.\*.alert_lower_breached | string | | 1 0 |
action_result.data.\*.alert_upper_breached | string | | 1 0 |
action_result.data.\*.auto_correct | string | | 1 0 |
action_result.data.\*.period_calculation | string | | -90d |
action_result.data.\*.period_calculation_latest | string | | -1d |
action_result.data.\*.perc_min_lowerbound_deviation | string | | 25.0 |
action_result.data.\*.perc_min_upperbound_deviation | string | | 25.0 |
action_result.data.\*.model_storage | string | | kvstore |
action_result.data.\*.last_exec | string | | 1784153540.9442525 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ml_outliers_add_period_exclusion'

Add an exclusion period to a given ML model

Type: **generic** <br>
Read only: **False**

This action adds a period of exclusion for a given Machine Learning model.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | The component value: dsm/dhm/wlk/flx | string | |
**object** | required | The entity name | string | |
**model_id** | required | The Machine Learning model identifier | string | |
**earliest** | optional | The earliest time of the exclusion window (epoch time, or a relative modifier such as -2d) | string | |
**latest** | optional | The latest time of the exclusion window (epoch time, or a relative modifier such as -1d) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.parameter.model_id | string | | |
action_result.parameter.earliest | string | | |
action_result.parameter.latest | string | | |
action_result.data.\*.results | string | | Exclusion period for ML model was successfully added |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'component_get_entity'

Get TrackMe entities realtime data and status

Type: **generic** <br>
Read only: **False**

This action returns the realtime TrackMe knowledge for a given TrackMe entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk | string | |
**filter_key** | optional | Key identifier, multiple keys can be specified as a comma-separated list of values. (you can use filter_object OR filter_key) | string | |
**filter_object** | optional | Object identifier, multiple objects can be specified as a comma-separated list of values. (you can use filter_object OR filter_key) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.filter_key | string | | |
action_result.parameter.filter_object | string | | |
action_result.data.\*.object | string | | org_eu_linux:linux_secure |
action_result.data.\*.object_category | string | | splk-dsm |
action_result.data.\*.tenant_id | string | | mytenant |
action_result.data.\*.keyid | string | | example-key |
action_result.data.\*.alias | string | | org_eu_linux:linux_secure |
action_result.data.\*.object_state | string | | green orange red |
action_result.data.\*.object_previous_state | string | | orange green |
action_result.data.\*.monitored_state | string | | enabled disabled |
action_result.data.\*.priority | string | | medium high low |
action_result.data.\*.sla_class | string | | silver gold bronze |
action_result.data.\*.sla_is_breached | string | | 0 1 |
action_result.data.\*.sla_message | string | | SLA is not breached, the entity is not in a red state |
action_result.data.\*.score | string | | 48 |
action_result.data.\*.status_message | string | | Entity has an impact score of 48.0 (base score: 0.0) |
action_result.data.\*.anomaly_reason | string | | lag_threshold_breached no_anomalies_detected |
action_result.data.\*.isAnomaly | string | | 0 1 |
action_result.data.\*.isOutlier | string | | 0 1 |
action_result.data.\*.isOutlierReason | string | | Outliers ML breached lower bound for kpi splk.flx.dcount_hosts |
action_result.data.\*.outliers_readiness | string | | True False |
action_result.data.\*.models_in_anomaly | string | | model_123456789012345 |
action_result.data.\*.ack_state | string | | active inactive |
action_result.data.\*.ack_type | string | | sticky unsticky |
action_result.data.\*.is_under_maintenance | string | | 0 1 |
action_result.data.\*.data_index | string | | org_eu_linux |
action_result.data.\*.data_sourcetype | string | | aws:config |
action_result.data.\*.dcount_host | string | | 1 |
action_result.data.\*.last_ingest | string | | 15 Jul 2026 22:18 |
action_result.data.\*.last_time | string | | 15 Jul 2026 19:16 |
action_result.data.\*.lag_summary | string | | 03:05:55 / 03:02:15 |
action_result.data.\*.latest_flip_state | string | | orange green |
action_result.data.\*.notes_count | string | | 1 |
action_result.data.\*.tags | string | | cloud infra |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'component_manage_entity'

This action allows managing TrackMe entities

Type: **correct** <br>
Read only: **False**

This action can be used to manage various aspects of TrackMe entities, such as enabling/disabling, deleting entities or maintaining components specific parameters using the extra_attributes JSON object.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk | string | |
**filter_object** | optional | Object identifier, multiple objects can be specified as a comma-separated list of values. (you can use filter_object OR filter_key) | string | |
**filter_key** | optional | Keyid identifier, multiple keys can be specified as a comma-separated list of values. (you can use filter_object OR filter_key) | string | |
**action** | required | The Action requested, valid options are: enable, disable, delete, manage_dsm_sampling, update_hours_ranges, update_wdays, update_priority, update_lag_policy, update_dcount_host, update_manual_tags | string | |
**extra_attributes** | optional | A JSON object containing attributes for the action. For example, the action update_lag_policy could be asssociated with the following extra_attributes: {"data_max_delay_allowed": 7200, "data_max_lag_allowed": 900} | string | |
**update_comment** | optional | Optional comment for audit purposes | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.filter_object | string | | |
action_result.parameter.filter_key | string | | |
action_result.parameter.action | string | | |
action_result.parameter.extra_attributes | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'logical_group_get_group_for_entity'

Get TrackMe logical groups associations for a given TrackMe entity

Type: **generic** <br>
Read only: **False**

This actions allows to retrieve and return the current associations information for a given TracKme entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**filter_object** | required | The TrackMe entity object identifier to search for and return Logical Groups association information | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.filter_object | string | | |
action_result.data.\*.object_group_name | string | | grp-linux-eu-appxxx |
action_result.data.\*.object_group_key | string | | example-group-key |
action_result.data.\*.object_group_min_green_percent | string | | 50 |
action_result.data.\*.object_group_mtime | string | | 1713009380.1757667 |
action_result.data.\*.object_group_mtime_human | string | | 13 Apr 2024 11:56 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'logical_group_manage'

Manage TrackMe logical groups

Type: **generic** <br>
Read only: **False**

This actions allows to manage TrackMe logical groups and perform association or unassociation of entities with Logical Groups.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**action** | required | The action to be performed on the logical group, valid options: show / associate / unassociate | string | |
**object_group_name** | optional | Logical Group name, required for action associate / unassociate, if performing association the logical group will be created if it does not exist yet | string | |
**object_list** | optional | Required for associate / unassociate, comma-separated list of entities to be associated or unassociated with the Logical Group | string | |
**object_group_min_green_percent** | optional | For action: associate only, minimal green percentage for this group (for action: associate), if not specified, defaults to 50 | numeric | |
**update_comment** | optional | A comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.action | string | | |
action_result.parameter.object_group_name | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.object_group_min_green_percent | numeric | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity toggle monitoring'

Enable or disable monitoring for TrackMe entities

Type: **generic** <br>
Read only: **False**

This action enables or disables monitoring for one or more TrackMe entities in a given component.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**action** | required | The action to perform, valid options are: enable | disable | string | |
**object_list** | optional | Comma-separated list of entity names (use either object_list or keys_list) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values (use either object_list or keys_list) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.action | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity update priority'

Update the priority of TrackMe entities

Type: **generic** <br>
Read only: **False**

This action updates the priority of one or more TrackMe entities in a given component.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**priority** | required | The priority, valid options are: low | medium | high | critical | pending | string | |
**object_list** | optional | Comma-separated list of entity names (use either object_list or keys_list) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values (use either object_list or keys_list) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.priority | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity update sla class'

Update the SLA class of TrackMe entities

Type: **generic** <br>
Read only: **False**

This action updates the SLA class of one or more TrackMe entities in a given component.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**sla_class** | required | The SLA class to apply (tenant-defined, e.g. gold, silver, bronze) | string | |
**object_list** | optional | Comma-separated list of entity names (use either object_list or keys_list) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values (use either object_list or keys_list) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.sla_class | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity reset'

Reset the learned knowledge of TrackMe entities

Type: **generic** <br>
Read only: **False**

This action resets the discovered index/sourcetype (dhm) or metrics (mhm) knowledge for one or more entities. Only the dhm and mhm components support reset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dhm, mhm (reset is only supported for these components) | string | |
**object_list** | optional | Comma-separated list of entity names (use either object_list or keys_list) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values (use either object_list or keys_list) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity delete'

Delete TrackMe entities

Type: **generic** <br>
Read only: **False**

This action deletes one or more TrackMe entities. A temporary deletion allows re-discovery, while a permanent deletion prevents the entity from being re-created.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**deletion_type** | required | The deletion type, valid options are: temporary | permanent | string | |
**object_list** | optional | Comma-separated list of entity names (use either object_list or keys_list) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values (use either object_list or keys_list) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.deletion_type | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity manage data sampling'

Manage data sampling for TrackMe DSM entities

Type: **generic** <br>
Read only: **False**

This action manages the data sampling feature for one or more TrackMe DSM entities (enable, disable, reset or run).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**action** | required | The data sampling action, valid options are: enable | disable | reset | run | string | |
**object_list** | optional | Comma-separated list of entity names (use either object_list or keys_list) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values (use either object_list or keys_list) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.action | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity set false positive'

Mark a TrackMe entity detection as a false positive

Type: **generic** <br>
Read only: **False**

This action generates a negative impact score for a given entity to suppress a false positive detection.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**object_id** | required | The entity identifier (KVstore \_key) | string | |
**object** | optional | The entity display name (optional, for logging) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.object | string | | |
action_result.data.\*.message | string | | False positive score generated successfully |
action_result.data.\*.original_score | string | | 75.0 |
action_result.data.\*.negative_score | string | | -75.0 |
action_result.data.\*.current_score | string | | 0.0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity manual score influence'

Apply a manual score influence to a TrackMe entity

Type: **generic** <br>
Read only: **False**

This action adds or subtracts a manual score delta for a given entity, to force it towards a green or red state.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**object_id** | required | The entity identifier (KVstore \_key) | string | |
**score_type** | required | The score influence type, valid options are: add | subtract | string | |
**score_value** | required | The score value to apply (positive integer) | numeric | |
**object** | optional | The entity display name (optional, for logging) | string | |
**comment** | optional | Optional comment recorded with the score event | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.score_type | string | | |
action_result.parameter.score_value | numeric | | |
action_result.parameter.object | string | | |
action_result.parameter.comment | string | | |
action_result.data.\*.message | string | | Manual score influence applied successfully (add 10) |
action_result.data.\*.applied_score | string | | 10 |
action_result.data.\*.score_type | string | | add subtract |
action_result.data.\*.score_value | string | | 10 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity get status'

Get the full status of a single TrackMe entity

Type: **investigate** <br>
Read only: **True**

This action returns a rich, computed description of a single TrackMe entity (identity, health, score, priority, SLA, maintenance and outliers).

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**object** | optional | The entity display name. Provide either object or object_id (mutually exclusive) | string | |
**object_id** | optional | The entity KVstore \_key. Provide either object or object_id (mutually exclusive) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.parameter.object_id | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity set maintenance'

Place TrackMe entities into a timed maintenance window

Type: **generic** <br>
Read only: **False**

This action places one or more TrackMe entities into a timed maintenance window during which alerting is suppressed.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**keys_list** | required | Comma-separated list of entity KVstore \_key values to place under maintenance | string | |
**maintenance_start_epoch** | required | Maintenance window start: epoch seconds, 'now', a relative offset (+30m/+2h/+1d), or ISO YYYY-MM-DDTHH:MM | string | |
**maintenance_end_epoch** | required | Maintenance window end: same formats as the start; must resolve after the start and in the future | string | |
**maintenance_comment** | optional | Optional comment surfaced in the maintenance status and audit record | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.maintenance_start_epoch | string | | |
action_result.parameter.maintenance_end_epoch | string | | |
action_result.parameter.maintenance_comment | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.response | string | | success |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity clear maintenance'

Clear the maintenance window of TrackMe entities

Type: **generic** <br>
Read only: **False**

This action clears the maintenance window of one or more TrackMe entities, returning them to their computed state.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**keys_list** | required | Comma-separated list of entity KVstore \_key values to clear from maintenance | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.response | string | | success |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity list maintenance'

List active and pending TrackMe entity maintenance windows

Type: **investigate** <br>
Read only: **True**

This action lists the per-entity maintenance windows for a tenant, with an is_active flag computed at request time.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**keys_list** | optional | Optional comma-separated list of entity KVstore \_key values to filter on; omit to return all maintenance records for the tenant | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.keys_list | string | | |
action_result.data.\*.tenant_id | string | | mytenant |
action_result.data.\*.object | string | | org_eu_linux:linux_secure |
action_result.data.\*.object_category | string | | splk-dsm |
action_result.data.\*.component | string | | dsm |
action_result.data.\*.is_active | string | | True False |
action_result.data.\*.maintenance_comment | string | | planned maintenance |
action_result.data.\*.maintenance_start_epoch | string | | 1784150000 |
action_result.data.\*.maintenance_end_epoch | string | | 1784160000 |
action_result.data.\*.src_user | string | | admin |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'outliers set false positive'

Mark an ML outliers detection as a false positive

Type: **generic** <br>
Read only: **False**

This action generates a negative outliers score for a given entity to suppress a false positive ML outliers detection.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**object_id** | required | The entity identifier (KVstore \_key) | string | |
**object** | optional | The entity display name (optional, resolved automatically from object_id if not provided) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.object | string | | |
action_result.data.\*.message | string | | False positive score generated successfully |
action_result.data.\*.original_score | string | | 75.0 |
action_result.data.\*.negative_score | string | | -75.0 |
action_result.data.\*.current_score | string | | 0.0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'outliers bulk action'

Run a bulk ML outliers action across multiple entities

Type: **generic** <br>
Read only: **False**

This action runs a bulk ML outliers operation (enable, disable, mlmonitor, mltrain, reset_status) across multiple entities. The mlmonitor and mltrain actions are dispatched asynchronously as a background Splunk search.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, flx, fqm, wlk | string | |
**action** | required | The bulk action, valid options are: enable, disable, mlmonitor, mltrain, reset_status | string | |
**object_list** | optional | Comma-separated list of entity names. Use either object_list or keys_list (mutually exclusive) | string | |
**keys_list** | optional | Comma-separated list of entity KVstore \_key values. Use either object_list or keys_list (mutually exclusive) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.action | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.process_count | string | | 10 |
action_result.data.\*.success_count | string | | 10 |
action_result.data.\*.failures_count | string | | 0 |
action_result.data.\*.action | string | | mltrain |
action_result.data.\*.job_sid | string | | 1712835612.3451912 |
action_result.data.\*.message | string | | Bulk action dispatched |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ai component health advisor'

Start an AI component health advisor job

Type: **generic** <br>
Read only: **False**

This action starts an asynchronous AI component health advisor job for a given entity and returns a job_id to poll with the status action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: wlk, mhm | string | |
**object** | optional | The entity display name. Provide either object or object_id (mutually exclusive) | string | |
**object_id** | optional | The entity KVstore \_key. Provide either object or object_id (mutually exclusive, object_id preferred) | string | |
**mode** | optional | Advisor mode, valid options are: inspect (default, read-only) or act (applies changes) | string | |
**provider_name** | optional | AI provider stanza to use, defaults to the first configured provider | string | |
**user_context** | optional | Free-text operator instructions passed to the advisor | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.mode | string | | |
action_result.parameter.provider_name | string | | |
action_result.parameter.user_context | string | | |
action_result.data.\*.job_id | string | | example-job-id |
action_result.data.\*.status | string | | running |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ai component health advisor status'

Get the status of an AI component health advisor job

Type: **investigate** <br>
Read only: **True**

This action polls the status of an AI component health advisor job. Terminal states are complete, error and cancelled.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | The AI job identifier returned by the start action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.job_id | string | | |
action_result.data.\*.status | string | | running complete error cancelled |
action_result.data.\*.error | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ai component health advisor cancel'

Cancel an AI component health advisor job

Type: **generic** <br>
Read only: **False**

This action cancels a running AI component health advisor job.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | The AI job identifier returned by the start action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.job_id | string | | |
action_result.data.\*.status | string | | cancelled already_done |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ai routine run now'

Run an AI routine on demand

Type: **generic** <br>
Read only: **False**

This action fires an AI routine on demand and returns a job_id to poll with the job status action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**routine_id** | required | The AI routine identifier to run | string | |
**mode** | optional | Optional mode override, set to inspect to force a read-only dry run (cannot escalate a notify routine to act) | string | |
**force_release** | optional | Set to true to clear a held in-flight lock before launching | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.routine_id | string | | |
action_result.parameter.mode | string | | |
action_result.parameter.force_release | string | | |
action_result.data.\*.routine_id | string | | example-routine-id |
action_result.data.\*.mode | string | | inspect act |
action_result.data.\*.job_id | string | | example-job-id |
action_result.data.\*.status | string | | running |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ai routine job status'

Get the status of an AI routine job

Type: **investigate** <br>
Read only: **True**

This action polls the status of an AI routine job. Terminal states are complete, error and cancelled.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | The AI job identifier returned by the start action | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.job_id | string | | |
action_result.data.\*.status | string | | running complete error cancelled |
action_result.data.\*.error | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ai routine cancel job'

Cancel an AI routine job

Type: **generic** <br>
Read only: **False**

This action cancels a running AI routine job and optionally releases the per-routine in-flight lock.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | The AI routine job identifier to cancel | string | |
**routine_id** | optional | For a run_now fire, the routine identifier, to release the per-routine in-flight lock immediately | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.job_id | string | | |
action_result.parameter.routine_id | string | | |
action_result.data.\*.status | string | | cancelled already_done |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tenant disable'

Disable a TrackMe virtual tenant

Type: **generic** <br>
Read only: **False**

This action disables an entire TrackMe virtual tenant, disabling all of its objects.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**force** | optional | Set to true to handle linked objects even if the tenant record is absent | string | |
**update_comment** | optional | A comment for the update, added to the audit record | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.force | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tenant enable'

Enable a TrackMe virtual tenant

Type: **generic** <br>
Read only: **False**

This action enables an entire TrackMe virtual tenant, enabling all of its objects.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**force** | optional | Set to true to handle linked objects even if the tenant record is absent | string | |
**update_comment** | optional | A comment for the update, added to the audit record | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.force | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tenant run tracker'

Run a TrackMe tenant tracker report on demand

Type: **generic** <br>
Read only: **False**

This action runs a TrackMe tenant tracker savedsearch on demand and returns the resulting rows.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**report** | required | The name of the TrackMe savedsearch/report to run for the tenant | string | |
**earliest** | optional | Optional Splunk earliest time quantifier; defaults to the savedsearch value | string | |
**latest** | optional | Optional Splunk latest time quantifier; defaults to the savedsearch value | string | |
**use_savedsearch_time** | optional | Set to true to use the savedsearch's own earliest/latest time range | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.report | string | | |
action_result.parameter.earliest | string | | |
action_result.parameter.latest | string | | |
action_result.parameter.use_savedsearch_time | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tenant get components status'

Get the per-component configuration status for a tenant

Type: **investigate** <br>
Read only: **True**

This action returns the per-component configuration and enablement status for a TrackMe tenant.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.data.\*.schema_version | string | | 2409 |
action_result.data.\*.component_splk_dsm | string | | 1 0 |
action_result.data.\*.component_splk_dhm | string | | 0 1 |
action_result.data.\*.component_splk_mhm | string | | 0 1 |
action_result.data.\*.component_splk_flx | string | | 0 1 |
action_result.data.\*.component_splk_fqm | string | | 0 1 |
action_result.data.\*.component_splk_wlk | string | | 0 1 |
action_result.data.\*.component_owner | string | | nobody |
action_result.data.\*.mloutliers | string | | 1 0 |
action_result.data.\*.mloutliers_allowlist | string | | dsm,dhm,flx,wlk,fqm |
action_result.data.\*.sampling | string | | 1 0 |
action_result.data.\*.adaptive_delay | string | | 1 0 |
action_result.data.\*.cmdb_lookup | string | | 1 0 |
action_result.data.\*.pagination_mode | string | | local remote |
action_result.data.\*.ui_default_timerange | string | | 24h |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'tenant get scheduler status'

Get the scheduled searches completion status

Type: **investigate** <br>
Read only: **True**

This action returns the scheduled searches completion status over the trailing 24h, optionally filtered to a single tenant.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | optional | Optional tenant identifier to filter on (the endpoint returns all tenants; filtering is applied client-side) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.data.\*.tenant_id | string | | mytenant |
action_result.data.\*.report | string | | TrackMe alert tenant_id:mytenant - stateful-alert |
action_result.data.\*.status | string | | completed skipped |
action_result.data.\*.is_alert | string | | 1 0 |
action_result.data.\*.pct_completed | string | | 100.00 |
action_result.data.\*.count | string | | 288 |
action_result.data.\*.count_completed | string | | 288 |
action_result.data.\*.count_skipped | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'alerts get tenant'

Get the current TrackMe alerts for a tenant

Type: **investigate** <br>
Read only: **True**

This action returns the current TrackMe alerts for a given tenant.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.data.\*.title | string | | TrackMe alert tenant_id:mytenant - stateful-alert |
action_result.data.\*.id | string | | TrackMe%20alert%20tenant_id%3Amytenant%20-%20stateful-alert |
action_result.data.\*.actions | string | | add_to_triggered,trackme_stateful_alert |
action_result.data.\*.disabled | string | | 0 1 |
action_result.data.\*.cron_schedule | string | | 4-59/5 * * * * |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'blocklist add'

Add a TrackMe blocklist rule

Type: **generic** <br>
Read only: **False**

This action adds a blocklist rule so a matching source is no longer tracked by TrackMe.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, wlk, fqm | string | |
**object_category** | required | The entity field to match against (e.g. object, sourcetype, index, alias) | string | |
**object** | required | The value to block (literal or regex; use * as a wildcard) | string | |
**comment** | optional | Optional comment for the blocklist record | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object_category | string | | |
action_result.parameter.object | string | | |
action_result.parameter.comment | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'blocklist del'

Delete TrackMe blocklist rules

Type: **generic** <br>
Read only: **False**

This action deletes one or more TrackMe blocklist rules by their record identifiers.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, wlk, fqm | string | |
**keys_list** | required | Comma-separated list of blocklist record KVstore \_key values to delete | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'maintenance kdb add record'

Register a scheduled maintenance knowledge record

Type: **generic** <br>
Read only: **False**

This action registers a scheduled maintenance window in the TrackMe maintenance knowledge database.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**time_start** | required | Maintenance start time (epoch seconds, or datestring YYYY-MM-DDTHH:MM when time_format=datestring) | string | |
**time_end** | required | Maintenance end time (same format as time_start) | string | |
**reason** | required | The reason for the maintenance window | string | |
**type** | required | The maintenance type, valid options are: planned | unplanned | string | |
**tenants_scope** | optional | Comma-separated list of tenants in scope; defaults to all tenants (\*) | string | |
**no_days_validity** | optional | Number of days the record is valid for; 0 means valid forever | numeric | |
**time_format** | optional | Time format, valid options are: epochtime (default) | datestring | string | |
**add_info** | optional | Optional additional information | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.time_start | string | | |
action_result.parameter.time_end | string | | |
action_result.parameter.reason | string | | |
action_result.parameter.type | string | | |
action_result.parameter.tenants_scope | string | | |
action_result.parameter.no_days_validity | numeric | | |
action_result.parameter.time_format | string | | |
action_result.parameter.add_info | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity create note'

Create a note attached to a TrackMe entity

Type: **generic** <br>
Read only: **False**

This action attaches an investigation note to a TrackMe entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_id** | required | The entity identifier (KVstore \_key) to attach the note to | string | |
**note** | required | The note content (Markdown supported) | string | |
**component** | optional | Optional component (dsm/dhm/mhm/flx/fqm/wlk) for audit scoping | string | |
**validity_days** | optional | Number of days before the note auto-purges; 0 means permanent | numeric | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.note | string | | |
action_result.parameter.component | string | | |
action_result.parameter.validity_days | numeric | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'entity assign labels'

Assign labels to a TrackMe entity

Type: **generic** <br>
Read only: **False**

This action assigns labels to a TrackMe entity. Unknown label names are auto-created. The resolved label set replaces any existing assignment.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_id** | required | The entity identifier (KVstore \_key) | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk | string | |
**label_names** | optional | Comma-separated list of label names to assign (unknown names are auto-created). Provide label_names and/or label_ids | string | |
**label_ids** | optional | Comma-separated list of existing label identifiers to assign. Provide label_ids and/or label_names | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.label_names | string | | |
action_result.parameter.label_ids | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'logical group remove object'

Remove entities from all TrackMe logical groups

Type: **generic** <br>
Read only: **False**

This action removes one or more entities from all of their TrackMe logical groups.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_list** | required | Comma-separated list of entities to remove from all logical groups (supports glob wildcards, but a bare * is refused) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_list | string | | |
action_result.parameter.update_comment | string | | |
action_result.data.\*.action | string | | success |
action_result.data.\*.process_count | string | | 2 |
action_result.data.\*.success_count | string | | 2 |
action_result.data.\*.failures_count | string | | 0 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'logical group get'

Get a TrackMe logical group

Type: **investigate** <br>
Read only: **True**

This action returns a single TrackMe logical group and its members by name.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_group_name** | required | The logical group name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_group_name | string | | |
action_result.data.\*.object_group_name | string | | grp-linux-eu-appxxx |
action_result.data.\*.object_group_key | string | | example-group-key |
action_result.data.\*.object_group_min_green_percent | string | | 50 |
action_result.data.\*.object_group_mtime | string | | 1713009380.1757667 |
action_result.data.\*.object_group_mtime_human | string | | 13 Apr 2024 11:56 |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'logical group delete'

Delete a TrackMe logical group

Type: **generic** <br>
Read only: **False**

This action deletes a TrackMe logical group and all membership related to it.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_group_name** | required | The logical group name to delete (deletes the group and all of its membership) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_group_name | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'logical group update members'

Update the members of a TrackMe logical group

Type: **generic** <br>
Read only: **False**

This action sets the green and red member lists of a TrackMe logical group, identified by its KVstore key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**object_group_key** | required | The logical group KVstore \_key (obtain it from the logical group get action) | string | |
**object_group_members_green** | required | Comma-separated list of entities to set as the group's green members (send an empty value to clear) | string | |
**object_group_members_red** | required | Comma-separated list of entities to set as the group's red members (send an empty value to clear) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.object_group_key | string | | |
action_result.parameter.object_group_members_green | string | | |
action_result.parameter.object_group_members_red | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'variable delay enable'

Enable variable delay for a TrackMe entity

Type: **generic** <br>
Read only: **False**

This action switches a TrackMe entity to an adaptive (variable) delay threshold. A variable delay configuration must already exist for the entity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm | string | |
**object** | optional | The entity display name. Provide either object or object_id (mutually exclusive) | string | |
**object_id** | optional | The entity KVstore \_key. Provide either object or object_id (mutually exclusive) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'variable delay disable'

Disable variable delay for a TrackMe entity

Type: **generic** <br>
Read only: **False**

This action switches a TrackMe entity back to a static delay threshold.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm | string | |
**object** | optional | The entity display name. Provide either object or object_id (mutually exclusive) | string | |
**object_id** | optional | The entity KVstore \_key. Provide either object or object_id (mutually exclusive) | string | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.object | string | | |
action_result.parameter.object_id | string | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disruption update min time'

Update the minimum disruption time for TrackMe entities

Type: **generic** <br>
Read only: **False**

This action tunes the minimum disruption time for one or more TrackMe entities to reduce alert flapping.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** | required | Tenant identifier | string | |
**component** | required | TrackMe component, valid options are: dsm, dhm, mhm, flx, wlk, fqm | string | |
**keys_list** | required | Comma-separated list of entity KVstore \_key values to update | string | |
**disruption_min_time_sec** | required | Minimum disruption time in seconds (0 disables, a positive value sets it) | numeric | |
**update_comment** | optional | A comment for the update, added to the audit record, defaults to: API update | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.tenant_id | string | | |
action_result.parameter.component | string | | |
action_result.parameter.keys_list | string | | |
action_result.parameter.disruption_min_time_sec | numeric | | |
action_result.parameter.update_comment | string | | |
action_result.summary.trackme_response | string | | {"...": "raw TrackMe API response as a JSON string"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'on poll'

Ingest TrackMe notable and/or stateful alert events as SOAR containers.

Events are deduplicated by their TrackMe event_id (mapped to the container
source_data_identifier), so overlapping poll windows never create duplicates.
The search window is therefore always the configured `ingest_lookback`
rather than the narrow since-last-poll window SOAR supplies: a deliberately
generous, overlapping window (the default pairs a 5 minute poll interval
with a -30m lookback) means a late-arriving or briefly missed event is still
picked up by a subsequent poll, and dedup absorbs the repeats.

Type: **ingest** <br>
Read only: **True**

Callback action for the on_poll ingest functionality

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | Start of time range, in epoch time (milliseconds). | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds). | numeric | |
**container_count** | optional | Maximum number of container records to query for. | numeric | |
**artifact_count** | optional | Maximum number of artifact records to query for. | numeric | |
**container_id** | optional | Comma-separated list of container IDs to limit the ingestion to. | string | |

#### Action Output

No Output

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
