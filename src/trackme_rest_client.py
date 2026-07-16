# Copyright (c) TrackMe Limited, 2024-2026
#
# REST client helper for the TrackMe Splunk SOAR connector.
#
# This is the SDK-era replacement for the legacy BaseConnector ``_make_rest_call``
# / ``_process_response`` methods. It talks to the TrackMe REST API endpoints
# exposed by Splunkd over HTTPS (generally port 8089), authenticating with a
# Splunk bearer token taken from the asset configuration.
#
# Behaviour is kept faithful to the legacy connector so that existing customer
# playbooks keep working unchanged; the only functional differences are:
#   * errors are raised as SDK exceptions (ActionFailure / AssetMisconfiguration)
#     instead of being folded into an ActionResult status, and
#   * HTML error bodies are surfaced as plain text (the ``bs4`` dependency is
#     no longer required).

import requests
import urllib3
from soar_sdk.exceptions import ActionFailure, AssetMisconfiguration
from soar_sdk.logging import getLogger


logger = getLogger()

# Default per-request timeout (seconds) when the asset does not override it.
DEFAULT_TIMEOUT = 300

# When SSL verification is disabled, requests emits an InsecureRequestWarning on
# every call; suppress it to keep the action logs clean.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _process_response(response: requests.Response):
    """Parse a TrackMe REST API response, mirroring the legacy connector.

    Returns the decoded JSON payload (dict or list) on success, or an empty
    dict for an empty 200 response. Raises AssetMisconfiguration on 401/403
    (authentication / capability problems) and ActionFailure otherwise.
    """
    # Classify authentication / capability errors first, independent of the
    # response content-type or body shape (a 401/403 can carry an empty or
    # malformed body).
    if response.status_code in (401, 403):
        raise AssetMisconfiguration(
            f"Authentication/authorization failed (HTTP {response.status_code}). "
            f"Data from server: {response.text}"
        )

    content_type = response.headers.get("Content-Type", "")

    # JSON response (the normal case for the TrackMe REST API)
    if "json" in content_type:
        try:
            resp_json = response.json()
        except Exception as e:
            raise ActionFailure(f"Unable to parse JSON response. Error: {e!s}") from e

        if 200 <= response.status_code < 399:
            return resp_json

        raise ActionFailure(
            f"Error from server. Status Code: {response.status_code} "
            f"Data from server: {response.text}"
        )

    # Empty response
    if not response.text:
        if response.status_code == 200:
            return {}
        raise ActionFailure(
            f"Empty response and no information in the header "
            f"(Status Code: {response.status_code})"
        )

    # Any other body (typically an HTML error page from a proxy or Splunkd)
    error_text = response.text.replace("{", "{{").replace("}", "}}")
    raise ActionFailure(
        f"Status Code: {response.status_code}. Data from server:\n{error_text}\n"
    )


def trackme_rest_call(
    asset,
    endpoint: str,
    method: str = "get",
    params: dict | None = None,
    data=None,
):
    """Perform a REST call to the TrackMe API and return the parsed payload.

    Args:
        asset: The configured asset (provides ``splunk_url``, ``splunk_token``
            and ``verify_ssl``).
        endpoint: The TrackMe REST endpoint path, e.g.
            ``/services/trackme/v2/ack/get_ack_for_object``.
        method: HTTP method name (``get``, ``post`` ...).
        params: Optional query-string parameters.
        data: Optional request body, passed verbatim to ``requests`` as ``data``
            (callers pass a JSON string for the endpoints that expect a JSON
            body, matching the legacy connector's wire format).

    Raises:
        ActionFailure: on connection errors or non-auth server errors.
        AssetMisconfiguration: on authentication / capability errors (401/403).
    """
    headers = {"Authorization": f"Bearer {asset.splunk_token}"}
    url = f"{asset.splunk_url}{endpoint}"
    timeout = getattr(asset, "timeout", None) or DEFAULT_TIMEOUT

    try:
        request_func = getattr(requests, method)
    except AttributeError as e:
        raise ActionFailure(f"Invalid method: {method}") from e

    logger.progress("Calling TrackMe endpoint: %s", endpoint)

    try:
        response = request_func(
            url,
            data=data,
            params=params,
            headers=headers,
            verify=bool(asset.verify_ssl),
            timeout=timeout,
        )
    except Exception as e:
        raise ActionFailure(f"Error Connecting to server. Details: {e!s}") from e

    return _process_response(response)


def trackme_splunk_search(
    asset,
    spl: str,
    earliest: str = "-24h",
    latest: str = "now",
    max_count: int = 1000,
) -> list:
    """Run a blocking Splunk oneshot search via Splunkd and return the result rows.

    Used by the ingest (on poll) action to pull TrackMe alert events from their
    Splunk indexes (the events are not exposed by a TrackMe REST endpoint).

    Args:
        asset: The configured asset (Splunkd URL, token, verify_ssl, timeout).
        spl: The search string (a leading ``search`` is added if missing).
        earliest / latest: Splunk time modifiers for the search window.
        max_count: Maximum number of results to return (0 means no limit).
    """
    spl = spl.strip()
    if not spl.startswith(("search", "|")):
        spl = f"search {spl}"

    logger.progress("Running Splunk search for ingestion")
    # Routed through trackme_rest_call so bearer auth, TLS, timeout and error
    # classification stay in one place; requests form-encodes the dict body,
    # which is what the Splunkd search endpoint expects.
    response = trackme_rest_call(
        asset,
        "/services/search/jobs",
        method="post",
        data={
            "search": spl,
            "output_mode": "json",
            "exec_mode": "oneshot",
            "earliest_time": earliest,
            "latest_time": latest,
            "count": str(max_count),
        },
    )
    rows = response.get("results") if isinstance(response, dict) else None
    return rows if isinstance(rows, list) else []
