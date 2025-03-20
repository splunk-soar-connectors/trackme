# About TrackMe for Splunk Enterprise & Splunk Cloud

TrackMe for Splunk provides visibility and operational excellence to monitor at scale your Splunk data sources availability & quality, scheduled Splunk workload and many more.

For more information about TrackkMe for Splunk, refer to:

- [https://trackme-solutions.com](https://trackme-solutions.com)
- [https://docs.trackme-solutions.com](https://docs.trackme-solutions.com)

# Port Information

This application uses HTTPS to communicate with TrackMe REST API endpoints exposed by Splunkd over HTTPS generally on the port 8089.

# Authentication to Splunkd API

Authentication to Splunkd is performed through the usage of a Splunk bearer token, which is associated with a Splunk user and depending on capabilities and permissions for this user.

For the configuration of the Splunk service account on the Splunk side, and its requirements in terms of capabilities, permissions and resources, consult:

- [https://docs.trackme-solutions.com/latest/admin_guide_configuration.html#service-account-and-permissions](https://docs.trackme-solutions.com/latest/admin_guide_configuration.html#service-account-and-permissions)

# TrackMe REST API

This application leverages the TrackMe REST API endpoints to interact with TrackMe backends, allowing to manage TrackMe entities and behaviours.

For more information about TrackMe REST API, refer to:

- [https://docs.trackme-solutions.com/latest/admin_guide_rest.html](https://docs.trackme-solutions.com/latest/admin_guide_rest.html)

# Additional information about SOAR Actions

### Action: manage entities

This actions allows to manage and modify TrackMe entities and their behaviours, the parameter **action** accepts different values and each action is associated with a set of options to be defined in a JSON format in the parameter **extra_attributes**.\
Some actions are valid for all components, while some others are valid for specific components only.

The following section details the different actions and their associated options.

#### enable (all components)

This action does not require any extra attributes.

#### disable (all components)

This action does not require any extra attributes.

#### delete (all components)

This action supports the following extra attributes:

_temporary entity deletion:_

```
{"deletion_type": "temporary"}
```

_permanent entity deletion:_

```
{"deletion_type": "permanent"}
```

#### manage_dsm_sampling (dsm only)

This action supports the following extra attributes:

_enable DSM sampling:_

```
{"action": "enable"}
```

_disable DSM sampling:_

```
{"action": "disable"}
```

_reset_

```
{"action": "reset"}
```

_run_

```
{"action": "run"}
```

_update_no_records_

```
{"action": "update_no_records", "data_sampling_nr": 100}
```

#### update_hours_ranges (dsm/dhm/flx/cim)

This action supports the following extra attributes:

_using a prefixed mode: all_ranges, manual:08h-to-20h_

```
{"hours_ranges": "all_ranges"}
```

_using a list of hours ranges, where 0 means midnight:_

```
{"hours_ranges": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]}
```

#### update_wdays (dsm/dhm/flx/cim)

This action supports the following extra attributes:

_using a prefixed mode: all_days, manual:monday-to-friday, manual:monday-to-saturday_

```
{"wdays": "all_days"}
```

_using a list of week days ranges, where 0 means Sunday:_

```
{"wdays": [1, 2, 3, 4, 5]}
```

#### update_priority (all components)

This action supports the following extra attributes:

_Update the entity priority: low, medium, high_

```
{"priority": "high"}
```

#### update_lag_policy (dsm/dhm)

This action supports the various extra attributes, all are optionals but one of them must be defined:

- allow_adaptive_delay: true/false
- data_lag_alert_kpis: all_kpis/lag_ingestion_kpi/lag_event_kpi
- data_max_delay_allowed: integer (value in seconds)
- data_max_lag_allowed: integer (value in seconds)
- data_override_lagging_class: true/false
- future_tolerance: integer (negative value in seconds)
- splk_dhm_alerting_policy: (dhm only) The policy, valid options are: global_policy / track_per_sourcetype / track_per_host

_Example:_

```
{
    "allow_adaptive_delay": true, 
    "data_lag_alert_kpis": "all_kpis", 
    "data_max_delay_allowed": 7200, 
    "data_max_lag_allowed": 900, 
    "data_override_lagging_class": true, 
    "future_tolerance": -900
}
```

#### update_dcount_host (dsm only)

This action supports the following extra attributes:

- min_dcount_host: integer (minimum value) or the keyword: "any"
- min_dcount_field: avg_dcount_host_5m / latest_dcount_host_5m / perc95_dcount_host_5m / stdev_dcount_host_5m / global_dcount_host

_Example:_

```
{
    "min_dcount_host": 10, 
    "min_dcount_field": "avg_dcount_host_5m"
}
```

#### update_manual_tags (dsm only)

This action supports the following extra attributes:

- tags_manual: list of manual tags

_Example:_

```
{
    "tags_manual": [
        "tag1",
        "tag2"
    ]
}
```
