[comment]: # "Auto-generated SOAR connector documentation"
# TrackMe for Splunk SOAR
# TrackMe for Splunk SOAR

Publisher: TrackMe Limited  
Connector Version: 1.0.3  
Product Vendor: TrackMe Limited  
Product Name: TrackMe  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.0.2  

This application provides powerful capabilities to interact with TrackMe for Splunk Enterprise & Splunk Cloud

About TrackMe for Splunk Enterprise & Splunk Cloud
==================================================

TrackMe for Splunk provides visibility and operational excellence to monitor at scale your Splunk data sources availability & quality, scheduled Splunk workload and many more.  
  
For more information about TrackkMe for Splunk, refer to:  
- [https://trackme-solutions.com](https://trackme-solutions.com)  
- [https://docs.trackme-solutions.com](https://docs.trackme-solutions.com)

Port Information
================

This application uses HTTPS to communicate with TrackMe REST API endpoints exposed by Splunkd over HTTPS generally on the port 8089.

Authentication to Splunkd API
=============================

Authentication to Splunkd is performed through the usage of a Splunk bearer token, which is associated with a Splunk user and depending on capabilities and permissions for this user.  
  
For the configuration of the Splunk service account on the Splunk side, and its requirements in terms of capabilities, permissions and resources, consult:  
- [https://docs.trackme-solutions.com/latest/admin\_guide\_configuration.html#service-account-and-permissions](https://docs.trackme-solutions.com/latest/admin_guide_configuration.html#service-account-and-permissions)

TrackMe REST API
================

This application leverages the TrackMe REST API endpoints to interact with TrackMe backends, allowing to manage TrackMe entities and behaviours.  
  
For more information about TrackMe REST API, refer to:  
- [https://docs.trackme-solutions.com/latest/admin\_guide\_rest.html](https://docs.trackme-solutions.com/latest/admin_guide_rest.html)

Additional information about SOAR Actions
=========================================

### Action: manage entities

This actions allows to manage and modify TrackMe entities and their behaviours, the parameter **action** accepts different values and each action is associated with a set of options to be defined in a JSON format in the parameter **extra_attributes**.  
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

#### manage\_dsm\_sampling (dsm only)

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
  
_update\_no\_records_  
```
{"action": "update_no_records", "data_sampling_nr": 100}
```

#### update\_hours\_ranges (dsm/dhm/flx/cim)

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

#### update\_lag\_policy (dsm/dhm)

This action supports the various extra attributes, all are optionals but one of them must be defined:  
  
- allow\_adaptive\_delay: true/false  
- data\_lag\_alert\_kpis: all\_kpis/lag\_ingestion\_kpi/lag\_event\_kpi  
- data\_max\_delay_allowed: integer (value in seconds)  
- data\_max\_lag_allowed: integer (value in seconds)  
- data\_override\_lagging_class: true/false  
- future_tolerance: integer (negative value in seconds)  
- splk\_dhm\_alerting\_policy: (dhm only) The policy, valid options are: global\_policy / track\_per\_sourcetype / track\_per\_host  
  
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

#### update\_dcount\_host (dsm only)

This action supports the following extra attributes:  
  
- min\_dcount\_host: integer (minimum value) or the keyword: "any"  
- min\_dcount\_field: avg\_dcount\_host\_5m / latest\_dcount\_host\_5m / perc95\_dcount\_host\_5m / stdev\_dcount\_host\_5m / global\_dcount\_host  
  
_Example:_  
```
{
    "min_dcount_host": 10, 
    "min_dcount_field": "avg_dcount_host_5m"
}
```

#### update\_manual\_tags (dsm only)

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

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a TrackMe asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**splunk_url** |  required  | string | Splunk API URL
**splunk_token** |  required  | password | Splunk bearer token
**verify_ssl** |  optional  | boolean | Verify Splunk API SSL certificate

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[get ack status](#action-get-ack-status) - Get Ack status  
[manage ack](#action-manage-ack) - Manage Ack  
[check maintenance status](#action-check-maintenance-status) - Check and return the maintenance mode status  
[enable maintenance mode](#action-enable-maintenance-mode) - Enable global TrackMe maintenance mode  
[disable maintenance mode](#action-disable-maintenance-mode) - Disable global TrackMe maintenance mode  
[get tenants status](#action-get-tenants-status) - Get TrackMe Tenants operation status  
[check connectivity](#action-check-connectivity) - Run a connectivity check for TrackMe remote accounts  
[request outlier models](#action-request-outlier-models) - Requests Machine Learning models training for a given entity  
[run outliers monitor](#action-run-outliers-monitor) - Runs Machine Learning Outliers monitor process for a given entity  
[reset outliers models](#action-reset-outliers-models) - Reset all ML outliers models for a given entity  
[get outliers models](#action-get-outliers-models) - Get ML Outliers models information for a given entity  
[add exclusion period](#action-add-exclusion-period) - Add an exclusion period to a given ML model  
[get entity data](#action-get-entity-data) - Get TrackMe entities realtime data and status  
[manage entities](#action-manage-entities) - This action allows managing TrackMe entities  
[run smart status](#action-run-smart-status) - Runs the SmartStatus TrackMe action  
[get associations information](#action-get-associations-information) - Get TrackMe logical groups associations for a given TrackMe entity  
[manage logical groups](#action-manage-logical-groups) - Manage TrackMe logical groups  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

Validate the asset configuration for connectivity using the given configuration.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'get ack status'
Get Ack status

Type: **investigate**  
Read only: **True**

This action allows retrieving the acknowledgement status for a given TrackMe entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**object_category** |  required  | The object category (splk-dsm, splk-dhm, splk-mhm, splk-cim, splk-flx, splk-wlk) | string | 
**object_list** |  required  | List of entities, in a comma separated format. Use \* to retrieve all objects, defaults to \* if not specified | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.object_category | string |  |   splk-dsm 
action_result.data.\*.object | string |  |   org_eu_linux:linux_secure 
action_result.data.\*.ack_state | string |  |   active  inactive 
action_result.data.\*.ack_type | string |  |   sticky  unsticky 
action_result.data.\*.ack_comment | string |  |   alert action auto-acknowledgement 
action_result.data.\*.ack_expiration | string |  |   1712917577.727753 
action_result.data.\*.ack_expiration_datetime | string |  |   12 Apr 2024 10:26 
action_result.data.\*.ack_is_enabled | string |  |   1 
action_result.data.\*.ack_mtime | string |  |   1712831177.7277536 
action_result.data.\*.ack_mtime_datetime | string |  |   11 Apr 2024 10:26 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'manage ack'
Manage Ack

Type: **generic**  
Read only: **False**

This action allows managing Acknowledgments for TrackMe entities, such as enabling, disabling or extending Acknowledgments.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | The tenant Identifier | string | 
**object_category** |  required  | The object category (splk-dsm, splk-dhm, splk-mhm, splk-cim, splk-flx, splk-wlk) | string | 
**object_list** |  required  | List of entities, in a comma separated format. If action=show and not set, will be defined to \* to retrieve all Ack records, mandatory for action=enable/disable | string | 
**action** |  required  | The action to be performed, valid options are: enable | disable | show | string | 
**ack_comment** |  optional  | Relevant if action=enable but optional, the acknowlegment comment to be added to the records | string | 
**ack_period** |  optional  | Required if action=enable, the period for the acknowledgment in seconds | string | 
**ack_type** |  optional  | The type of Ack, valid options are sticky | unsticky, defaults to unsticky if not specified. Unsticky Ack are purged automatically when the entity goes back to a green state, while sticky Ack are purged only when the expiration is reached | string | 
**update_comment** |  optional  | A comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.object_category | string |  |   splk-dsm 
action_result.parameter.object_list | string |  |   org_eu_linux:linux_secure 
action_result.parameter.action | string |  |   enable  disable  show 
action_result.parameter.ack_comment | string |  |   alert action auto-acknowledgement 
action_result.parameter.ack_period | string |  |   86400 
action_result.parameter.ack_type | string |  |   sticky  unsticky 
action_result.parameter.update_comment | string |  |   Update from SOAR Automation 
action_result.status | string |  |   success  failed 
action_result.data.\*.process_count | numeric |  |   1 
action_result.data.\*.success_count | numeric |  |   1 
action_result.data.\*.failures_count | numeric |  |   0 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'check maintenance status'
Check and return the maintenance mode status

Type: **generic**  
Read only: **False**

This action allows retrieving the current TrackMe maintenance mode status.

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.knowledge_record_id | string |  |   6617c6d6ce4b42ea1602a5b3 
action_result.data.\*.maintenance | string |  |   0  1 
action_result.data.\*.maintenance_comment | string |  |   Maintenance enabled for operation ref: xxxx 
action_result.data.\*.maintenance_countdown | string |  |   86358 
action_result.data.\*.maintenance_message | string |  |   The global maintenance mode is currently enabled, alerts from TrackMe are not permitted 
action_result.data.\*.maintenance_mode | string |  |   enabled  disabled 
action_result.data.\*.maintenance_mode_end | string |  |   1712920620 
action_result.data.\*.maintenance_mode_start | string |  |   1712834220 
action_result.data.\*.src_user | string |  |   svc-trackme 
action_result.data.\*.time_started | string |  |   2024-04-11 12:17 
action_result.data.\*.time_updated | string |  |   2024-04-11 12:32 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'enable maintenance mode'
Enable global TrackMe maintenance mode

Type: **generic**  
Read only: **False**

This action enables the TrackMe global maintenance mode.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**add_knowledge_record** |  optional  | Boolean value to indicate if a knowledge record should be added to the knowledge database, defaults to true | string | 
**maintenance_duration** |  optional  | Duration of the maintenance window in seconds, if unspecified and maintenance_mode_end is not specified either, defaults to now plus 24 hours | numeric | 
**maintenance_mode_end** |  optional  | Date time in epochtime format for the end of the maintenance window, it is overriden by maintenance_duration if specified, defaults to now plus 24 hours if not specified and maintenance_duration is not specified | numeric | 
**maintenance_mode_start** |  optional  | Date time in epochtime format for the start of the maintennce window, defaults to now if not specified | numeric | 
**time_format** |  optional  | Time format when submitting start and end maintenance values, defaults to epochtime and can alternatively be set to datestring which expects YYYY-MM-DDTHH:MM as the input format | string | 
**update_comment** |  optional  | Comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.knowledge_record_id | string |  |   6617c6d6ce4b42ea1602a5b3 
action_result.data.\*.maintenance | string |  |   0  1 
action_result.data.\*.maintenance_comment | string |  |   Maintenance enabled for operation ref: xxxx 
action_result.data.\*.maintenance_countdown | string |  |   86358 
action_result.data.\*.maintenance_message | string |  |   The global maintenance mode is currently enabled, alerts from TrackMe are not permitted 
action_result.data.\*.maintenance_mode | string |  |   enabled  disabled 
action_result.data.\*.maintenance_mode_end | string |  |   TBC 
action_result.data.\*.maintenance_mode_start | string |  |   1712920620 
action_result.data.\*.src_user | string |  |   svc-trackme 
action_result.data.\*.time_started | string |  |   2024-04-11 12:17 
action_result.data.\*.time_updated | string |  |   2024-04-11 12:32 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'disable maintenance mode'
Disable global TrackMe maintenance mode

Type: **generic**  
Read only: **False**

This action disable the TrackMe global maintenance mode.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**update_comment** |  optional  | Comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.epoch_updated | string |  |   1712835165 
action_result.data.\*.maintenance | string |  |   0  1 
action_result.data.\*.maintenance_comment | string |  |   Maintenance enabled for operation ref: xxxx 
action_result.data.\*.maintenance_message | string |  |   The global maintenance mode is currently enabled, alerts from TrackMe are not permitted 
action_result.data.\*.maintenance_mode | string |  |   enabled  disabled 
action_result.data.\*.src_user | string |  |   svc-trackme 
action_result.data.\*.time_updated | string |  |   2024-04-11 12:37 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get tenants status'
Get TrackMe Tenants operation status

Type: **generic**  
Read only: **False**

This action retrieves the current operational status of the TrackMe tenants.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  optional  | Tenant identifier, do not specify a tenant identifier to retrieve the status of all tenants | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.tenant_id | string |  |   mytenant 
action_result.data.\*.status | string |  |   OPERATIONAL  DEGRADED 
action_result.data.\*.overall_ops_pct | string |  |   100 
action_result.data.\*.job_component_register | string |  |   JSON object with jobs operation details 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'check connectivity'
Run a connectivity check for TrackMe remote accounts

Type: **generic**  
Read only: **False**

This action runs a connectivity check for TrackMe remote accounts which validates both network connectivity and authentication to the remote Splunk deployment.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account** |  optional  | TrackMe remote account name, do not specify any account to verify all configured accounts | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.account | string |  |   my_remote 
action_result.data.\*.status | string |  |   success  failure 
action_result.data.\*.message | string |  |   remote search connectivity check was successful, service was established 
action_result.data.\*.host | string |  |   https://mysplunk.mydomain.com:8089 
action_result.port | string |  |   8089 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'request outlier models'
Requests Machine Learning models training for a given entity

Type: **generic**  
Read only: **False**

Programmatically train ML models for a given entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**object** |  required  | TrackMe entity name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.object | string |  |   org_eu_linux:linux_secure 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'run outliers monitor'
Runs Machine Learning Outliers monitor process for a given entity

Type: **generic**  
Read only: **False**

This actions runs TrackMe Learning Outliers monitor for a given entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**object** |  required  | TrackMe entity name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.object | string |  |   org_eu_linux:linux_secure 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'reset outliers models'
Reset all ML outliers models for a given entity

Type: **generic**  
Read only: **False**

This actions resets ML models rules for a given entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**object** |  required  | TrackMe entity name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.object | string |  |   org_eu_linux:linux_secure 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get outliers models'
Get ML Outliers models information for a given entity

Type: **generic**  
Read only: **False**

This action retrieves the key information for Machine Learning Outliers for a given entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**object** |  required  | TrackMe entity name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.object | string |  |   org_eu_linux:linux_secure 
action_result.status | string |  |   success  failed 
action_result.data.\*.alert_lower_breached | string |  |   1 
action_result.data.\*.alert_upper_breached | string |  |   0 
action_result.data.\*.auto_correct | string |  |   1 
action_result.data.\*.confidence | string |  |   normal 
action_result.data.\*.confidence_reason | string |  |   ML has sufficient historical metrics to proceed (metrics_duration=11+11:40:04, required=6days) 
action_result.data.\*.density_lowerthreshold | string |  |   0.005 
action_result.data.\*.density_upperthreshold | string |  |   0.005 
action_result.data.\*.is_disabled | string |  |   0 
action_result.data.\*.kpi_metric | string |  |   splk.feeds.avg_eventcount_5m 
action_result.data.\*.kpi_span | string |  |   10m 
action_result.data.\*.last_exec | string |  |   1712835612.3451912 
action_result.data.\*.method_calculation | string |  |   avg 
action_result.data.\*.min_value_for_lowerbound_breached | string |  |   0 
action_result.data.\*.min_value_for_upperbound_breached | string |  |   0 
action_result.data.\*.ml_model_filename | string |  |   __mlspl_model_249281506266661.mlmodel 
action_result.data.\*.ml_model_filesize | string |  |   81592 
action_result.data.\*.ml_model_gen_search | string |  |   | mstats avg(trackme.splk.feeds.avg_eventcount_5m) as splk.feeds.avg_eventcount_5m where index="trackme_metrics" tenant_id="secops" object_category="splk-dsm" object="org_eu_linux:linux_secure" by object span="10m" | eval factor=strftime(_time, "%H") | fit DensityFunction splk.feeds.avg_eventcount_5m lower_threshold=0.005 upper_threshold=0.005 into model_249281506266661 by factor | rex field=BoundaryRanges "(-Infinity:(?<LowerBound>[\\d|\\.]\*))|((?<UpperBound>[\\d|\\.]\*):Infinity)" | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ] | fields _time splk.feeds.avg_eventcount_5m LowerBound UpperBound | stats count as metrics_count 
action_result.data.\*.ml_model_lookup_owner | string |  |   splunk-system-user 
action_result.data.\*.ml_model_lookup_share | string |  |   private 
action_result.data.\*.ml_model_render_search | string |  |   | mstats avg(trackme.splk.feeds.avg_eventcount_5m) as splk.feeds.avg_eventcount_5m where index="trackme_metrics" tenant_id="secops" object_category="splk-dsm" object="org_eu_linux:linux_secure" by object span="10m" | eval factor=strftime(_time, "%H") | apply model_249281506266661 | rex field=BoundaryRanges "(-Infinity:(?<LowerBound>[\\d|\\.]\*))|((?<UpperBound>[\\d|\\.]\*):Infinity)" | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ] | fields _time splk.feeds.avg_eventcount_5m LowerBound UpperBound 
action_result.data.\*.ml_model_summary_search | string |  |   | summary model_249281506266661 
action_result.data.\*.model_id | string |  |   model_249281506266661 
action_result.data.\*.perc_min_lowerbound_deviation | string |  |   25.0 
action_result.data.\*.perc_min_upperbound_deviation | string |  |   25.0 
action_result.data.\*.period_calculation | string |  |   -30d 
action_result.data.\*.rules_access_search | string |  |   | inputlookup trackme_dsm_outliers_entity_rules_tenant_secops where _key="9b7a2df12fec5174057fc63e74fefd39" 
action_result.data.\*.time_factor | string |  |   %H 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'add exclusion period'
Add an exclusion period to a given ML model

Type: **generic**  
Read only: **False**

This action adds a period of exclusion for a given Machine Learning model.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | The component value: dsm/dhm/wlk/flx/cim | string | 
**object** |  required  | The entity name | string | 
**model_id** |  required  | The Machine Learning model identifier | string | 
**earliest** |  optional  | The earliest time to be excluded in epoch time format | numeric | 
**latest** |  optional  | The latest time to be excluded in epoch time format | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.object | string |  |   org_eu_linux:linux_secure 
action_result.parameter.model_id | string |  |   model_249281506266661 
action_result.parameter.earliest | numeric |  |   1712610968 
action_result.parameter.latest | numeric |  |   1712697368 
action_result.status | string |  |   success  failed 
action_result.data.\*.results | numeric |  |   Exclusion period for ML model was successfully added 
action_result.data.\*.failures_count | numeric |  |   0 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get entity data'
Get TrackMe entities realtime data and status

Type: **generic**  
Read only: **False**

This action returns the realtime TrackMe knowledge for a given TrackMe entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**filter_key** |  optional  | Key identifier, multiple keys can be specified as a comma separated list of values. (you can use filter_object OR filter_key) | string | 
**filter_object** |  optional  | Object identifier, multiple objects can be specified as a comma separated list of values. (you can use filter_object OR filter_key) | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.data.\*.object | string |  |   org_eu_linux:linux_secure 
action_result.data.\*.keyid | string |  |   9b7a2df12fec5174057fc63e74fefd39 
action_result.data.\*.anomaly_reason | string |  |   lag_threshold_breached  delay_threshold_breached  ml_outliers_detection  data_sampling_anomaly  future_over_tolerance  out_of_monitoring_days  out_of_monitoring_hours  min_hosts_dcount  in_logical_group  status_not_met  skipping_searches_detected  execution_errors_detected  orphan_search_detected  execution_delayed  compliance_failed 
action_result.data.\*.alias | string |  |   org_eu_linux:linux_secure 
action_result.data.\*.priority | string |  |   low  medium  high 
action_result.data.\*.monitored_state | string |  |   enabled  disabled 
action_result.data.\*.ack_state | string |  |   active 
action_result.data.\*.ack_type | string |  |   sticky  unsticky 
action_result.data.\*.isOutlier | numeric |  |   0  1 
action_result.data.\*.isOutlierReason | string |  |   "Outliers ML for kpi="splk.flx.dcount_hosts", model_id="model_205090884007035", LowerBound="478.455" breached with kpi_metric_value="257.975" at time="2024-04-08 14:50:00.000 UTC", pct_decrease="46.08", Outliers ML for kpi="splk.flx.events_count", model_id="model_136982422509193", LowerBound="3697551.595" breached with kpi_metric_value="1758610.25" at time="2024-04-08 14:50:00.000 UTC", pct_decrease="52.44" 
action_result.data.\*.outliers_readiness | string |  |   True  False 
action_result.data.\*.models_in_anomaly | string |  |   model_205090884007035 
action_result.data.\*.isAnomaly | numeric |  |   0  1 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'manage entities'
This action allows managing TrackMe entities

Type: **correct**  
Read only: **False**

This action can be used to manage various aspects of TrackMe entities, such as enabling/disabling, deleting entities or maintaining components specific parameters using the extra_attributes JSON object.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**filter_object** |  optional  | Object identifier, multiple objects can be specified as a comma separated list of values. (you can use filter_object OR filter_key) | string | 
**filter_key** |  optional  | Keyid identifier, multiple keys can be specified as a comma separated list of values. (you can use filter_object OR filter_key) | string | 
**action** |  required  | The Action requested, valid options are: enable, disable, delete, manage_dsm_sampling, update_hours_ranges, update_wdays, update_priority, update_lag_policy, update_dcount_host, update_manual_tags | string | 
**extra_attributes** |  optional  | A JSON object containing attributes for the action. For example, the action update_lag_policy could be asssociated with the following extra_attributes: {"data_max_delay_allowed": 7200, "data_max_lag_allowed": 900} | string | 
**update_comment** |  optional  | Optional comment for audit purposes | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.filter_object | string |  |   org_eu_linux:linux_secure 
action_result.parameter.filter_key | string |  |   9b7a2df12fec5174057fc63e74fefd39 
action_result.parameter.action | string |  |   update_priority 
action_result.parameter.extra_attributes | string |  |   {"priority": "high"} 
action_result.parameter.update_comment | string |  |   Update from SOAR Automation 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'run smart status'
Runs the SmartStatus TrackMe action

Type: **generic**  
Read only: **False**

The SmartStatus TrackMe action performs automated investigations in Splunk depending on the current status of the entity, and returns the key information for the entity anomalies detected.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**component** |  required  | TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk, cim | string | 
**object** |  required  | TrackMe entity name | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.component | string |  |   dsm 
action_result.parameter.object | string |  |   org_eu_linux:linux_secure 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get associations information'
Get TrackMe logical groups associations for a given TrackMe entity

Type: **generic**  
Read only: **False**

This actions allows to retrieve and return the current associations information for a given TracKme entity.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**filter_object** |  required  | The TrackMe entity object identifier to search for and return Logical Groups association information | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.filter_object | string |  |   key:host|linux-srv-eu1 
action_result.data.\*.object_group_name | numeric |  |   grp-linux-eu-appxxx 
action_result.data.\*.object_group_key | numeric |  |   661a678627481938da080cb2 
action_result.data.\*.object_group_members | numeric |  |   linux-srv-eu1  linux-srv-eu2 
action_result.data.\*.object_group_mtime | numeric |  |   1713009380.1757667 
action_result.data.\*.object_group_mtime_human | numeric |  |   13 Apr 2024 11:56 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'manage logical groups'
Manage TrackMe logical groups

Type: **generic**  
Read only: **False**

This actions allows to manage TrackMe logical groups and perform association or unassociation of entities with Logical Groups.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**tenant_id** |  required  | Tenant identifier | string | 
**action** |  required  | The action to be performed on the logical group, valid options: show / associate / unassociate | string | 
**object_group_name** |  optional  | Logical Group name, required for action associate / unassociate, if performing association the logical group will be created if it does not exist yet | string | 
**object_list** |  optional  | Required for associate / unassociate, comma separated list of entities to be associated or unassociated with the Logical Group | string | 
**object_group_min_green_percent** |  optional  | For action: associate only, minimal green percentage for this group (for action: associate), if not specified, defaults to 50 | numeric | 
**update_comment** |  optional  | A comment for the update, comments are added to the audit record, if unset will be defined to: API update | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tenant_id | string |  |   mytenant 
action_result.parameter.action | string |  |   associate 
action_result.parameter.object_group_name | string |  |   grp-linux-eu-appxxx 
action_result.parameter.object_list | string |  |   linux-srv-eu1,linux-srv-eu2 
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  