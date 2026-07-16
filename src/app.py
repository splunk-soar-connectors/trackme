# Copyright (c) TrackMe Limited, 2024-2026
#
# TrackMe for Splunk SOAR — SDK application.
#
# This connector interacts with the TrackMe REST API endpoints exposed by
# Splunkd over HTTPS. It is the splunk-soar-sdk port of the legacy
# BaseConnector app; the legacy actions are preserved with identical action
# names, identifiers, parameters and output datapaths so that existing customer
# playbooks keep working unchanged.
#
# NOTE: the legacy action *names* are the snake_case identifiers (ack_get,
# component_manage_entity, ...) because that is what the legacy manifest
# shipped. SOAR playbooks dispatch phantom.act(action=...) on the name, so
# these must never be prettified — doing so breaks every existing playbook.

import contextlib
import json
from collections.abc import Iterator
from math import isfinite

from pydantic import ConfigDict, model_validator
from soar_sdk.abstract import SOARClient
from soar_sdk.action_results import ActionOutput, OutputField
from soar_sdk.app import App
from soar_sdk.asset import AssetField, BaseAsset, FieldCategory
from soar_sdk.exceptions import ActionFailure, AssetMisconfiguration
from soar_sdk.logging import getLogger
from soar_sdk.meta.app import AppContributor
from soar_sdk.models.container import Container
from soar_sdk.params import OnPollParams, Param, Params

from .trackme_rest_client import trackme_rest_call, trackme_splunk_search


logger = getLogger()


# Maps a TrackMe component to the endpoint verb prefix used by its write API,
# e.g. component "dsm" -> "/services/trackme/v2/splk_dsm/write/ds_monitoring".
_COMPONENT_PREFIX_ALL = {
    "dsm": "ds",
    "dhm": "dh",
    "mhm": "mh",
    "flx": "flx",
    "fqm": "fqm",
    "wlk": "wlk",
}

# The legacy component_manage_entity action predates fqm and only ever routed
# these five components; the newer per-component actions accept all six.
_LEGACY_COMPONENTS = ("dsm", "dhm", "mhm", "wlk", "flx")


def _csv_to_list(value: str) -> list:
    return [v.strip() for v in value.split(",") if v.strip()]


def _int_param(value: float | None, name: str) -> int | None:
    """Coerce a SOAR numeric parameter to the whole number TrackMe expects.

    The SDK offers no integer parameter type, so a user entering ``1`` arrives
    as ``1.0`` and would be serialised onto the wire as ``1.0``. TrackMe rejects
    that for integer fields (``no_days_validity`` is a confirmed example), and
    is only incidentally lenient elsewhere. Fractional input is rejected rather
    than silently truncated, since every caller here means a whole number of
    seconds, days, percent or epoch seconds.
    """
    if value is None:
        return None
    if not isfinite(value) or value != int(value):
        raise ActionFailure(f"{name} must be a whole number, but got: {value}")
    return int(value)


def _result_rows(response: object, key: str = "query_results") -> list:
    """Return the list of result rows from a TrackMe response.

    Accepts a bare list (returned as-is), or a dict from which the rows are
    read under ``key``; anything else yields an empty list. This keeps the
    row-yielding actions from crashing when an endpoint returns an unexpected
    shape (e.g. a dict where a list was expected).
    """
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        rows = response.get(key)
        return rows if isinstance(rows, list) else []
    return []


class TrackMeOutput(ActionOutput):
    """Base output that documents key datapaths while passing the full TrackMe
    response through unchanged.

    The legacy connector added the raw TrackMe API response as the action data
    with no type validation. ``extra="allow"`` preserves any undeclared fields a
    playbook might read (in their native types), while the validator below coerces
    the values of *declared* fields to strings so the SDK's typed validation can
    never reject a real TrackMe response (which may contain nulls, numbers, or
    "N/A" strings where a schema example suggested otherwise). Declared fields are
    therefore typed ``str | None`` and exist purely to document datapaths.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _coerce_declared_fields_to_str(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        coerced = dict(data)
        for name, field in cls.model_fields.items():
            for key in (name, field.alias):
                if key and key in coerced:
                    value = coerced[key]
                    if value is not None and not isinstance(value, str):
                        coerced[key] = (
                            json.dumps(value)
                            if isinstance(value, list | dict)
                            else str(value)
                        )
        return coerced


class TrackMeGenericOutput(TrackMeOutput):
    """Passthrough output for actions whose response schema is free-form."""


class TrackMeResponseSummary(ActionOutput):
    """Action summary preserved from the legacy connector (``trackme_response``)."""

    trackme_response: str | None = OutputField(
        example_values=['{"...": "raw TrackMe API response as a JSON string"}']
    )


class Asset(BaseAsset):
    splunk_url: str = AssetField(
        description="Splunk API URL", default="https://mysplunk.mydomain.com:8089"
    )
    splunk_token: str = AssetField(description="Splunk bearer token", sensitive=True)
    verify_ssl: bool | None = AssetField(
        description="Verify Splunk API SSL certificate", default=False
    )
    timeout: float | None = AssetField(
        description="Per-request timeout in seconds for TrackMe REST calls",
        default=300,
    )
    ingest_event_type: str | None = AssetField(
        description="Which TrackMe alert events to ingest on poll: notable, stateful, or both",
        default="both",
        value_list=["both", "notable", "stateful"],
        category=FieldCategory.INGEST,
    )
    ingest_tenant: str | None = AssetField(
        description="Optional comma-separated list of tenant identifiers to restrict ingestion to specific TrackMe tenants (leave empty to ingest all tenants)",
        category=FieldCategory.INGEST,
    )
    ingest_lookback: str | None = AssetField(
        description="Splunk earliest-time window searched on every poll. Deliberately overlap the poll interval (event_id dedup makes overlap safe, and overlap avoids missing late-arriving events): the default -30m suits a 5 minute poll interval",
        default="-30m",
        category=FieldCategory.INGEST,
    )
    ingest_max_events: float | None = AssetField(
        description="Maximum total number of events to ingest per poll, across all selected event types (0 for no limit)",
        default=1000,
        category=FieldCategory.INGEST,
    )


app = App(
    name="TrackMe for Splunk SOAR",
    app_type="siem",
    logo="logo_trackme.svg",
    logo_dark="logo_trackme_dark.svg",
    product_vendor="TrackMe Limited",
    product_name="TrackMe",
    publisher="TrackMe Limited",
    appid="dce19fec-9c3e-4bec-914e-8230ac80a417",
    fips_compliant=False,
    encrypt_cache_state=True,
    encrypt_ingest_state=True,
    asset_cls=Asset,
)

# The SDK App() constructor does not expose the manifest "contributors" field;
# inject it via app_meta_info, which the manifest builder copies onto the app
# metadata (see soar_sdk manifests processor).
app.app_meta_info["contributors"] = [AppContributor(name="Guilhem Marchand")]


@app.test_connectivity()
def test_connectivity(soar: SOARClient, asset: Asset) -> None:
    soar.set_message("Connecting to endpoint")
    trackme_rest_call(
        asset,
        "/services/trackme/v2/vtenants/show_tenants",
        method="get",
    )
    logger.progress("Test Connectivity Passed")


class GetAckStatusParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_category: str = Param(
        description="The object category (splk-dsm, splk-dhm, splk-mhm, splk-flx, splk-wlk)"
    )
    object_list: str = Param(
        description="List of entities, in a comma-separated format. Use * to target all objects"
    )


class GetAckStatusOutput(TrackMeOutput):
    object: str | None = OutputField(
        example_values=["org_eu_linux:linux_secure"], column_name="Object"
    )
    object_category: str | None = OutputField(example_values=["splk-dsm"])
    ack_state: str | None = OutputField(
        example_values=["inactive", "active"], column_name="Ack State"
    )
    ack_is_enabled: str | None = OutputField(
        example_values=["0", "1"], column_name="Enabled"
    )
    ack_type: str | None = OutputField(example_values=["N/A", "sticky", "unsticky"])
    ack_source: str | None = OutputField(example_values=["user_ack"])
    ack_comment: str | None = OutputField(example_values=["API update"])
    ack_expiration: str | None = OutputField(example_values=["0", "1712917577.727753"])
    ack_expiration_datetime: str | None = OutputField(
        example_values=["N/A"], column_name="Expires"
    )
    ack_mtime: str | None = OutputField(example_values=["1712831177.7277536"])
    ack_mtime_datetime: str | None = OutputField(example_values=["15 Jul 2026 22:12"])
    anomaly_reason: str | None = OutputField(
        example_values=["N/A", "lag_threshold_breached"]
    )


@app.action(
    name="ack_get",
    description="Get Ack status",
    action_type="investigate",
    verbose="This action allows retrieving the acknowledgement status for a given TrackMe entity.",
    summary_type=TrackMeResponseSummary,
)
def ack_get(
    params: GetAckStatusParams, soar: SOARClient, asset: Asset
) -> GetAckStatusOutput:
    body = {
        "tenant_id": params.tenant_id,
        "object_category": params.object_category,
        "object_list": params.object_list,
    }

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ack/get_ack_for_object",
        method="post",
        data=json.dumps(body),
    )

    # The endpoint returns a list of ack records. An empty list is the
    # documented "no acknowledgement" case -> report inactive. Any other shape
    # is a malformed response and must surface as an error, not a false status.
    if not isinstance(response, list):
        raise ActionFailure(
            f"Unexpected acknowledgement response shape: {type(response).__name__}"
        )
    if response:
        ack_response = response[0]
    else:
        ack_response = {
            "ack_comment": "N/A",
            "ack_expiration": "N/A",
            "ack_expiration_datetime": "N/A",
            "ack_is_enabled": 0,
            "ack_mtime": "N/A",
            "ack_mtime_datetime": "N/A",
            "ack_state": "inactive",
            "ack_type": "N/A",
            "object": params.object_list,
            "object_category": params.object_category,
        }

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(ack_response)))
    logger.progress("Ack get successful")
    return GetAckStatusOutput(**ack_response)


class ManageAckParams(Params):
    tenant_id: str = Param(description="The tenant Identifier")
    object_category: str = Param(
        description="The object category (splk-dsm, splk-dhm, splk-mhm, splk-flx, splk-wlk)"
    )
    object_list: str = Param(
        description="List of entities, in a comma-separated format. If action=show and not set, will be defined to * to retrieve all Ack records, mandatory for action=enable/disable"
    )
    action: str = Param(
        description="The action to be performed, valid options are: enable | disable | show"
    )
    ack_comment: str | None = Param(
        description="Relevant if action=enable but optional, the acknowlegment comment to be added to the records"
    )
    ack_period: str | None = Param(
        description="Required if action=enable, the period for the acknowledgment in seconds"
    )
    ack_type: str | None = Param(
        description="The type of Ack, valid options are sticky | unsticky, defaults to unsticky if not specified. Unsticky Ack are purged automatically when the entity goes back to a green state, while sticky Ack are purged only when the expiration is reached"
    )
    update_comment: str | None = Param(
        description="A comment for the update, comments are added to the audit record, if unset will be defined to: API update"
    )


class ManageAckOutput(TrackMeOutput):
    process_count: str | None = OutputField(example_values=[1])
    success_count: str | None = OutputField(example_values=[1])
    failures_count: str | None = OutputField(example_values=[0])


@app.action(
    name="ack_manage",
    description="Manage Ack",
    action_type="generic",
    read_only=False,
    verbose="This action allows managing Acknowledgments for TrackMe entities, such as enabling, disabling or extending Acknowledgments.",
    summary_type=TrackMeResponseSummary,
)
def ack_manage(
    params: ManageAckParams, soar: SOARClient, asset: Asset
) -> ManageAckOutput:
    body = {
        "tenant_id": params.tenant_id,
        "object_category": params.object_category,
        "object_list": params.object_list,
        "action": params.action,
    }
    if params.ack_comment:
        body["ack_comment"] = params.ack_comment
    if params.ack_period:
        body["ack_period"] = params.ack_period
    if params.ack_type:
        body["ack_type"] = params.ack_type
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ack/write/ack_manage",
        method="post",
        data=json.dumps(body),
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Ack manage successful")
    return ManageAckOutput(**response)


class CheckMaintenanceStatusOutput(TrackMeOutput):
    maintenance: str | None = OutputField(
        example_values=["False", "True"], column_name="Maintenance"
    )
    maintenance_mode: str | None = OutputField(
        example_values=["disabled", "enabled", "scheduled"], column_name="Mode"
    )
    maintenance_message: str | None = OutputField(
        example_values=[
            "The maintenance is currently disabled, all alerts from TrackMe are permitted"
        ]
    )
    maintenance_comment: str | None = OutputField(example_values=["API update"])
    tenants_scope: str | None = OutputField(example_values=["*"], column_name="Scope")
    maintenance_countdown: str | None = OutputField(example_values=["86358"])
    maintenance_mode_start: str | None = OutputField(example_values=["1712834220"])
    maintenance_mode_end: str | None = OutputField(example_values=["1712920620"])
    knowledge_record_id: str | None = OutputField(example_values=["example-record-id"])
    src_user: str | None = OutputField(example_values=["svc-trackme"])
    time_started: str | None = OutputField(example_values=["2026-07-15 22:05"])
    time_updated: str | None = OutputField(example_values=["2026-07-15 22:05"])


@app.action(
    name="maintenance_status",
    description="Check and return the maintenance mode status",
    action_type="generic",
    read_only=False,
    verbose="This action allows retrieving the current TrackMe maintenance mode status.",
    summary_type=TrackMeResponseSummary,
)
def maintenance_status(
    params: Params, soar: SOARClient, asset: Asset
) -> CheckMaintenanceStatusOutput:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/maintenance/check_global_maintenance_status",
        method="get",
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Get maintenance mode successful")
    return CheckMaintenanceStatusOutput(**response)


class EnableMaintenanceModeParams(Params):
    add_knowledge_record: str | None = Param(
        description="Boolean value to indicate if a knowledge record should be added to the knowledge database, defaults to true"
    )
    maintenance_duration: float | None = Param(
        description="Duration of the maintenance window in seconds, if unspecified and maintenance_mode_end is not specified either, defaults to now plus 24 hours"
    )
    maintenance_mode_end: float | None = Param(
        description="Date time in epochtime format for the end of the maintenance window, it is overriden by maintenance_duration if specified, defaults to now plus 24 hours if not specified and maintenance_duration is not specified"
    )
    maintenance_mode_start: float | None = Param(
        description="Date time in epochtime format for the start of the maintennce window, defaults to now if not specified"
    )
    time_format: str | None = Param(
        description="Time format when submitting start and end maintenance values, defaults to epochtime and can alternatively be set to datestring which expects YYYY-MM-DDTHH:MM as the input format"
    )
    update_comment: str | None = Param(
        description="Comment for the update, comments are added to the audit record, if unset will be defined to: API update"
    )


class EnableMaintenanceModeOutput(TrackMeOutput):
    knowledge_record_id: str | None = OutputField(example_values=["example-record-id"])
    maintenance: str | None = OutputField(example_values=[0, 1])
    maintenance_comment: str | None = OutputField(
        example_values=["Maintenance enabled for operation ref: xxxx"]
    )
    maintenance_countdown: str | None = OutputField(example_values=[86358])
    maintenance_message: str | None = OutputField(
        example_values=[
            "The global maintenance mode is currently enabled, alerts from TrackMe are not permitted"
        ]
    )
    maintenance_mode: str | None = OutputField(example_values=["enabled", "disabled"])
    maintenance_mode_end: str | None = OutputField(example_values=["TBC"])
    maintenance_mode_start: str | None = OutputField(example_values=[1712920620])
    src_user: str | None = OutputField(example_values=["svc-trackme"])
    time_started: str | None = OutputField(example_values=["2024-04-11 12:17"])
    time_updated: str | None = OutputField(example_values=["2024-04-11 12:32"])


@app.action(
    name="maintenance_enable",
    description="Enable global TrackMe maintenance mode",
    action_type="generic",
    read_only=False,
    verbose="This action enables the TrackMe global maintenance mode.",
    summary_type=TrackMeResponseSummary,
)
def maintenance_enable(
    params: EnableMaintenanceModeParams, soar: SOARClient, asset: Asset
) -> EnableMaintenanceModeOutput:
    body = {}
    if params.add_knowledge_record:
        body["add_knowledge_record"] = params.add_knowledge_record
    if params.maintenance_duration:
        body["maintenance_duration"] = _int_param(
            params.maintenance_duration, "maintenance_duration"
        )
    if params.maintenance_mode_end:
        body["maintenance_mode_end"] = _int_param(
            params.maintenance_mode_end, "maintenance_mode_end"
        )
    if params.maintenance_mode_start:
        body["maintenance_mode_start"] = _int_param(
            params.maintenance_mode_start, "maintenance_mode_start"
        )
    if params.time_format:
        body["time_format"] = params.time_format
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/maintenance/global_maintenance_enable",
        method="post",
        data=json.dumps(body),
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Maintenance mode enable successful")
    return EnableMaintenanceModeOutput(**response)


class DisableMaintenanceModeParams(Params):
    update_comment: str | None = Param(
        description="Comment for the update, comments are added to the audit record, if unset will be defined to: API update"
    )


class DisableMaintenanceModeOutput(TrackMeOutput):
    epoch_updated: str | None = OutputField(example_values=[1712835165])
    maintenance: str | None = OutputField(example_values=[0, 1])
    maintenance_comment: str | None = OutputField(
        example_values=["Maintenance enabled for operation ref: xxxx"]
    )
    maintenance_message: str | None = OutputField(
        example_values=[
            "The global maintenance mode is currently enabled, alerts from TrackMe are not permitted"
        ]
    )
    maintenance_mode: str | None = OutputField(example_values=["enabled", "disabled"])
    src_user: str | None = OutputField(example_values=["svc-trackme"])
    time_updated: str | None = OutputField(example_values=["2024-04-11 12:37"])


@app.action(
    name="maintenance_disable",
    description="Disable global TrackMe maintenance mode",
    action_type="generic",
    read_only=False,
    verbose="This action disable the TrackMe global maintenance mode.",
    summary_type=TrackMeResponseSummary,
)
def maintenance_disable(
    params: DisableMaintenanceModeParams, soar: SOARClient, asset: Asset
) -> DisableMaintenanceModeOutput:
    body = {}
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/maintenance/maintenance_disable",
        method="post",
        data=json.dumps(body),
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Maintenance mode disable successful")
    return DisableMaintenanceModeOutput(**response)


class GetTenantsStatusParams(Params):
    tenant_id: str | None = Param(
        description="Tenant identifier, do not specify a tenant identifier to retrieve the status of all tenants"
    )


class GetTenantsStatusOutput(TrackMeOutput):
    tenant_id: str | None = OutputField(example_values=["mytenant"])
    status: str | None = OutputField(example_values=["OPERATIONAL", "DEGRADED"])
    overall_ops_pct: str | None = OutputField(example_values=[100])
    job_component_register: str | None = OutputField(
        example_values=["JSON object with jobs operation details"]
    )


@app.action(
    name="tenants_ops_status",
    description="Get TrackMe Tenants operation status",
    action_type="generic",
    read_only=False,
    verbose="This action retrieves the current operational status of the TrackMe tenants.",
    summary_type=TrackMeResponseSummary,
)
def tenants_ops_status(
    params: GetTenantsStatusParams, soar: SOARClient, asset: Asset
) -> Iterator[GetTenantsStatusOutput]:
    body = {}
    if params.tenant_id:
        body["tenant_id"] = params.tenant_id

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/configuration/get_tenant_ops_status",
        method="post",
        data=json.dumps(body),
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Get TrackMe Tenants Ops status successful")
    return (GetTenantsStatusOutput(**item) for item in _result_rows(response))


class CheckConnectivityParams(Params):
    account: str | None = Param(
        description="TrackMe remote account name, do not specify any account to verify all configured accounts"
    )


class CheckConnectivityOutput(TrackMeOutput):
    status: str | None = OutputField(
        example_values=["success", "failed"], column_name="Status"
    )
    host: str | None = OutputField(
        example_values=["mysplunk.mydomain.com"],
        cef_types=["host name", "ip"],
        column_name="Host",
    )
    port: str | None = OutputField(example_values=["8089"], column_name="Port")
    account: str | None = OutputField(
        example_values=["my_remote_account"], column_name="Account"
    )
    message: str | None = OutputField(
        example_values=[
            "remote search connectivity check was successful, service was established"
        ]
    )


@app.action(
    name="remote_accounts_check_connectivity",
    description="Run a connectivity check for TrackMe remote accounts",
    action_type="generic",
    read_only=False,
    verbose="This action runs a connectivity check for TrackMe remote accounts which validates both network connectivity and authentication to the remote Splunk deployment.",
)
def remote_accounts_check_connectivity(
    params: CheckConnectivityParams, soar: SOARClient, asset: Asset
) -> Iterator[CheckConnectivityOutput]:
    remote_accounts_list = []
    if not params.account:
        response = trackme_rest_call(
            asset,
            "/services/trackme/v2/configuration/list_accounts",
            method="get",
        )
        for remote_account in response.get("accounts", []):
            if remote_account != "local":
                remote_accounts_list.append(remote_account)
    else:
        remote_accounts_list.append(params.account)

    if not len(remote_accounts_list) > 0:
        raise ActionFailure(
            "No remote accounts configured were found on this TrackMe instance."
        )

    results = []
    for remote_account in remote_accounts_list:
        body = {"account": remote_account}
        response = trackme_rest_call(
            asset,
            "/services/trackme/v2/configuration/test_remote_account",
            method="post",
            data=json.dumps(body),
        )
        results.append(
            CheckConnectivityOutput(
                account=remote_account,
                host=response.get("host"),
                message=response.get("message"),
                status=response.get("status"),
                port=response.get("port"),
            )
        )

    logger.progress("Check remote account connectivity successful")
    return iter(results)


class RequestOutlierModelsParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk"
    )
    object: str = Param(description="TrackMe entity name")


@app.action(
    name="ml_outliers_train_models",
    description="Requests Machine Learning models training for a given entity",
    action_type="generic",
    read_only=False,
    verbose="Programmatically train ML models for a given entity.",
    summary_type=TrackMeResponseSummary,
)
def ml_outliers_train_models(
    params: RequestOutlierModelsParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object_list": params.object,
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/write/outliers_train_models",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Machine Leaning Outliers training successful")
    return TrackMeGenericOutput(**response)


class RunOutliersMonitorParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk"
    )
    object: str = Param(description="TrackMe entity name")


@app.action(
    name="ml_outliers_run_monitor",
    description="Runs Machine Learning Outliers monitor process for a given entity",
    action_type="generic",
    read_only=False,
    verbose="This actions runs TrackMe Learning Outliers monitor for a given entity.",
    summary_type=TrackMeResponseSummary,
)
def ml_outliers_run_monitor(
    params: RunOutliersMonitorParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object_list": params.object,
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/write/outliers_mlmonitor_models",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Machine Leaning Outliers monitor successful")
    return TrackMeGenericOutput(**response)


class ResetOutliersModelsParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk"
    )
    object: str = Param(description="TrackMe entity name")


@app.action(
    name="ml_outliers_reset_models",
    description="Reset all ML outliers models for a given entity",
    action_type="generic",
    read_only=False,
    verbose="This actions resets ML models rules for a given entity.",
    summary_type=TrackMeResponseSummary,
)
def ml_outliers_reset_models(
    params: ResetOutliersModelsParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object": params.object,
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/write/outliers_reset_models",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Machine Leaning Outliers reset successful")
    return TrackMeGenericOutput(**response)


class GetOutliersModelsParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk"
    )
    object: str = Param(description="TrackMe entity name")


class GetOutliersModelsOutput(TrackMeOutput):
    object: str | None = OutputField(
        example_values=["org_eu_linux:linux_secure"], column_name="Object"
    )
    object_category: str | None = OutputField(example_values=["splk-flx"])
    model_id: str | None = OutputField(
        example_values=["model_123456789012345"], column_name="Model ID"
    )
    kpi_metric: str | None = OutputField(
        example_values=["splk.flx.dcount_hosts"], column_name="KPI Metric"
    )
    algorithm: str | None = OutputField(
        example_values=["TrackMeNativeDensityFunction"], column_name="Algorithm"
    )
    kpi_span: str | None = OutputField(example_values=["10m"])
    is_disabled: str | None = OutputField(example_values=["0", "1"])
    confidence: str | None = OutputField(
        example_values=["normal", "low", "high"], column_name="Confidence"
    )
    confidence_reason: str | None = OutputField(
        example_values=["ML has sufficient historical metrics to proceed"]
    )
    score: str | None = OutputField(example_values=["36"], column_name="Score")
    method_calculation: str | None = OutputField(example_values=["avg"])
    density_lowerthreshold: str | None = OutputField(example_values=["0.005"])
    density_upperthreshold: str | None = OutputField(example_values=["0.005"])
    alert_lower_breached: str | None = OutputField(example_values=["1", "0"])
    alert_upper_breached: str | None = OutputField(example_values=["1", "0"])
    auto_correct: str | None = OutputField(example_values=["1", "0"])
    period_calculation: str | None = OutputField(example_values=["-90d"])
    period_calculation_latest: str | None = OutputField(example_values=["-1d"])
    perc_min_lowerbound_deviation: str | None = OutputField(example_values=["25.0"])
    perc_min_upperbound_deviation: str | None = OutputField(example_values=["25.0"])
    model_storage: str | None = OutputField(example_values=["kvstore"])
    last_exec: str | None = OutputField(example_values=["1784153540.9442525"])


@app.action(
    name="ml_outliers_get_models",
    description="Get ML Outliers models information for a given entity",
    action_type="generic",
    read_only=False,
    verbose="This action retrieves the key information for Machine Learning Outliers for a given entity.",
    summary_type=TrackMeResponseSummary,
)
def ml_outliers_get_models(
    params: GetOutliersModelsParams, soar: SOARClient, asset: Asset
) -> Iterator[GetOutliersModelsOutput]:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object": params.object,
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/outliers_get_rules",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Machine Leaning Outliers get successful")
    return (GetOutliersModelsOutput(**item) for item in _result_rows(response))


class AddExclusionPeriodParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(description="The component value: dsm/dhm/wlk/flx")
    object: str = Param(description="The entity name")
    model_id: str = Param(description="The Machine Learning model identifier")
    earliest: str | None = Param(
        description="The earliest time of the exclusion window (epoch time, or a relative modifier such as -2d)"
    )
    latest: str | None = Param(
        description="The latest time of the exclusion window (epoch time, or a relative modifier such as -1d)"
    )


class AddExclusionPeriodOutput(TrackMeOutput):
    results: str | None = OutputField(
        example_values=["Exclusion period for ML model was successfully added"]
    )
    failures_count: str | None = OutputField(example_values=["0"])


@app.action(
    name="ml_outliers_add_period_exclusion",
    description="Add an exclusion period to a given ML model",
    action_type="generic",
    read_only=False,
    verbose="This action adds a period of exclusion for a given Machine Learning model.",
    summary_type=TrackMeResponseSummary,
)
def ml_outliers_add_period_exclusion(
    params: AddExclusionPeriodParams, soar: SOARClient, asset: Asset
) -> AddExclusionPeriodOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object": params.object,
        "action": "add",
        "model_id": params.model_id,
        "earliest": params.earliest,
        "latest": params.latest,
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/write/outliers_manage_model_period_exclusion",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Machine Leaning Outliers add exclusion period successful")
    return AddExclusionPeriodOutput(**response)


class GetEntityDataParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk"
    )
    filter_key: str | None = Param(
        description="Key identifier, multiple keys can be specified as a comma-separated list of values. (you can use filter_object OR filter_key)"
    )
    filter_object: str | None = Param(
        description="Object identifier, multiple objects can be specified as a comma-separated list of values. (you can use filter_object OR filter_key)"
    )


class GetEntityDataOutput(TrackMeOutput):
    object: str | None = OutputField(
        example_values=["org_eu_linux:linux_secure"], column_name="Object"
    )
    object_category: str | None = OutputField(example_values=["splk-dsm"])
    tenant_id: str | None = OutputField(example_values=["mytenant"])
    keyid: str | None = OutputField(example_values=["example-key"])
    alias: str | None = OutputField(example_values=["org_eu_linux:linux_secure"])
    object_state: str | None = OutputField(
        example_values=["green", "orange", "red"], column_name="State"
    )
    object_previous_state: str | None = OutputField(example_values=["orange", "green"])
    monitored_state: str | None = OutputField(
        example_values=["enabled", "disabled"], column_name="Monitored"
    )
    priority: str | None = OutputField(
        example_values=["medium", "high", "low"], column_name="Priority"
    )
    sla_class: str | None = OutputField(example_values=["silver", "gold", "bronze"])
    sla_is_breached: str | None = OutputField(example_values=["0", "1"])
    sla_message: str | None = OutputField(
        example_values=["SLA is not breached, the entity is not in a red state"]
    )
    score: str | None = OutputField(example_values=["48"], column_name="Score")
    status_message: str | None = OutputField(
        example_values=["Entity has an impact score of 48.0 (base score: 0.0)"]
    )
    anomaly_reason: str | None = OutputField(
        example_values=["lag_threshold_breached", "no_anomalies_detected"]
    )
    isAnomaly: str | None = OutputField(example_values=["0", "1"])
    isOutlier: str | None = OutputField(example_values=["0", "1"])
    isOutlierReason: str | None = OutputField(
        example_values=[
            "Outliers ML breached lower bound for kpi splk.flx.dcount_hosts"
        ]
    )
    outliers_readiness: str | None = OutputField(example_values=["True", "False"])
    models_in_anomaly: str | None = OutputField(
        example_values=["model_123456789012345"]
    )
    ack_state: str | None = OutputField(example_values=["active", "inactive"])
    ack_type: str | None = OutputField(example_values=["sticky", "unsticky"])
    is_under_maintenance: str | None = OutputField(example_values=["0", "1"])
    data_index: str | None = OutputField(example_values=["org_eu_linux"])
    data_sourcetype: str | None = OutputField(example_values=["aws:config"])
    dcount_host: str | None = OutputField(example_values=["1"])
    last_ingest: str | None = OutputField(example_values=["15 Jul 2026 22:18"])
    last_time: str | None = OutputField(example_values=["15 Jul 2026 19:16"])
    lag_summary: str | None = OutputField(example_values=["03:05:55 / 03:02:15"])
    latest_flip_state: str | None = OutputField(example_values=["orange", "green"])
    notes_count: str | None = OutputField(example_values=["1"])
    tags: str | None = OutputField(example_values=["cloud", "infra"])


@app.action(
    name="component_get_entity",
    description="Get TrackMe entities realtime data and status",
    action_type="generic",
    read_only=False,
    verbose="This action returns the realtime TrackMe knowledge for a given TrackMe entity.",
    summary_type=TrackMeResponseSummary,
)
def component_get_entity(
    params: GetEntityDataParams, soar: SOARClient, asset: Asset
) -> Iterator[GetEntityDataOutput]:
    query_params = {
        "tenant_id": params.tenant_id,
        "component": params.component,
    }
    if params.filter_key:
        query_params["filter_key"] = params.filter_key
    if params.filter_object:
        query_params["filter_object"] = params.filter_object

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/component/load_component_data",
        method="get",
        params=query_params,
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Get TrackMe entity realtime data successful")
    return (GetEntityDataOutput(**item) for item in _result_rows(response, key="data"))


class ManageEntitiesParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: flx, dsm, dhm, mhm, wlk"
    )
    filter_object: str | None = Param(
        description="Object identifier, multiple objects can be specified as a comma-separated list of values. (you can use filter_object OR filter_key)"
    )
    filter_key: str | None = Param(
        description="Keyid identifier, multiple keys can be specified as a comma-separated list of values. (you can use filter_object OR filter_key)"
    )
    action: str = Param(
        description="The Action requested, valid options are: enable, disable, delete, manage_dsm_sampling, update_hours_ranges, update_wdays, update_priority, update_lag_policy, update_dcount_host, update_manual_tags"
    )
    extra_attributes: str | None = Param(
        description='A JSON object containing attributes for the action. For example, the action update_lag_policy could be asssociated with the following extra_attributes: {"data_max_delay_allowed": 7200, "data_max_lag_allowed": 900}'
    )
    update_comment: str | None = Param(
        description="Optional comment for audit purposes"
    )


@app.action(
    name="component_manage_entity",
    description="This action allows managing TrackMe entities",
    action_type="correct",
    read_only=False,
    verbose="This action can be used to manage various aspects of TrackMe entities, such as enabling/disabling, deleting entities or maintaining components specific parameters using the extra_attributes JSON object.",
    summary_type=TrackMeResponseSummary,
)
def component_manage_entity(
    params: ManageEntitiesParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    tenant_id = params.tenant_id
    component = params.component
    action = params.action
    filter_object = params.filter_object
    filter_key = params.filter_key
    update_comment = params.update_comment

    extra_attributes = params.extra_attributes
    with contextlib.suppress(Exception):
        extra_attributes = json.loads(extra_attributes)
    if extra_attributes is not None and not isinstance(extra_attributes, dict):
        raise ActionFailure("extra_attributes must be a valid JSON object.")

    target_endpoint = None
    if bool(filter_object) == bool(filter_key):
        raise ActionFailure(
            "Exactly one of filter_object or filter_key must be provided."
        )

    body = {"tenant_id": tenant_id}
    if filter_object:
        body["object_list"] = filter_object
    else:
        body["keys_list"] = filter_key

    if update_comment:
        body["update_comment"] = update_comment

    allowed_actions = [
        "enable",
        "disable",
        "delete",
        "manage_dsm_sampling",
        "update_hours_ranges",
        "update_wdays",
        "update_priority",
        "update_lag_policy",
        "update_dcount_host",
        "update_manual_tags",
    ]
    if action not in allowed_actions:
        raise ActionFailure(
            f"Invalid action={action}, valid actions are: {allowed_actions}"
        )

    prefix = (
        _COMPONENT_PREFIX_ALL.get(component)
        if component in _LEGACY_COMPONENTS
        else None
    )

    if action in ("enable", "disable"):
        body["action"] = action
        if prefix:
            target_endpoint = (
                f"/services/trackme/v2/splk_{component}/write/{prefix}_monitoring"
            )

    elif action == "delete":
        deletion_type = "temporary"
        if extra_attributes:
            try:
                deletion_type = extra_attributes["deletion_type"]
            except Exception:
                deletion_type = "temporary"
        body["deletion_type"] = deletion_type
        if prefix:
            target_endpoint = (
                f"/services/trackme/v2/splk_{component}/write/{prefix}_delete"
            )

    elif action == "manage_dsm_sampling":
        if component != "dsm":
            raise ActionFailure(
                f'Component "{component}" does not support action "{action}" '
                "(data sampling is a dsm-only feature)"
            )
        if not extra_attributes:
            raise ActionFailure(
                f"When request action={action}, you must provide in extra_attributes "
                "the requested action:enable|disable|reset|run|update_no_records"
            )
        try:
            sampling_action = extra_attributes["action"]
        except Exception as e:
            raise ActionFailure(
                "sampling action must be set in extra_attributes, valid actions are: "
                "enable|disable|reset|run|update_no_records"
            ) from e
        if sampling_action not in (
            "enable",
            "disable",
            "reset",
            "run",
            "update_no_records",
        ):
            raise ActionFailure(
                f"Illegal action={sampling_action}, valid actions are: "
                "enable|disable|reset|run|update_no_records"
            )
        body["action"] = sampling_action

        if sampling_action in ("enable", "disable", "reset", "run"):
            target_endpoint = (
                "/services/trackme/v2/splk_dsm/write/ds_manage_data_sampling"
            )
        elif sampling_action == "update_no_records":
            target_endpoint = (
                "/services/trackme/v2/splk_dsm/write/ds_update_data_sampling_records_nr"
            )
            try:
                data_sampling_nr = extra_attributes["data_sampling_nr"]
                if not isinstance(data_sampling_nr, int):
                    raise ActionFailure(
                        f"action={action} requires data_sampling_nr to be set in "
                        "extra_attributes as an integer value."
                    )
                body["data_sampling_nr"] = data_sampling_nr
            except ActionFailure:
                raise
            except Exception as e:
                raise ActionFailure(
                    f"action={action} requires data_sampling_nr to be set in "
                    "extra_attributes as an integer value."
                ) from e

    elif action == "update_hours_ranges":
        if not extra_attributes:
            raise ActionFailure(
                f"When request action={action}, you must provide in extra_attributes "
                "the hours_ranges parameter"
            )
        try:
            hours_ranges = extra_attributes["hours_ranges"]
        except Exception as e:
            raise ActionFailure(
                f"hours_ranges must be set in extra_attributes when action={action}"
            ) from e
        if not isinstance(hours_ranges, list) and hours_ranges not in (
            "all_ranges",
            "manual:08h-to-20h",
        ):
            raise ActionFailure(
                "hours_ranges must be all_ranges, manual:08h-to-20h, or a list of "
                f"integers, but got: {hours_ranges}"
            )
        body["monitoring_hours_ranges"] = hours_ranges
        if prefix:
            target_endpoint = f"/services/trackme/v2/splk_{component}/write/{prefix}_update_hours_ranges"

    elif action == "update_wdays":
        if not extra_attributes:
            raise ActionFailure(
                f"When request action={action}, you must provide in extra_attributes "
                "the wdays parameter"
            )
        try:
            wdays = extra_attributes["wdays"]
        except Exception as e:
            raise ActionFailure(
                f"wdays must be set in extra_attributes when action={action}"
            ) from e
        if not isinstance(wdays, list) and wdays not in (
            "all_days",
            "manual:monday-to-friday",
            "manual:monday-to-saturday",
        ):
            raise ActionFailure(
                "wdays must be all_days, manual:monday-to-friday, "
                f"manual:monday-to-saturday, or a list of integers, but got: {wdays}"
            )
        body["monitoring_wdays"] = wdays
        if prefix:
            target_endpoint = (
                f"/services/trackme/v2/splk_{component}/write/{prefix}_update_wdays"
            )

    elif action == "update_priority":
        if not extra_attributes:
            raise ActionFailure(
                f"When request action={action}, you must provide in extra_attributes "
                "the priority parameter"
            )
        try:
            priority = extra_attributes["priority"]
        except Exception as e:
            raise ActionFailure(
                f"priority must be set in extra_attributes when action={action}"
            ) from e
        if priority not in ("low", "medium", "high"):
            raise ActionFailure(
                f"priority must be low, medium, or high, but got: {priority}"
            )
        body["priority"] = priority
        if prefix:
            target_endpoint = (
                f"/services/trackme/v2/splk_{component}/write/{prefix}_update_priority"
            )

    elif action == "update_lag_policy":
        if not extra_attributes:
            raise ActionFailure(
                f"When request action={action}, you must provide in extra_attributes "
                "at least one lag policy option"
            )
        allow_adaptive_delay = extra_attributes.get("allow_adaptive_delay", None)
        if allow_adaptive_delay:
            if allow_adaptive_delay not in ("true", "false"):
                raise ActionFailure(
                    f"allow_adaptive_delay must be true or false, but got: {allow_adaptive_delay}"
                )
            body["allow_adaptive_delay"] = allow_adaptive_delay

        data_lag_alert_kpis = extra_attributes.get("data_lag_alert_kpis", None)
        if data_lag_alert_kpis:
            if data_lag_alert_kpis not in (
                "all_kpis",
                "lag_ingestion_kpi",
                "lag_event_kpi",
            ):
                raise ActionFailure(
                    "data_lag_alert_kpis must be all_kpis, lag_ingestion_kpi, or "
                    f"lag_event_kpi, but got: {data_lag_alert_kpis}"
                )
            body["data_lag_alert_kpis"] = data_lag_alert_kpis

        data_max_delay_allowed = extra_attributes.get("data_max_delay_allowed", None)
        if data_max_delay_allowed:
            if not isinstance(data_max_delay_allowed, int):
                raise ActionFailure(
                    f"data_max_delay_allowed must be an integer, but got: {data_max_delay_allowed}"
                )
            body["data_max_delay_allowed"] = data_max_delay_allowed

        data_max_lag_allowed = extra_attributes.get("data_max_lag_allowed", None)
        if data_max_lag_allowed:
            if not isinstance(data_max_lag_allowed, int):
                raise ActionFailure(
                    f"data_max_lag_allowed must be an integer, but got: {data_max_lag_allowed}"
                )
            body["data_max_lag_allowed"] = data_max_lag_allowed

        data_override_lagging_class = extra_attributes.get(
            "data_override_lagging_class", None
        )
        if data_override_lagging_class:
            if data_override_lagging_class not in ("true", "false"):
                raise ActionFailure(
                    "data_override_lagging_class must be true or false, but got: "
                    f"{data_override_lagging_class}"
                )
            body["data_override_lagging_class"] = data_override_lagging_class

        future_tolerance = extra_attributes.get("future_tolerance", None)
        if future_tolerance:
            if not isinstance(future_tolerance, int):
                raise ActionFailure(
                    f"future_tolerance must be an integer, but got: {future_tolerance}"
                )
            body["future_tolerance"] = future_tolerance

        splk_dhm_alerting_policy = extra_attributes.get(
            "splk_dhm_alerting_policy", None
        )
        if splk_dhm_alerting_policy:
            if component != "dhm":
                raise ActionFailure(
                    f"splk_dhm_alerting_policy is only valid for dhm component, but got: {component}"
                )
            if splk_dhm_alerting_policy not in (
                "all_kpis",
                "lag_ingestion_kpi",
                "lag_event_kpi",
            ):
                raise ActionFailure(
                    "splk_dhm_alerting_policy must be all_kpis, lag_ingestion_kpi, or "
                    f"lag_event_kpi, but got: {splk_dhm_alerting_policy}"
                )
            body["splk_dhm_alerting_policy"] = splk_dhm_alerting_policy

        if component == "dsm":
            target_endpoint = "/services/trackme/v2/splk_dsm/write/ds_update_lag_policy"
        elif component == "dhm":
            target_endpoint = "/services/trackme/v2/splk_dhm/write/dh_update_lag_policy"
        else:
            raise ActionFailure(
                f'Component "{component}" does not support action "{action}"'
            )

    elif action == "update_dcount_host":
        if component != "dsm":
            raise ActionFailure(
                f'Component "{component}" does not support action "{action}"'
            )
        try:
            min_dcount_host = extra_attributes["min_dcount_host"]
            if not isinstance(min_dcount_host, int) and min_dcount_host != "any":
                raise ActionFailure(
                    'min_dcount_host must be an integer or the keyworkd "any" to '
                    f"disable it, but got: {min_dcount_host}"
                )
            body["min_dcount_host"] = min_dcount_host
        except ActionFailure:
            raise
        except Exception as e:
            raise ActionFailure(
                f"min_dcount_host must be set in extra_attributes when action={action}"
            ) from e

        if min_dcount_host != "any":
            try:
                min_dcount_field = extra_attributes["min_dcount_field"]
            except Exception as e:
                raise ActionFailure(
                    f"min_dcount_field must be set in extra_attributes when action={action}"
                ) from e
            if min_dcount_field not in (
                "avg_dcount_host_5m",
                "latest_dcount_host_5m",
                "perc95_dcount_host_5m",
                "stdev_dcount_host_5m",
                "global_dcount_host",
            ):
                raise ActionFailure(
                    "min_dcount_field must be avg_dcount_host_5m, latest_dcount_host_5m, "
                    "perc95_dcount_host_5m, stdev_dcount_host_5m, or global_dcount_host, "
                    f"but got: {min_dcount_field}"
                )
            body["min_dcount_field"] = min_dcount_field

        target_endpoint = (
            "/services/trackme/v2/splk_dsm/write/ds_update_min_dcount_host"
        )

    elif action == "update_manual_tags":
        if component != "dsm":
            raise ActionFailure(
                f'Component "{component}" does not support action "{action}"'
            )
        try:
            tags_manual = extra_attributes["tags_manual"]
            if not isinstance(tags_manual, str):
                raise ActionFailure(
                    f"tags_manual must be a string, but got: {tags_manual}"
                )
            body["tags_manual"] = tags_manual
        except ActionFailure:
            raise
        except Exception as e:
            raise ActionFailure(
                f"tags_manual must be set in extra_attributes when action={action}"
            ) from e
        target_endpoint = "/services/trackme/v2/splk_dsm/write/ds_update_manual_tags"

    if not target_endpoint:
        raise ActionFailure(
            f'Component "{component}" does not support action "{action}"'
        )

    response = trackme_rest_call(
        asset,
        target_endpoint,
        method="post",
        data=json.dumps(body),
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Manage TrackMe entity successful")
    return TrackMeGenericOutput(**response)


class GetAssociationsInformationParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    filter_object: str = Param(
        description="The TrackMe entity object identifier to search for and return Logical Groups association information"
    )


class GetAssociationsInformationOutput(TrackMeOutput):
    object_group_name: str | None = OutputField(
        example_values=["grp-linux-eu-appxxx"], column_name="Group Name"
    )
    object_group_key: str | None = OutputField(
        example_values=["example-group-key"], column_name="Group Key"
    )
    object_group_min_green_percent: str | None = OutputField(example_values=["50"])
    object_group_mtime: str | None = OutputField(example_values=["1713009380.1757667"])
    object_group_mtime_human: str | None = OutputField(
        example_values=["13 Apr 2024 11:56"]
    )


@app.action(
    name="logical_group_get_group_for_entity",
    description="Get TrackMe logical groups associations for a given TrackMe entity",
    action_type="generic",
    read_only=False,
    verbose="This actions allows to retrieve and return the current associations information for a given TracKme entity.",
    summary_type=TrackMeResponseSummary,
)
def logical_group_get_group_for_entity(
    params: GetAssociationsInformationParams, soar: SOARClient, asset: Asset
) -> Iterator[GetAssociationsInformationOutput]:
    body = {"tenant_id": params.tenant_id}
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_logical_groups/logical_groups_collection",
        method="post",
        data=json.dumps(body),
    )

    entity_associated_logical_groups = []
    for item in _result_rows(response):
        object_group_members = item.get("object_group_members", [])
        for member in object_group_members:
            if member == params.filter_object:
                entity_associated_logical_groups.append(
                    {
                        "object_group_name": item.get("object_group_name"),
                        "object_group_key": item.get("_key"),
                        "object_group_members": object_group_members,
                        "object_group_min_green_percent": item.get(
                            "object_group_min_green_percent"
                        ),
                        "object_group_mtime": item.get("object_group_mtime"),
                        "object_group_mtime_human": item.get(
                            "object_group_mtime_human"
                        ),
                    }
                )

    soar.set_summary(
        TrackMeResponseSummary(
            trackme_response=json.dumps(entity_associated_logical_groups)
        )
    )

    if entity_associated_logical_groups:
        return (
            GetAssociationsInformationOutput(**item)
            for item in entity_associated_logical_groups
        )
    # Entity has no logical group association
    return iter(
        [
            GetAssociationsInformationOutput(
                object_group_name=None,
                object_group_key=None,
                object_group_members=[],
                object_group_min_green_percent=None,
                object_group_mtime=None,
                object_group_mtime_human=None,
            )
        ]
    )


class ManageLogicalGroupsParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    action: str = Param(
        description="The action to be performed on the logical group, valid options: show / associate / unassociate"
    )
    object_group_name: str | None = Param(
        description="Logical Group name, required for action associate / unassociate, if performing association the logical group will be created if it does not exist yet"
    )
    object_list: str | None = Param(
        description="Required for associate / unassociate, comma-separated list of entities to be associated or unassociated with the Logical Group"
    )
    object_group_min_green_percent: float | None = Param(
        description="For action: associate only, minimal green percentage for this group (for action: associate), if not specified, defaults to 50"
    )
    update_comment: str | None = Param(
        description="A comment for the update, comments are added to the audit record, if unset will be defined to: API update"
    )


@app.action(
    name="logical_group_manage",
    description="Manage TrackMe logical groups",
    action_type="generic",
    read_only=False,
    verbose="This actions allows to manage TrackMe logical groups and perform association or unassociation of entities with Logical Groups.",
    summary_type=TrackMeResponseSummary,
)
def logical_group_manage(
    params: ManageLogicalGroupsParams, soar: SOARClient, asset: Asset
) -> Iterator[TrackMeGenericOutput]:
    action = params.action

    body = {"tenant_id": params.tenant_id}
    if params.object_group_min_green_percent:
        body["object_group_min_green_percent"] = _int_param(
            params.object_group_min_green_percent, "object_group_min_green_percent"
        )
    if params.update_comment:
        body["update_comment"] = params.update_comment

    allowed_actions = ["show", "associate", "unassociate"]
    if action not in allowed_actions:
        raise ActionFailure(
            f"Invalid action={action}, valid actions are: {allowed_actions}"
        )

    if action == "show":
        target_endpoint = (
            "/services/trackme/v2/splk_logical_groups/logical_groups_collection"
        )
    else:
        body["action"] = action
        body["object_group_name"] = params.object_group_name
        body["object_list"] = params.object_list
        target_endpoint = "/services/trackme/v2/splk_logical_groups/write/logical_groups_associate_group"

    response = trackme_rest_call(
        asset,
        target_endpoint,
        method="post",
        data=json.dumps(body),
    )

    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Manage TrackMe logical group successful")
    return (TrackMeGenericOutput(**item) for item in _result_rows(response))


# ---------------------------------------------------------------------------
# Phase 2 — per-component entity operations
#
# Most TrackMe components (dsm, dhm, mhm, flx, fqm, wlk) expose an identical set
# of write endpoints under /splk_<component>/write/<prefix>_<op>. A single SOAR
# action per operation takes a `component` argument and routes accordingly.
# Entities are targeted by object_list (names) OR keys_list (KV _key values).
# ---------------------------------------------------------------------------


_ALL_COMPONENTS = tuple(_COMPONENT_PREFIX_ALL)


def _component_write_endpoint(
    component: str, op: str, allowed: tuple = _ALL_COMPONENTS
) -> str:
    if component not in allowed:
        raise ActionFailure(
            f"Unsupported component '{component}', valid options are: {list(allowed)}"
        )
    prefix = _COMPONENT_PREFIX_ALL[component]
    return f"/services/trackme/v2/splk_{component}/write/{prefix}_{op}"


def _entity_target_body(
    tenant_id: str,
    object_list: str | None,
    keys_list: str | None,
    update_comment: str | None = None,
) -> dict:
    if bool(object_list) == bool(keys_list):
        raise ActionFailure("Exactly one of object_list or keys_list must be provided.")
    body: dict = {"tenant_id": tenant_id}
    if object_list:
        body["object_list"] = object_list
    else:
        body["keys_list"] = keys_list
    if update_comment:
        body["update_comment"] = update_comment
    return body


class EntityBatchUpdateOutput(TrackMeOutput):
    action: str | None = OutputField(example_values=["success"])
    process_count: str | None = OutputField(example_values=["2"])
    success_count: str | None = OutputField(example_values=["2"])
    failures_count: str | None = OutputField(example_values=["0"])


class ToggleMonitoringParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    action: str = Param(
        description="The action to perform, valid options are: enable | disable"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names (use either object_list or keys_list)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values (use either object_list or keys_list)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity toggle monitoring",
    description="Enable or disable monitoring for TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action enables or disables monitoring for one or more TrackMe entities in a given component.",
    summary_type=TrackMeResponseSummary,
)
def entity_toggle_monitoring(
    params: ToggleMonitoringParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    if params.action not in ("enable", "disable"):
        raise ActionFailure(
            f"Invalid action={params.action}, valid options are: enable | disable"
        )
    endpoint = _component_write_endpoint(params.component, "monitoring")
    body = _entity_target_body(
        params.tenant_id, params.object_list, params.keys_list, params.update_comment
    )
    body["action"] = params.action

    response = trackme_rest_call(asset, endpoint, method="post", data=json.dumps(body))
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity toggle monitoring successful")
    return EntityBatchUpdateOutput(**response)


class UpdatePriorityParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    priority: str = Param(
        description="The priority, valid options are: low | medium | high | critical | pending"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names (use either object_list or keys_list)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values (use either object_list or keys_list)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity update priority",
    description="Update the priority of TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action updates the priority of one or more TrackMe entities in a given component.",
    summary_type=TrackMeResponseSummary,
)
def entity_update_priority(
    params: UpdatePriorityParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    if params.priority not in ("low", "medium", "high", "critical", "pending"):
        raise ActionFailure(
            f"Invalid priority={params.priority}, valid options are: "
            "low | medium | high | critical | pending"
        )
    endpoint = _component_write_endpoint(params.component, "update_priority")
    body = _entity_target_body(
        params.tenant_id, params.object_list, params.keys_list, params.update_comment
    )
    body["priority"] = params.priority

    response = trackme_rest_call(asset, endpoint, method="post", data=json.dumps(body))
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity update priority successful")
    return EntityBatchUpdateOutput(**response)


class UpdateSlaClassParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    sla_class: str = Param(
        description="The SLA class to apply (tenant-defined, e.g. gold, silver, bronze)"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names (use either object_list or keys_list)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values (use either object_list or keys_list)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity update sla class",
    description="Update the SLA class of TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action updates the SLA class of one or more TrackMe entities in a given component.",
    summary_type=TrackMeResponseSummary,
)
def entity_update_sla_class(
    params: UpdateSlaClassParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    endpoint = _component_write_endpoint(params.component, "update_sla_class")
    body = _entity_target_body(
        params.tenant_id, params.object_list, params.keys_list, params.update_comment
    )
    body["sla_class"] = params.sla_class

    response = trackme_rest_call(asset, endpoint, method="post", data=json.dumps(body))
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity update SLA class successful")
    return EntityBatchUpdateOutput(**response)


class ResetEntityParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dhm, mhm (reset is only supported for these components)"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names (use either object_list or keys_list)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values (use either object_list or keys_list)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity reset",
    description="Reset the learned knowledge of TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action resets the discovered index/sourcetype (dhm) or metrics (mhm) knowledge for one or more entities. Only the dhm and mhm components support reset.",
    summary_type=TrackMeResponseSummary,
)
def entity_reset(
    params: ResetEntityParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    endpoint = _component_write_endpoint(
        params.component, "reset", allowed=("dhm", "mhm")
    )
    body = _entity_target_body(
        params.tenant_id, params.object_list, params.keys_list, params.update_comment
    )

    response = trackme_rest_call(asset, endpoint, method="post", data=json.dumps(body))
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity reset successful")
    return EntityBatchUpdateOutput(**response)


class DeleteEntityParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    deletion_type: str = Param(
        description="The deletion type, valid options are: temporary | permanent"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names (use either object_list or keys_list)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values (use either object_list or keys_list)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity delete",
    description="Delete TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action deletes one or more TrackMe entities. A temporary deletion allows re-discovery, while a permanent deletion prevents the entity from being re-created.",
    summary_type=TrackMeResponseSummary,
)
def entity_delete(
    params: DeleteEntityParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    if params.deletion_type not in ("temporary", "permanent"):
        raise ActionFailure(
            f"Invalid deletion_type={params.deletion_type}, valid options are: "
            "temporary | permanent"
        )
    endpoint = _component_write_endpoint(params.component, "delete")
    body = _entity_target_body(
        params.tenant_id, params.object_list, params.keys_list, params.update_comment
    )
    body["deletion_type"] = params.deletion_type

    response = trackme_rest_call(asset, endpoint, method="post", data=json.dumps(body))
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity delete successful")
    return EntityBatchUpdateOutput(**response)


class ManageDataSamplingParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    action: str = Param(
        description="The data sampling action, valid options are: enable | disable | reset | run"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names (use either object_list or keys_list)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values (use either object_list or keys_list)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity manage data sampling",
    description="Manage data sampling for TrackMe DSM entities",
    action_type="generic",
    read_only=False,
    verbose="This action manages the data sampling feature for one or more TrackMe DSM entities (enable, disable, reset or run).",
    summary_type=TrackMeResponseSummary,
)
def entity_manage_data_sampling(
    params: ManageDataSamplingParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    if params.action not in ("enable", "disable", "reset", "run"):
        raise ActionFailure(
            f"Invalid action={params.action}, valid options are: "
            "enable | disable | reset | run"
        )
    body = _entity_target_body(
        params.tenant_id, params.object_list, params.keys_list, params.update_comment
    )
    body["action"] = params.action

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_dsm/write/ds_manage_data_sampling",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity manage data sampling successful")
    return TrackMeGenericOutput(**response)


class ComponentScoreOutput(TrackMeOutput):
    message: str | None = OutputField(
        example_values=["False positive score generated successfully"]
    )
    original_score: str | None = OutputField(example_values=["75.0"])
    negative_score: str | None = OutputField(example_values=["-75.0"])
    current_score: str | None = OutputField(example_values=["0.0"])


class SetFalsePositiveParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    object_id: str = Param(description="The entity identifier (KVstore _key)")
    object: str | None = Param(
        description="The entity display name (optional, for logging)"
    )


@app.action(
    name="entity set false positive",
    description="Mark a TrackMe entity detection as a false positive",
    action_type="generic",
    read_only=False,
    verbose="This action generates a negative impact score for a given entity to suppress a false positive detection.",
    summary_type=TrackMeResponseSummary,
)
def entity_set_false_positive(
    params: SetFalsePositiveParams, soar: SOARClient, asset: Asset
) -> ComponentScoreOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object_id": params.object_id,
    }
    if params.object:
        body["object"] = params.object

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/component/write/set_false_positive",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity set false positive successful")
    return ComponentScoreOutput(**response)


class ManualScoreOutput(TrackMeOutput):
    message: str | None = OutputField(
        example_values=["Manual score influence applied successfully (add 10)"]
    )
    applied_score: str | None = OutputField(example_values=["10"])
    score_type: str | None = OutputField(example_values=["add", "subtract"])
    score_value: str | None = OutputField(example_values=["10"])


class ManualScoreInfluenceParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    object_id: str = Param(description="The entity identifier (KVstore _key)")
    score_type: str = Param(
        description="The score influence type, valid options are: add | subtract"
    )
    score_value: float = Param(
        description="The score value to apply (positive integer)"
    )
    object: str | None = Param(
        description="The entity display name (optional, for logging)"
    )
    comment: str | None = Param(
        description="Optional comment recorded with the score event"
    )


@app.action(
    name="entity manual score influence",
    description="Apply a manual score influence to a TrackMe entity",
    action_type="generic",
    read_only=False,
    verbose="This action adds or subtracts a manual score delta for a given entity, to force it towards a green or red state.",
    summary_type=TrackMeResponseSummary,
)
def entity_manual_score_influence(
    params: ManualScoreInfluenceParams, soar: SOARClient, asset: Asset
) -> ManualScoreOutput:
    if params.score_type not in ("add", "subtract"):
        raise ActionFailure(
            f"Invalid score_type={params.score_type}, valid options are: add | subtract"
        )
    if params.score_value <= 0 or params.score_value != int(params.score_value):
        raise ActionFailure(
            f"score_value must be a positive integer, but got: {params.score_value}"
        )
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object_id": params.object_id,
        "score_type": params.score_type,
        "score_value": int(params.score_value),
    }
    if params.object:
        body["object"] = params.object
    if params.comment:
        body["comment"] = params.comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/component/write/manual_score_influence",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity manual score influence successful")
    return ManualScoreOutput(**response)


class GetEntityStatusParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    object: str | None = Param(
        description="The entity display name. Provide either object or object_id (mutually exclusive)"
    )
    object_id: str | None = Param(
        description="The entity KVstore _key. Provide either object or object_id (mutually exclusive)"
    )


@app.action(
    name="entity get status",
    description="Get the full status of a single TrackMe entity",
    action_type="investigate",
    read_only=True,
    verbose="This action returns a rich, computed description of a single TrackMe entity (identity, health, score, priority, SLA, maintenance and outliers).",
    summary_type=TrackMeResponseSummary,
)
def entity_get_status(
    params: GetEntityStatusParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    if bool(params.object) == bool(params.object_id):
        raise ActionFailure("Exactly one of object or object_id must be provided.")
    if params.component not in _ALL_COMPONENTS:
        raise ActionFailure(
            f"Unsupported component '{params.component}', valid options are: "
            f"{list(_ALL_COMPONENTS)}"
        )
    body = {
        "tenant_id": params.tenant_id,
        "object_category": f"splk-{params.component}",
    }
    if params.object:
        body["object"] = params.object
    if params.object_id:
        body["object_id"] = params.object_id

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/describe/entity",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Get TrackMe entity status successful")
    return TrackMeGenericOutput(**response)


# ---------------------------------------------------------------------------
# Phase 2 — per-entity maintenance windows
# ---------------------------------------------------------------------------


class MaintenanceWriteOutput(TrackMeOutput):
    action: str | None = OutputField(example_values=["success"])
    response: str | None = OutputField(example_values=["success"])


class SetEntityMaintenanceParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    keys_list: str = Param(
        description="Comma-separated list of entity KVstore _key values to place under maintenance"
    )
    maintenance_start_epoch: str = Param(
        description="Maintenance window start: epoch seconds, 'now', a relative offset (+30m/+2h/+1d), or ISO YYYY-MM-DDTHH:MM"
    )
    maintenance_end_epoch: str = Param(
        description="Maintenance window end: same formats as the start; must resolve after the start and in the future"
    )
    maintenance_comment: str | None = Param(
        description="Optional comment surfaced in the maintenance status and audit record"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity set maintenance",
    description="Place TrackMe entities into a timed maintenance window",
    action_type="generic",
    read_only=False,
    verbose="This action places one or more TrackMe entities into a timed maintenance window during which alerting is suppressed.",
    summary_type=TrackMeResponseSummary,
)
def entity_set_maintenance(
    params: SetEntityMaintenanceParams, soar: SOARClient, asset: Asset
) -> MaintenanceWriteOutput:
    if params.component not in _ALL_COMPONENTS:
        raise ActionFailure(
            f"Unsupported component '{params.component}', valid options are: "
            f"{list(_ALL_COMPONENTS)}"
        )
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "keys_list": params.keys_list,
        "maintenance_start_epoch": params.maintenance_start_epoch,
        "maintenance_end_epoch": params.maintenance_end_epoch,
    }
    if params.maintenance_comment:
        body["maintenance_comment"] = params.maintenance_comment
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/entity_maintenance/write/set_maintenance",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity set maintenance successful")
    return MaintenanceWriteOutput(**response)


class ClearEntityMaintenanceParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    keys_list: str = Param(
        description="Comma-separated list of entity KVstore _key values to clear from maintenance"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity clear maintenance",
    description="Clear the maintenance window of TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action clears the maintenance window of one or more TrackMe entities, returning them to their computed state.",
    summary_type=TrackMeResponseSummary,
)
def entity_clear_maintenance(
    params: ClearEntityMaintenanceParams, soar: SOARClient, asset: Asset
) -> MaintenanceWriteOutput:
    body = {"tenant_id": params.tenant_id, "keys_list": params.keys_list}
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/entity_maintenance/write/clear_maintenance",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity clear maintenance successful")
    return MaintenanceWriteOutput(**response)


class MaintenanceRecordOutput(TrackMeOutput):
    tenant_id: str | None = OutputField(example_values=["mytenant"])
    object: str | None = OutputField(
        example_values=["org_eu_linux:linux_secure"], column_name="Object"
    )
    object_category: str | None = OutputField(example_values=["splk-dsm"])
    component: str | None = OutputField(example_values=["dsm"], column_name="Component")
    is_active: str | None = OutputField(
        example_values=["True", "False"], column_name="Active"
    )
    maintenance_comment: str | None = OutputField(
        example_values=["planned maintenance"], column_name="Comment"
    )
    maintenance_start_epoch: str | None = OutputField(
        example_values=["1784150000"], column_name="Start"
    )
    maintenance_end_epoch: str | None = OutputField(
        example_values=["1784160000"], column_name="End"
    )
    src_user: str | None = OutputField(example_values=["admin"])


class ListEntityMaintenanceParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    keys_list: str | None = Param(
        description="Optional comma-separated list of entity KVstore _key values to filter on; omit to return all maintenance records for the tenant"
    )


@app.action(
    name="entity list maintenance",
    description="List active and pending TrackMe entity maintenance windows",
    action_type="investigate",
    read_only=True,
    verbose="This action lists the per-entity maintenance windows for a tenant, with an is_active flag computed at request time.",
    summary_type=TrackMeResponseSummary,
)
def entity_list_maintenance(
    params: ListEntityMaintenanceParams, soar: SOARClient, asset: Asset
) -> Iterator[MaintenanceRecordOutput]:
    body = {"tenant_id": params.tenant_id}
    if params.keys_list:
        body["keys_list"] = params.keys_list

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/entity_maintenance/list_maintenance",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity list maintenance successful")
    return (
        MaintenanceRecordOutput(**item)
        for item in _result_rows(response, key="records")
    )


# ---------------------------------------------------------------------------
# Phase 2 — ML Outliers extensions
# ---------------------------------------------------------------------------


class OutliersSetFalsePositiveParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    object_id: str = Param(description="The entity identifier (KVstore _key)")
    object: str | None = Param(
        description="The entity display name (optional, resolved automatically from object_id if not provided)"
    )


class OutliersSetFalsePositiveOutput(TrackMeOutput):
    message: str | None = OutputField(
        example_values=["False positive score generated successfully"]
    )
    original_score: str | None = OutputField(example_values=[75.0])
    negative_score: str | None = OutputField(example_values=[-75.0])
    current_score: str | None = OutputField(example_values=[0.0])


@app.action(
    name="outliers set false positive",
    description="Mark an ML outliers detection as a false positive",
    action_type="generic",
    read_only=False,
    verbose="This action generates a negative outliers score for a given entity to suppress a false positive ML outliers detection.",
    summary_type=TrackMeResponseSummary,
)
def outliers_set_false_positive(
    params: OutliersSetFalsePositiveParams, soar: SOARClient, asset: Asset
) -> OutliersSetFalsePositiveOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object_id": params.object_id,
    }
    if params.object:
        body["object"] = params.object

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/write/outliers_set_false_positive",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Outliers set false positive successful")
    return OutliersSetFalsePositiveOutput(**response)


class OutliersBulkActionParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, flx, fqm, wlk"
    )
    action: str = Param(
        description="The bulk action, valid options are: enable, disable, mlmonitor, mltrain, reset_status"
    )
    object_list: str | None = Param(
        description="Comma-separated list of entity names. Use either object_list or keys_list (mutually exclusive)"
    )
    keys_list: str | None = Param(
        description="Comma-separated list of entity KVstore _key values. Use either object_list or keys_list (mutually exclusive)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


class OutliersBulkActionOutput(TrackMeOutput):
    process_count: str | None = OutputField(example_values=[10])
    success_count: str | None = OutputField(example_values=[10])
    failures_count: str | None = OutputField(example_values=[0])
    action: str | None = OutputField(example_values=["mltrain"])
    job_sid: str | None = OutputField(example_values=["1712835612.3451912"])
    message: str | None = OutputField(example_values=["Bulk action dispatched"])


@app.action(
    name="outliers bulk action",
    description="Run a bulk ML outliers action across multiple entities",
    action_type="generic",
    read_only=False,
    verbose="This action runs a bulk ML outliers operation (enable, disable, mlmonitor, mltrain, reset_status) across multiple entities. The mlmonitor and mltrain actions are dispatched asynchronously as a background Splunk search.",
    summary_type=TrackMeResponseSummary,
)
def outliers_bulk_action(
    params: OutliersBulkActionParams, soar: SOARClient, asset: Asset
) -> OutliersBulkActionOutput:
    if bool(params.object_list) == bool(params.keys_list):
        raise ActionFailure("Exactly one of object_list or keys_list must be provided.")

    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "action": params.action,
    }
    if params.object_list:
        body["object_list"] = params.object_list
    if params.keys_list:
        body["keys_list"] = params.keys_list
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_outliers_engine/write/outliers_bulk_action",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Outliers bulk action successful")
    return OutliersBulkActionOutput(**response)


# ---------------------------------------------------------------------------
# Phase 2 — AI advisors & routines (asynchronous start / status / cancel)
#
# All AI jobs share a correlation id returned as `job_id` by the start call.
# The transport for job_id on the status/cancel calls differs per family:
#   * component health -> query string
#   * routines         -> either (query used here)
#
# The AI concierge advisor is deliberately not exposed: it is an interactive
# surface driven by the TrackMe UI and its AI chat, taking free-text user
# intent and returning proposals for a human to approve, which does not map
# onto playbook automation. Actions can be added later if that changes;
# removing them once shipped would break customer playbooks.
# ---------------------------------------------------------------------------


class AiJobStartOutput(TrackMeOutput):
    job_id: str | None = OutputField(example_values=["example-job-id"])
    status: str | None = OutputField(example_values=["running"])


class AiJobStatusOutput(TrackMeOutput):
    status: str | None = OutputField(
        example_values=["running", "complete", "error", "cancelled"]
    )
    error: str | None = OutputField(example_values=[""])


class AiJobCancelOutput(TrackMeOutput):
    status: str | None = OutputField(example_values=["cancelled", "already_done"])


class AiRoutineStartOutput(TrackMeOutput):
    routine_id: str | None = OutputField(example_values=["example-routine-id"])
    mode: str | None = OutputField(example_values=["inspect", "act"])
    job_id: str | None = OutputField(example_values=["example-job-id"])
    status: str | None = OutputField(example_values=["running"])


class AiComponentHealthStartParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(description="TrackMe component, valid options are: wlk, mhm")
    object: str | None = Param(
        description="The entity display name. Provide either object or object_id (mutually exclusive)"
    )
    object_id: str | None = Param(
        description="The entity KVstore _key. Provide either object or object_id (mutually exclusive, object_id preferred)"
    )
    mode: str | None = Param(
        description="Advisor mode, valid options are: inspect (default, read-only) or act (applies changes)"
    )
    provider_name: str | None = Param(
        description="AI provider stanza to use, defaults to the first configured provider"
    )
    user_context: str | None = Param(
        description="Free-text operator instructions passed to the advisor"
    )


@app.action(
    name="ai component health advisor",
    description="Start an AI component health advisor job",
    action_type="generic",
    read_only=False,
    verbose="This action starts an asynchronous AI component health advisor job for a given entity and returns a job_id to poll with the status action.",
    summary_type=TrackMeResponseSummary,
)
def ai_component_health_advisor(
    params: AiComponentHealthStartParams, soar: SOARClient, asset: Asset
) -> AiJobStartOutput:
    if bool(params.object) == bool(params.object_id):
        raise ActionFailure("Exactly one of object or object_id must be provided.")

    body = {"tenant_id": params.tenant_id, "component": params.component}
    if params.object:
        body["object"] = params.object
    if params.object_id:
        body["object_id"] = params.object_id
    if params.mode:
        body["mode"] = params.mode
    if params.provider_name:
        body["provider_name"] = params.provider_name
    if params.user_context:
        body["user_context"] = params.user_context

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ai_component_health/health_advisor",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("AI component health advisor started")
    return AiJobStartOutput(**response)


class AiJobIdParams(Params):
    job_id: str = Param(
        description="The AI job identifier returned by the start action"
    )


@app.action(
    name="ai component health advisor status",
    description="Get the status of an AI component health advisor job",
    action_type="investigate",
    read_only=True,
    verbose="This action polls the status of an AI component health advisor job. Terminal states are complete, error and cancelled.",
    summary_type=TrackMeResponseSummary,
)
def ai_component_health_advisor_status(
    params: AiJobIdParams, soar: SOARClient, asset: Asset
) -> AiJobStatusOutput:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ai_component_health/health_advisor_status",
        method="get",
        params={"job_id": params.job_id},
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("AI component health advisor status retrieved")
    return AiJobStatusOutput(**response)


@app.action(
    name="ai component health advisor cancel",
    description="Cancel an AI component health advisor job",
    action_type="generic",
    read_only=False,
    verbose="This action cancels a running AI component health advisor job.",
    summary_type=TrackMeResponseSummary,
)
def ai_component_health_advisor_cancel(
    params: AiJobIdParams, soar: SOARClient, asset: Asset
) -> AiJobCancelOutput:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ai_component_health/health_advisor_cancel",
        method="delete",
        params={"job_id": params.job_id},
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("AI component health advisor cancel requested")
    return AiJobCancelOutput(**response)


class AiRoutineRunNowParams(Params):
    routine_id: str = Param(description="The AI routine identifier to run")
    mode: str | None = Param(
        description="Optional mode override, set to inspect to force a read-only dry run (cannot escalate a notify routine to act)"
    )
    force_release: str | None = Param(
        description="Set to true to clear a held in-flight lock before launching"
    )


@app.action(
    name="ai routine run now",
    description="Run an AI routine on demand",
    action_type="generic",
    read_only=False,
    verbose="This action fires an AI routine on demand and returns a job_id to poll with the job status action.",
    summary_type=TrackMeResponseSummary,
)
def ai_routine_run_now(
    params: AiRoutineRunNowParams, soar: SOARClient, asset: Asset
) -> AiRoutineStartOutput:
    body = {"routine_id": params.routine_id}
    if params.mode:
        body["mode"] = params.mode
    if params.force_release:
        body["force_release"] = params.force_release

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ai_routines/write/run_now",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("AI routine run now started")
    return AiRoutineStartOutput(**response)


@app.action(
    name="ai routine job status",
    description="Get the status of an AI routine job",
    action_type="investigate",
    read_only=True,
    verbose="This action polls the status of an AI routine job. Terminal states are complete, error and cancelled.",
    summary_type=TrackMeResponseSummary,
)
def ai_routine_job_status(
    params: AiJobIdParams, soar: SOARClient, asset: Asset
) -> AiJobStatusOutput:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ai_routines/write/job_status",
        method="get",
        params={"job_id": params.job_id},
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("AI routine job status retrieved")
    return AiJobStatusOutput(**response)


class AiRoutineCancelJobParams(Params):
    job_id: str = Param(description="The AI routine job identifier to cancel")
    routine_id: str | None = Param(
        description="For a run_now fire, the routine identifier, to release the per-routine in-flight lock immediately"
    )


@app.action(
    name="ai routine cancel job",
    description="Cancel an AI routine job",
    action_type="generic",
    read_only=False,
    verbose="This action cancels a running AI routine job and optionally releases the per-routine in-flight lock.",
    summary_type=TrackMeResponseSummary,
)
def ai_routine_cancel_job(
    params: AiRoutineCancelJobParams, soar: SOARClient, asset: Asset
) -> AiJobCancelOutput:
    body = {"job_id": params.job_id}
    if params.routine_id:
        body["routine_id"] = params.routine_id

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/ai_routines/write/cancel_job",
        method="delete",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("AI routine cancel job requested")
    return AiJobCancelOutput(**response)


# ---------------------------------------------------------------------------
# Phase 2 — tenant, operations, labels, notes, blocklist
# ---------------------------------------------------------------------------


class TenantScopeParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    force: str | None = Param(
        description="Set to true to handle linked objects even if the tenant record is absent"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record"
    )


@app.action(
    name="tenant disable",
    description="Disable a TrackMe virtual tenant",
    action_type="generic",
    read_only=False,
    verbose="This action disables an entire TrackMe virtual tenant, disabling all of its objects.",
    summary_type=TrackMeResponseSummary,
)
def tenant_disable(
    params: TenantScopeParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {"tenant_id": params.tenant_id}
    if params.force:
        body["force"] = params.force
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/vtenants/admin/disable_tenant",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Tenant disable successful")
    return TrackMeGenericOutput(**response)


@app.action(
    name="tenant enable",
    description="Enable a TrackMe virtual tenant",
    action_type="generic",
    read_only=False,
    verbose="This action enables an entire TrackMe virtual tenant, enabling all of its objects.",
    summary_type=TrackMeResponseSummary,
)
def tenant_enable(
    params: TenantScopeParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {"tenant_id": params.tenant_id}
    if params.force:
        body["force"] = params.force
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/vtenants/admin/enable_tenant",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Tenant enable successful")
    return TrackMeGenericOutput(**response)


class RunTenantTrackerParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    report: str = Param(
        description="The name of the TrackMe savedsearch/report to run for the tenant"
    )
    earliest: str | None = Param(
        description="Optional Splunk earliest time quantifier; defaults to the savedsearch value"
    )
    latest: str | None = Param(
        description="Optional Splunk latest time quantifier; defaults to the savedsearch value"
    )
    use_savedsearch_time: str | None = Param(
        description="Set to true to use the savedsearch's own earliest/latest time range"
    )


@app.action(
    name="tenant run tracker",
    description="Run a TrackMe tenant tracker report on demand",
    action_type="generic",
    read_only=False,
    verbose="This action runs a TrackMe tenant tracker savedsearch on demand and returns the resulting rows.",
    summary_type=TrackMeResponseSummary,
)
def tenant_run_tracker(
    params: RunTenantTrackerParams, soar: SOARClient, asset: Asset
) -> Iterator[TrackMeGenericOutput]:
    body = {"tenant_id": params.tenant_id, "report": params.report}
    if params.earliest:
        body["earliest"] = params.earliest
    if params.latest:
        body["latest"] = params.latest
    if params.use_savedsearch_time:
        body["use_savedsearch_time"] = params.use_savedsearch_time

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/vtenants/write/run_tenant_tracker",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Tenant run tracker successful")
    return (TrackMeGenericOutput(**row) for row in _result_rows(response))


class TenantComponentsStatusParams(Params):
    tenant_id: str = Param(description="Tenant identifier")


class TenantComponentsStatusOutput(TrackMeOutput):
    schema_version: str | None = OutputField(
        example_values=["2409"], column_name="Schema Version"
    )
    component_splk_dsm: str | None = OutputField(
        example_values=["1", "0"], column_name="DSM"
    )
    component_splk_dhm: str | None = OutputField(
        example_values=["0", "1"], column_name="DHM"
    )
    component_splk_mhm: str | None = OutputField(
        example_values=["0", "1"], column_name="MHM"
    )
    component_splk_flx: str | None = OutputField(
        example_values=["0", "1"], column_name="FLX"
    )
    component_splk_fqm: str | None = OutputField(
        example_values=["0", "1"], column_name="FQM"
    )
    component_splk_wlk: str | None = OutputField(
        example_values=["0", "1"], column_name="WLK"
    )
    component_owner: str | None = OutputField(example_values=["nobody"])
    mloutliers: str | None = OutputField(
        example_values=["1", "0"], column_name="ML Outliers"
    )
    mloutliers_allowlist: str | None = OutputField(
        example_values=["dsm,dhm,flx,wlk,fqm"]
    )
    sampling: str | None = OutputField(example_values=["1", "0"])
    adaptive_delay: str | None = OutputField(example_values=["1", "0"])
    cmdb_lookup: str | None = OutputField(example_values=["1", "0"])
    pagination_mode: str | None = OutputField(example_values=["local", "remote"])
    ui_default_timerange: str | None = OutputField(example_values=["24h"])


@app.action(
    name="tenant get components status",
    description="Get the per-component configuration status for a tenant",
    action_type="investigate",
    read_only=True,
    verbose="This action returns the per-component configuration and enablement status for a TrackMe tenant.",
    summary_type=TrackMeResponseSummary,
)
def tenant_get_components_status(
    params: TenantComponentsStatusParams, soar: SOARClient, asset: Asset
) -> TenantComponentsStatusOutput:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/configuration/components",
        method="post",
        data=json.dumps({"tenant_id": params.tenant_id}),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Tenant get components status successful")
    return TenantComponentsStatusOutput(**response)


class TenantSchedulerStatusParams(Params):
    tenant_id: str | None = Param(
        description="Optional tenant identifier to filter on (the endpoint returns all tenants; filtering is applied client-side)"
    )


class TenantSchedulerStatusOutput(TrackMeOutput):
    tenant_id: str | None = OutputField(example_values=["mytenant"])
    report: str | None = OutputField(
        example_values=["TrackMe alert tenant_id:mytenant - stateful-alert"],
        column_name="Report",
    )
    status: str | None = OutputField(
        example_values=["completed", "skipped"], column_name="Status"
    )
    is_alert: str | None = OutputField(example_values=["1", "0"])
    pct_completed: str | None = OutputField(
        example_values=["100.00"], column_name="% Completed"
    )
    count: str | None = OutputField(example_values=["288"], column_name="Count")
    count_completed: str | None = OutputField(example_values=["288"])
    count_skipped: str | None = OutputField(example_values=["0"])


@app.action(
    name="tenant get scheduler status",
    description="Get the scheduled searches completion status",
    action_type="investigate",
    read_only=True,
    verbose="This action returns the scheduled searches completion status over the trailing 24h, optionally filtered to a single tenant.",
    summary_type=TrackMeResponseSummary,
)
def tenant_get_scheduler_status(
    params: TenantSchedulerStatusParams, soar: SOARClient, asset: Asset
) -> Iterator[TenantSchedulerStatusOutput]:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/restricted_searches/scheduler_status",
        method="get",
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Tenant get scheduler status successful")
    rows = _result_rows(response)
    if params.tenant_id:
        rows = [r for r in rows if r.get("tenant_id") == params.tenant_id]
    return (TenantSchedulerStatusOutput(**row) for row in rows)


class AlertsGetTenantParams(Params):
    tenant_id: str = Param(description="Tenant identifier")


class AlertsGetTenantOutput(TrackMeOutput):
    title: str | None = OutputField(
        example_values=["TrackMe alert tenant_id:mytenant - stateful-alert"],
        column_name="Title",
    )
    id: str | None = OutputField(
        example_values=["TrackMe%20alert%20tenant_id%3Amytenant%20-%20stateful-alert"]
    )
    actions: str | None = OutputField(
        example_values=["add_to_triggered,trackme_stateful_alert"]
    )
    disabled: str | None = OutputField(
        example_values=["0", "1"], column_name="Disabled"
    )
    cron_schedule: str | None = OutputField(
        example_values=["4-59/5 * * * *"], column_name="Cron"
    )


@app.action(
    name="alerts get tenant",
    description="Get the current TrackMe alerts for a tenant",
    action_type="investigate",
    read_only=True,
    verbose="This action returns the current TrackMe alerts for a given tenant.",
    summary_type=TrackMeResponseSummary,
)
def alerts_get_tenant(
    params: AlertsGetTenantParams, soar: SOARClient, asset: Asset
) -> Iterator[AlertsGetTenantOutput]:
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/alerting/get_tenant_alerts",
        method="post",
        data=json.dumps({"tenant_id": params.tenant_id}),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Alerts get tenant successful")
    return (AlertsGetTenantOutput(**row) for row in _result_rows(response))


class BlocklistAddParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, wlk, fqm"
    )
    object_category: str = Param(
        description="The entity field to match against (e.g. object, sourcetype, index, alias)"
    )
    object: str = Param(
        description="The value to block (literal or regex; use * as a wildcard)"
    )
    comment: str | None = Param(description="Optional comment for the blocklist record")
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="blocklist add",
    description="Add a TrackMe blocklist rule",
    action_type="generic",
    read_only=False,
    verbose="This action adds a blocklist rule so a matching source is no longer tracked by TrackMe.",
    summary_type=TrackMeResponseSummary,
)
def blocklist_add(
    params: BlocklistAddParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "object_category": params.object_category,
        "object": params.object,
    }
    if params.comment:
        body["comment"] = params.comment
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_blocklist/write/blocklist_add",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Blocklist add successful")
    return TrackMeGenericOutput(**response)


class BlocklistDelParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, wlk, fqm"
    )
    keys_list: str = Param(
        description="Comma-separated list of blocklist record KVstore _key values to delete"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="blocklist del",
    description="Delete TrackMe blocklist rules",
    action_type="generic",
    read_only=False,
    verbose="This action deletes one or more TrackMe blocklist rules by their record identifiers.",
    summary_type=TrackMeResponseSummary,
)
def blocklist_del(
    params: BlocklistDelParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "keys_list": params.keys_list,
    }
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_blocklist/write/blocklist_del",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Blocklist del successful")
    return EntityBatchUpdateOutput(**response)


class MaintenanceKdbAddParams(Params):
    time_start: str = Param(
        description="Maintenance start time (epoch seconds, or datestring YYYY-MM-DDTHH:MM when time_format=datestring)"
    )
    time_end: str = Param(
        description="Maintenance end time (same format as time_start)"
    )
    reason: str = Param(description="The reason for the maintenance window")
    type: str = Param(
        description="The maintenance type, valid options are: planned | unplanned"
    )
    tenants_scope: str | None = Param(
        description="Comma-separated list of tenants in scope; defaults to all tenants (*)"
    )
    no_days_validity: float | None = Param(
        description="Number of days the record is valid for; 0 means valid forever"
    )
    time_format: str | None = Param(
        description="Time format, valid options are: epochtime (default) | datestring"
    )
    add_info: str | None = Param(description="Optional additional information")
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="maintenance kdb add record",
    description="Register a scheduled maintenance knowledge record",
    action_type="generic",
    read_only=False,
    verbose="This action registers a scheduled maintenance window in the TrackMe maintenance knowledge database.",
    summary_type=TrackMeResponseSummary,
)
def maintenance_kdb_add_record(
    params: MaintenanceKdbAddParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    if params.type not in ("planned", "unplanned"):
        raise ActionFailure(
            f"Invalid type={params.type}, valid options are: planned | unplanned"
        )
    body = {
        "time_start": params.time_start,
        "time_end": params.time_end,
        "reason": params.reason,
        "type": params.type,
    }
    if params.tenants_scope:
        body["tenants_scope"] = _csv_to_list(params.tenants_scope)
    if params.no_days_validity is not None:
        body["no_days_validity"] = _int_param(
            params.no_days_validity, "no_days_validity"
        )
    if params.time_format:
        body["time_format"] = params.time_format
    if params.add_info:
        body["add_info"] = params.add_info
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/maintenance_kdb/admin/maintenance_kdb_add_record",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Maintenance KDB add record successful")
    return TrackMeGenericOutput(**response)


class CreateNoteParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_id: str = Param(
        description="The entity identifier (KVstore _key) to attach the note to"
    )
    note: str = Param(description="The note content (Markdown supported)")
    component: str | None = Param(
        description="Optional component (dsm/dhm/mhm/flx/fqm/wlk) for audit scoping"
    )
    validity_days: float | None = Param(
        description="Number of days before the note auto-purges; 0 means permanent"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity create note",
    description="Create a note attached to a TrackMe entity",
    action_type="generic",
    read_only=False,
    verbose="This action attaches an investigation note to a TrackMe entity.",
    summary_type=TrackMeResponseSummary,
)
def entity_create_note(
    params: CreateNoteParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "object_id": params.object_id,
        "note": params.note,
    }
    if params.component:
        body["component"] = params.component
    if params.validity_days is not None:
        body["validity_days"] = _int_param(params.validity_days, "validity_days")
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/notes/write/create_note",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity create note successful")
    return TrackMeGenericOutput(**response)


class AssignLabelsParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_id: str = Param(description="The entity identifier (KVstore _key)")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, fqm, wlk"
    )
    label_names: str | None = Param(
        description="Comma-separated list of label names to assign (unknown names are auto-created). Provide label_names and/or label_ids"
    )
    label_ids: str | None = Param(
        description="Comma-separated list of existing label identifiers to assign. Provide label_ids and/or label_names"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="entity assign labels",
    description="Assign labels to a TrackMe entity",
    action_type="generic",
    read_only=False,
    verbose="This action assigns labels to a TrackMe entity. Unknown label names are auto-created. The resolved label set replaces any existing assignment.",
    summary_type=TrackMeResponseSummary,
)
def entity_assign_labels(
    params: AssignLabelsParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    label_names = _csv_to_list(params.label_names) if params.label_names else []
    label_ids = _csv_to_list(params.label_ids) if params.label_ids else []
    if not label_names and not label_ids:
        # Guard against whitespace-only input that would parse to empty lists and
        # (since this replaces the assignment) silently clear all labels.
        raise ActionFailure(
            "At least one non-empty label name or label id must be provided."
        )
    body = {
        "tenant_id": params.tenant_id,
        "object_id": params.object_id,
        "component": params.component,
    }
    if label_names:
        body["label_names"] = label_names
    if label_ids:
        body["label_ids"] = label_ids
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/labels/write/assign_labels",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Entity assign labels successful")
    return TrackMeGenericOutput(**response)


class LogicalGroupRemoveObjectParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_list: str = Param(
        description="Comma-separated list of entities to remove from all logical groups (supports glob wildcards, but a bare * is refused)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="logical group remove object",
    description="Remove entities from all TrackMe logical groups",
    action_type="generic",
    read_only=False,
    verbose="This action removes one or more entities from all of their TrackMe logical groups.",
    summary_type=TrackMeResponseSummary,
)
def logical_group_remove_object(
    params: LogicalGroupRemoveObjectParams, soar: SOARClient, asset: Asset
) -> EntityBatchUpdateOutput:
    if params.object_list.strip() == "*":
        raise ActionFailure(
            "A bare '*' is not allowed; specify the entities to remove explicitly."
        )
    body = {"tenant_id": params.tenant_id, "object_list": params.object_list}
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_logical_groups/write/logical_groups_remove_object_from_groups",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Logical group remove object successful")
    return EntityBatchUpdateOutput(**response)


def _normalise_group_row(item: dict) -> dict:
    """Surface a logical group's KVstore key as the documented datapath.

    The group collection returns its key as `_key`, so the declared
    `object_group_key` datapath would otherwise always be null here, while the
    same datapath is populated by `logical_group_get_group_for_entity` (which
    maps it explicitly). Keep the two consistent for playbooks.
    """
    row = dict(item)
    if not row.get("object_group_key"):
        row["object_group_key"] = row.get("_key")
    return row


class LogicalGroupOutput(TrackMeOutput):
    object_group_name: str | None = OutputField(
        example_values=["grp-linux-eu-appxxx"], column_name="Group Name"
    )
    object_group_key: str | None = OutputField(
        example_values=["example-group-key"], column_name="Group Key"
    )
    object_group_min_green_percent: str | None = OutputField(example_values=["50"])
    object_group_mtime: str | None = OutputField(example_values=["1713009380.1757667"])
    object_group_mtime_human: str | None = OutputField(
        example_values=["13 Apr 2024 11:56"]
    )


class GetLogicalGroupParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_group_name: str = Param(description="The logical group name")


@app.action(
    name="logical group get",
    description="Get a TrackMe logical group",
    action_type="investigate",
    read_only=True,
    verbose="This action returns a single TrackMe logical group and its members by name.",
    summary_type=TrackMeResponseSummary,
)
def logical_group_get(
    params: GetLogicalGroupParams, soar: SOARClient, asset: Asset
) -> Iterator[LogicalGroupOutput]:
    body = {
        "tenant_id": params.tenant_id,
        "object_group_name": params.object_group_name,
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_logical_groups/logical_groups_get_grp",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Logical group get successful")
    # Deliberately not _result_rows: this endpoint fetches one group by name and
    # returns the bare KVstore record (the handler returns `query_by_id(key)`),
    # not a rows envelope. _result_rows would look for a `query_results` key that
    # is never there and yield nothing at all.
    rows = response if isinstance(response, list) else [response]
    return (LogicalGroupOutput(**_normalise_group_row(item)) for item in rows)


class DeleteLogicalGroupParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_group_name: str = Param(
        description="The logical group name to delete (deletes the group and all of its membership)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="logical group delete",
    description="Delete a TrackMe logical group",
    action_type="generic",
    read_only=False,
    verbose="This action deletes a TrackMe logical group and all membership related to it.",
    summary_type=TrackMeResponseSummary,
)
def logical_group_delete(
    params: DeleteLogicalGroupParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "object_group_name": params.object_group_name,
    }
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_logical_groups/write/logical_groups_del_grp",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Logical group delete successful")
    return TrackMeGenericOutput(**response)


class UpdateLogicalGroupMembersParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    object_group_key: str = Param(
        description="The logical group KVstore _key (obtain it from the logical group get action)"
    )
    object_group_members_green: str = Param(
        description="Comma-separated list of entities to set as the group's green members (send an empty value to clear)"
    )
    object_group_members_red: str = Param(
        description="Comma-separated list of entities to set as the group's red members (send an empty value to clear)"
    )


@app.action(
    name="logical group update members",
    description="Update the members of a TrackMe logical group",
    action_type="generic",
    read_only=False,
    verbose="This action sets the green and red member lists of a TrackMe logical group, identified by its KVstore key.",
    summary_type=TrackMeResponseSummary,
)
def logical_group_update_members(
    params: UpdateLogicalGroupMembersParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "object_group_key": params.object_group_key,
        "object_group_members_green": _csv_to_list(params.object_group_members_green),
        "object_group_members_red": _csv_to_list(params.object_group_members_red),
    }
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_logical_groups/write/logical_groups_update_group_list",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Logical group update members successful")
    return TrackMeGenericOutput(**response)


class VariableDelayParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(description="TrackMe component, valid options are: dsm, dhm")
    object: str | None = Param(
        description="The entity display name. Provide either object or object_id (mutually exclusive)"
    )
    object_id: str | None = Param(
        description="The entity KVstore _key. Provide either object or object_id (mutually exclusive)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


def _variable_delay_body(params: "VariableDelayParams") -> dict:
    if params.component not in ("dsm", "dhm"):
        raise ActionFailure(
            f"Invalid component={params.component}, valid options are: dsm | dhm"
        )
    if bool(params.object) == bool(params.object_id):
        raise ActionFailure("Exactly one of object or object_id must be provided.")
    body = {"tenant_id": params.tenant_id, "component": params.component}
    if params.object:
        body["object"] = params.object
    if params.object_id:
        body["object_id"] = params.object_id
    if params.update_comment:
        body["update_comment"] = params.update_comment
    return body


@app.action(
    name="variable delay enable",
    description="Enable variable delay for a TrackMe entity",
    action_type="generic",
    read_only=False,
    verbose="This action switches a TrackMe entity to an adaptive (variable) delay threshold. A variable delay configuration must already exist for the entity.",
    summary_type=TrackMeResponseSummary,
)
def variable_delay_enable(
    params: VariableDelayParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = _variable_delay_body(params)
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_variable_delay/write/enable",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Variable delay enable successful")
    return TrackMeGenericOutput(**response)


@app.action(
    name="variable delay disable",
    description="Disable variable delay for a TrackMe entity",
    action_type="generic",
    read_only=False,
    verbose="This action switches a TrackMe entity back to a static delay threshold.",
    summary_type=TrackMeResponseSummary,
)
def variable_delay_disable(
    params: VariableDelayParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = _variable_delay_body(params)
    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_variable_delay/write/disable",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Variable delay disable successful")
    return TrackMeGenericOutput(**response)


class DisruptionUpdateMinTimeParams(Params):
    tenant_id: str = Param(description="Tenant identifier")
    component: str = Param(
        description="TrackMe component, valid options are: dsm, dhm, mhm, flx, wlk, fqm"
    )
    keys_list: str = Param(
        description="Comma-separated list of entity KVstore _key values to update"
    )
    disruption_min_time_sec: float = Param(
        description="Minimum disruption time in seconds (0 disables, a positive value sets it)"
    )
    update_comment: str | None = Param(
        description="A comment for the update, added to the audit record, defaults to: API update"
    )


@app.action(
    name="disruption update min time",
    description="Update the minimum disruption time for TrackMe entities",
    action_type="generic",
    read_only=False,
    verbose="This action tunes the minimum disruption time for one or more TrackMe entities to reduce alert flapping.",
    summary_type=TrackMeResponseSummary,
)
def disruption_update_min_time(
    params: DisruptionUpdateMinTimeParams, soar: SOARClient, asset: Asset
) -> TrackMeGenericOutput:
    body = {
        "tenant_id": params.tenant_id,
        "component": params.component,
        "keys_list": params.keys_list,
        "disruption_min_time_sec": _int_param(
            params.disruption_min_time_sec, "disruption_min_time_sec"
        ),
    }
    if params.update_comment:
        body["update_comment"] = params.update_comment

    response = trackme_rest_call(
        asset,
        "/services/trackme/v2/splk_disruption/write/disruption_update_min_time",
        method="post",
        data=json.dumps(body),
    )
    soar.set_summary(TrackMeResponseSummary(trackme_response=json.dumps(response)))
    logger.progress("Disruption update min time successful")
    return TrackMeGenericOutput(**response)


# ---------------------------------------------------------------------------
# Phase 2 — ingestion (on poll): TrackMe alert events -> SOAR containers
#
# TrackMe generates two alert-surface event types, each written to a Splunk
# index and uniquely identified by event_id:
#   * notable  -> index=trackme_notable  sourcetype=trackme:notable
#   * stateful -> index=trackme_summary  sourcetype=trackme:stateful_alerts
# The on_poll action searches those indexes and yields one SOAR container per
# event, mapping event_id to the container source_data_identifier so SOAR
# deduplicates natively (a repeated event_id updates the container instead of
# creating a duplicate). This makes overlapping poll windows safe.
# ---------------------------------------------------------------------------


_INGEST_SOURCES = {
    "notable": ("trackme_notable", "trackme:notable"),
    "stateful": ("trackme_summary", "trackme:stateful_alerts"),
}
_STATE_SEVERITY = {"red": "high", "orange": "medium", "yellow": "low", "green": "low"}
_PRIORITY_SEVERITY = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


def _parse_event(row: dict) -> dict:
    """Return the TrackMe event fields for a Splunk search result row.

    TrackMe writes its alert events as JSON, so the searchable fields live in
    the ``_raw`` payload; extract them (falling back to the row as-is).
    """
    raw = row.get("_raw")
    if isinstance(raw, str):
        with contextlib.suppress(Exception):
            event = json.loads(raw)
            if isinstance(event, dict):
                event.setdefault("_time", row.get("_time"))
                return event
    return row


def _ingest_severity(event: dict) -> str:
    # notable events carry `state`, stateful events carry `object_state`
    state = (event.get("object_state") or event.get("state") or "").lower()
    if state in _STATE_SEVERITY:
        return _STATE_SEVERITY[state]
    return _PRIORITY_SEVERITY.get((event.get("priority") or "").lower(), "medium")


def _event_to_container(event_type: str, event: dict) -> Container:
    event_id = event.get("event_id")
    tenant = event.get("tenant_id", "")
    obj = event.get("object", "")
    state = event.get("object_state") or event.get("state") or ""
    severity = _ingest_severity(event)
    # stateful events carry an alert_status (open / ongoing / closed)
    status = "closed" if event.get("alert_status") == "closed" else "new"
    cef = {k: v for k, v in event.items() if not k.startswith("_")}
    artifact = {
        "name": f"TrackMe {event_type} event",
        "label": "event",
        "cef": cef,
        "source_data_identifier": event_id,
        "severity": severity,
    }
    return Container(
        name=f"TrackMe {event_type} | {tenant} | {obj}"[:250],
        # No label: SOAR applies the asset's own ingest label ("Label to apply
        # to objects from this source"), which is where the operator sets it.
        source_data_identifier=event_id,
        severity=severity,
        status=status,
        description=event.get("status_message")
        or f"TrackMe {event_type} event for {obj} (state={state})",
        artifacts=[artifact],
        data=event,
    )


@app.on_poll()
def on_poll(
    params: OnPollParams, soar: SOARClient, asset: Asset
) -> Iterator[Container]:
    """Ingest TrackMe notable and/or stateful alert events as SOAR containers.

    Events are deduplicated by their TrackMe event_id (mapped to the container
    source_data_identifier), so overlapping poll windows never create duplicates.
    The search window is therefore always the configured ``ingest_lookback``
    rather than the narrow since-last-poll window SOAR supplies: a deliberately
    generous, overlapping window (the default pairs a 5 minute poll interval
    with a -30m lookback) means a late-arriving or briefly missed event is still
    picked up by a subsequent poll, and dedup absorbs the repeats.
    """
    event_type = (asset.ingest_event_type or "both").lower()
    if event_type != "both" and event_type not in _INGEST_SOURCES:
        raise AssetMisconfiguration(
            f"Invalid ingest_event_type '{asset.ingest_event_type}', valid options "
            f"are: both, {', '.join(_INGEST_SOURCES)}"
        )
    types = list(_INGEST_SOURCES) if event_type == "both" else [event_type]

    earliest = asset.ingest_lookback or "-30m"
    latest = "now"

    # Budget across event types so the cap is a per-poll total, not per-search.
    # Validate before converting: 0.5 would truncate to 0 and silently turn the
    # cap off (0 means no limit), and a negative value would skip ingestion.
    max_events = asset.ingest_max_events
    if max_events is None:
        max_events = 0
    if not isfinite(max_events) or max_events < 0 or max_events != int(max_events):
        raise AssetMisconfiguration(
            f"Invalid ingest_max_events '{asset.ingest_max_events}': it must be a "
            "non-negative whole number (0 for no limit)."
        )
    remaining = int(max_events)
    if params.is_manual_poll() and params.container_count:
        manual = int(params.container_count)
        remaining = manual if not remaining else min(remaining, manual)
    capped = bool(remaining)

    # A single tenant narrows to `tenant_id="x"`; several are OR'd together so
    # one poll can cover a subset of tenants.
    tenant_clause = ""
    tenants = _csv_to_list(asset.ingest_tenant) if asset.ingest_tenant else []
    if len(tenants) == 1:
        tenant_clause = f' tenant_id="{tenants[0]}"'
    elif tenants:
        ors = " OR ".join(f'tenant_id="{t}"' for t in tenants)
        tenant_clause = f" ({ors})"

    for etype in types:
        if capped and remaining <= 0:
            logger.progress("Ingestion cap reached, skipping remaining event types")
            break
        index, sourcetype = _INGEST_SOURCES[etype]
        spl = f'search index={index} sourcetype="{sourcetype}"{tenant_clause}'
        logger.progress("Ingesting TrackMe %s events", etype)
        rows = trackme_splunk_search(asset, spl, earliest, latest, remaining)
        for row in rows:
            event = _parse_event(row)
            if not event.get("event_id"):
                continue
            if capped:
                remaining -= 1
            yield _event_to_container(etype, event)


if __name__ == "__main__":
    app.cli()
