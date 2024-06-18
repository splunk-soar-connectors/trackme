#!/usr/bin/python
# -*- coding: utf-8 -*-
# File: trackme_connector.py
#
# Copyright (c) TrackMe Limited, 2024
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
# Python 3 Compatibility imports
from __future__ import print_function, unicode_literals

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2024, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import json

# Phantom App imports
import phantom.app as phantom
# Usage of the consts file is recommended
# from trackme_consts import *
import requests
from bs4 import BeautifulSoup
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector


class RetVal(tuple):

    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class TrackmeConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(TrackmeConnector, self).__init__()

        self._state = None

        # Variable to hold a base_url in case the app makes REST calls
        # Do note that the app json defines the asset config, so please
        # modify this as you deem fit.
        self._splunk_url = None
        self._splunk_token = None
        self._verify_ssl = None
        self._headers = dict()

    def _process_empty_response(self, response, action_result):
        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(
            action_result.set_status(
                phantom.APP_ERROR, "Empty response and no information in the header"
            ),
            None,
        )

    def _process_html_response(self, response, action_result):
        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split("\n")
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = "\n".join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(
            status_code, error_text
        )

        message = message.replace("{", "{{").replace("}", "}}")
        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):
        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Unable to parse JSON response. Error: {0}".format(str(e)),
                ),
                None,
            )

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):
        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, "add_debug_data"):
            action_result.add_debug_data({"r_status_code": r.status_code})
            action_result.add_debug_data({"r_text": r.text})
            action_result.add_debug_data({"r_headers": r.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if "json" in r.headers.get("Content-Type", ""):
            return self._process_json_response(r, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if "html" in r.headers.get("Content-Type", ""):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_response(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            r.status_code, r.text.replace("{", "{{").replace("}", "}}")
        )

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(
        self,
        endpoint,
        action_result,
        params=None,
        body=None,
        headers=None,
        method="get",
        **kwargs,
    ):
        # **kwargs can be any additional parameters that requests.request accepts

        if headers is None:
            headers = self._headers

        resp_json = None

        try:
            request_func = getattr(requests, method)
        except AttributeError:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR, "Invalid method: {0}".format(method)
                ),
                resp_json,
            )

        # Create a URL to connect to
        url = self._splunk_url + endpoint

        """ for debug purposes
        self.debug_print("url : " + url)
        self.debug_print(headers)
        self.debug_print(f"verify: {self._verify_ssl}")
        """

        try:
            r = request_func(
                url,
                data=body,
                params=params,
                headers=headers,
                verify=self._verify_ssl,
                **kwargs,
            )
        except Exception as e:
            return RetVal(
                action_result.set_status(
                    phantom.APP_ERROR,
                    "Error Connecting to server. Details: {0}".format(str(e)),
                ),
                resp_json,
            )

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):
        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/vtenants/show_tenants",
            action_result,
            params=None,
            headers=self._headers,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success
        self.save_progress("Test Connectivity Passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ack_get(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        object_category = param["object_category"]
        object_list = param["object_list"]

        # body
        body = {
            "tenant_id": tenant_id,
            "object_category": object_category,
            "object_list": object_list,
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/ack/get_ack_for_object",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        try:
            ack_response = response[0]
        except Exception:
            ack_response = {
                "ack_comment": "N/A",
                "ack_expiration": "N/A",
                "ack_expiration_datetime": "N/A",
                "ack_is_enabled": 0,
                "ack_mtime": "N/A",
                "ack_mtime_datetime": "N/A",
                "ack_state": "inactive",
                "ack_type": "N/A",
                "object": object_list,
                "object_category": object_category,
            }

        summary["trackme_response"] = json.dumps(ack_response)
        self.debug_print(f"ack_response: {ack_response}")

        # add data
        action_result.add_data(ack_response)

        self.save_progress("Ack get successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ack_manage(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        object_category = param["object_category"]
        object_list = param["object_list"]
        action = param["action"]

        # Optional parameters
        ack_comment = param.get("ack_comment", None)
        ack_period = param.get("ack_period", None)
        ack_type = param.get("ack_type", None)
        update_comment = param.get("update_comment", None)

        # body
        body = {
            "tenant_id": tenant_id,
            "object_category": object_category,
            "object_list": object_list,
            "action": action,
        }

        if ack_comment:
            body["ack_comment"] = ack_comment
        if ack_period:
            body["ack_period"] = ack_period
        if ack_type:
            body["ack_type"] = ack_type
        if update_comment:
            body["update_comment"] = update_comment

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/ack/ack_manage",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        self.debug_print(f"response: {response}")

        summary["trackme_response"] = json.dumps(response)
        # self.debug_print(f'ack_response: {ack_response}')

        # add data
        action_result.add_data(response)

        self.save_progress("Ack manage successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_maintenance_status(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/maintenance/check_global_maintenance_status",
            action_result,
            method="get",
            body=None,
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        self.debug_print(f"response: {response}")
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("Get maintenance mode successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_maintenance_enable(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        add_knowledge_record = param.get("add_knowledge_record")
        maintenance_duration = param.get("maintenance_duration")
        maintenance_mode_end = param.get("maintenance_mode_end")
        maintenance_mode_start = param.get("maintenance_mode_start")
        time_format = param.get("time_format")
        update_comment = param.get("update_comment")

        # body
        body = {}

        if add_knowledge_record:
            body["add_knowledge_record"] = add_knowledge_record
        if maintenance_duration:
            body["maintenance_duration"] = maintenance_duration
        if maintenance_mode_end:
            body["maintenance_mode_end"] = maintenance_mode_end
        if maintenance_mode_start:
            body["maintenance_mode_start"] = maintenance_mode_start
        if time_format:
            body["time_format"] = time_format
        if update_comment:
            body["update_comment"] = update_comment

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/maintenance/global_maintenance_enable",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        self.debug_print(f"response: {response}")

        summary["trackme_response"] = json.dumps(response)
        # self.debug_print(f'ack_response: {ack_response}')

        # add data
        action_result.add_data(response)

        self.save_progress("Maintenance mode enable successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_maintenance_disable(self, param):
        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        update_comment = param.get("update_comment")

        # body
        body = {}

        if update_comment:
            body["update_comment"] = update_comment

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/maintenance/maintenance_disable",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        self.debug_print(f"response: {response}")

        summary["trackme_response"] = json.dumps(response)
        self.debug_print(f"maintenance_response: {response}")

        # add data
        action_result.add_data(response)

        self.save_progress("Maintenance mode disable successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_tenants_ops_status(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param.get("tenant_id", None)

        # body
        body = {}

        if tenant_id:
            body["tenant_id"] = tenant_id

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/configuration/get_tenant_ops_status",
            action_result,
            method="post",
            body=body,
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data (response is a list)
        for item in response:
            action_result.add_data(item)

        self.save_progress("Get TrackMe Tenants Ops status successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_remote_accounts_check_connectivity(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        account = param.get("account", None)

        # body
        body = {}

        # If account is not a parameter, retrieve existing accounts
        remote_accounts_list = []
        if not account:
            ret_val, response = self._make_rest_call(
                "/services/trackme/v2/configuration/list_accounts",
                action_result,
                method="get",
                body=None,
                params=None,
                headers=None,
            )

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # self.debug_print(f"list accounts response: {response}")

            remote_accounts = response.get("accounts", [])
            for remote_account in remote_accounts:
                if remote_account != "local":
                    remote_accounts_list.append(remote_account)

        else:
            remote_accounts_list.append(account)

        # raise an exception is accounts is empty
        if not len(remote_accounts_list) > 0:
            raise Exception(
                "No remote accounts configured were found on this TrackMe instance."
            )

        # Iterate over the accounts and check connectivity
        for remote_account in remote_accounts_list:
            body["account"] = remote_account
            ret_val, response = self._make_rest_call(
                "/services/trackme/v2/configuration/test_remote_account",
                action_result,
                method="post",
                body=json.dumps(body),
                params=None,
                headers=None,
            )

            if phantom.is_fail(ret_val):
                return action_result.get_status()

            # add data
            action_result.add_data(
                {
                    "account": account,
                    "host": response.get("host"),
                    "message": response.get("message"),
                    "status": response.get("status"),
                    "port": response.get("port"),
                }
            )

        # Return success

        self.save_progress("Check remote account connectivity successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ml_outliers_train_models(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        object_value = param["object"]

        # body
        body = {
            "tenant_id": tenant_id,
            "component": component,
            "object": object_value,
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/splk_outliers_engine/write/outliers_train_models",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("Machine Leaning Outliers training successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ml_outliers_run_monitor(self, param):

        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        object_value = param["object"]

        # body
        body = {
            "tenant_id": tenant_id,
            "component": component,
            "object": object_value,
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/splk_outliers_engine/write/outliers_mlmonitor_models",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("Machine Leaning Outliers monitor successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ml_outliers_reset_models(self, param):

        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        object_value = param["object"]

        # body
        body = {
            "tenant_id": tenant_id,
            "component": component,
            "object": object_value,
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/splk_outliers_engine/write/outliers_reset_models",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("Machine Leaning Outliers reset successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ml_outliers_get_models(self, param):

        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        object_value = param["object"]

        # body
        body = {
            "tenant_id": tenant_id,
            "component": component,
            "object": object_value,
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/splk_outliers_engine/outliers_get_rules",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data (response is a list)
        for item in response:
            action_result.add_data(item)

        self.save_progress("Machine Leaning Outliers get successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_ml_outliers_add_period_exclusion(self, param):

        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        object_value = param["object"]
        model_id = param["model_id"]
        earliest = param.get("earliest")
        latest = param.get("latest")

        # body
        body = {
            "tenant_id": tenant_id,
            "component": component,
            "object": object_value,
            "action": "add",
            "model_id": model_id,
            "earliest": earliest,
            "latest": latest,
        }

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/splk_outliers_engine/write/outliers_manage_model_period_exclusion",
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("Machine Leaning Outliers add exclusion period successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_component_get_entity(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        filter_key = param.get("filter_key")
        filter_object = param.get("filter_object")

        # This endpoints expects params especially
        params = {
            "tenant_id": tenant_id,
            "component": component,
        }

        if filter_key:
            params["filter_key"] = filter_key
        if filter_object:
            params["filter_object"] = filter_object

        # make rest call
        ret_val, response = self._make_rest_call(
            "/services/trackme/v2/component/load_component_data",
            action_result,
            method="get",
            body=None,
            params=params,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data (response is a list)
        data_response = response.get("data", [])
        for item in data_response:
            action_result.add_data(item)

        self.save_progress("Get TrackMe entity realtime data successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_component_manage_entity(self, param):  # noqa
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        tenant_id = param["tenant_id"]
        component = param["component"]
        action = param["action"]

        # Optional values should use the .get() function
        filter_object = param.get("filter_object", None)
        filter_key = param.get("filter_key", None)
        extra_attributes = param.get("extra_attributes", None)
        update_comment = param.get("update_comment", None)

        # This endpoints expects params especially
        params = {
            "tenant_id": tenant_id,
            "component": component,
        }

        if filter_key:
            params["filter_key"] = filter_key
        if filter_object:
            params["filter_object"] = filter_object

        # try to parse extra_attributes from JSON string to an object
        try:
            extra_attributes = json.loads(extra_attributes)
        except Exception:
            pass

        # define the target endpoint depending on the requested action
        target_endpoint = None

        # init the rest body
        body = {
            "tenant_id": tenant_id,
        }

        # add filters
        if filter_object:
            body["object_list"] = filter_object
        elif filter_key:
            body["keys_list"] = filter_key

        # add update_comment
        if update_comment:
            body["update_comment"] = update_comment

        # handle action
        allowd_actions = [
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

        if action not in allowd_actions:
            raise Exception(
                f"Invalid action={action}, valid actions are: {allowd_actions}"
            )

        if action in ("enable", "disable"):

            # add action to the body, this is expected by these endpoints
            body["action"] = action

            if component == "dsm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/ds_monitoring"
                )
            elif component == "dhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/dh_monitoring"
                )
            elif component == "mhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/mh_monitoring"
                )
            elif component == "wlk":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/wlk_monitoring"
                )
            elif component == "flx":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/flx_monitoring"
                )

        elif action in ("delete"):

            # deletion type, attempt to retrieve from the key deletion_type in extra_attributes
            if extra_attributes:
                try:
                    deletion_type = extra_attributes["deletion_type"]
                except Exception:
                    deletion_type = "temporary"

            # add to body
            body["deletion_type"] = deletion_type

            if component == "dsm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/ds_delete"
                )
            elif component == "dhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/dh_delete"
                )
            elif component == "mhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/mh_delete"
                )
            elif component == "wlk":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/wlk_delete"
                )
            elif component == "flx":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/flx_delete"
                )

        # manage splk-dsm sampling
        elif action == "manage_dsm_sampling":

            # get sampling action and details from extra_attributes
            if not extra_attributes:
                raise Exception(
                    f"When request action={action}, you must provide in extra_attributes the requested action: enable|disable|reset|run|update_no_records"
                )
            else:
                try:
                    sampling_action = extra_attributes["action"]
                except Exception:
                    raise Exception(
                        "sampling action must be set in extra_attributes, valid actions are: enable|disable|reset|run|update_no_records"
                    )
                if sampling_action not in (
                    "enable",
                    "disable",
                    "reset",
                    "run",
                    "update_no_records",
                ):
                    raise Exception(
                        f"Illegal action={sampling_action}, valid actions are: enable|disable|reset|run|update_no_records"
                    )
                else:
                    body["action"] = sampling_action

            # handle sampling action
            if sampling_action in ("enable", "disable", "reset", "run"):

                # set endpoint
                target_endpoint = (
                    "/services/trackme/v2/splk_dsm/write/ds_manage_data_sampling"
                )

            elif sampling_action in ("update_no_records"):

                # set endpoint
                target_endpoint = "/services/trackme/v2/splk_dsm/write/ds_update_data_sampling_records_nr"

                # retrieve the number of records requested (data_sampling_nr)
                try:
                    data_sampling_nr = extra_attributes["data_sampling_nr"]
                    if not isinstance(data_sampling_nr, int):
                        raise Exception(
                            f"action={action} requires data_sampling_nr to be set in extra_attributes as an integer value."
                        )

                    else:
                        body["data_sampling_nr"] = data_sampling_nr

                except Exception:
                    raise Exception(
                        f"action={action} requires data_sampling_nr to be set in extra_attributes as an integer value."
                    )

        # update hours ranges of monitoring
        elif action == "update_hours_ranges":

            # get the hours ranges from extra_attributes
            if not extra_attributes:
                raise Exception(
                    f"When request action={action}, you must provide in extra_attributes the hours_ranges parameter"
                )
            else:
                try:
                    hours_ranges = extra_attributes["hours_ranges"]
                except Exception:
                    raise Exception(
                        f"hours_ranges must be set in extra_attributes when action={action}"
                    )

            # verify the input "all_ranges", "manual:08h-to-20h", or a list of integers
            if not isinstance(hours_ranges, list):
                if hours_ranges not in ("all_ranges", "manual:08h-to-20h"):
                    raise Exception(
                        f"hours_ranges must be all_ranges, manual:08h-to-20h, or a list of integers, but got: {hours_ranges}"
                    )

            # add to body
            body["monitoring_hours_ranges"] = hours_ranges

            # set endpoint
            if component == "dsm":
                target_endpoint = f"/services/trackme/v2/splk_{component}/write/ds_update_hours_ranges"
            elif component == "dhm":
                target_endpoint = f"/services/trackme/v2/splk_{component}/write/dh_update_hours_ranges"
            elif component == "mhm":
                target_endpoint = f"/services/trackme/v2/splk_{component}/write/mh_update_hours_ranges"
            elif component == "wlk":
                target_endpoint = f"/services/trackme/v2/splk_{component}/write/wlk_update_hours_ranges"
            elif component == "flx":
                target_endpoint = f"/services/trackme/v2/splk_{component}/write/flx_update_hours_ranges"

        # update week days of monitoring
        elif action == "update_wdays":

            # get the hours ranges from extra_attributes
            if not extra_attributes:
                raise Exception(
                    f"When request action={action}, you must provide in extra_attributes the wdays parameter"
                )
            else:
                try:
                    wdays = extra_attributes["wdays"]
                except Exception:
                    raise Exception(
                        f"wdays must be set in extra_attributes when action={action}"
                    )

            # verify the input "all_days", "manual:monday-to-friday", "manual:monday-to-saturday", or a list of integers
            if not isinstance(wdays, list):
                if wdays not in (
                    "all_days",
                    "manual:monday-to-friday",
                    "manual:monday-to-saturday",
                ):
                    raise Exception(
                        f"wdays must be all_days, manual:monday-to-friday, manual:monday-to-saturday, or a list of integers, but got: {wdays}"
                    )

            # add to body
            body["monitoring_wdays"] = wdays

            # set endpoint
            if component == "dsm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/ds_update_wdays"
                )
            elif component == "dhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/dh_update_wdays"
                )
            elif component == "mhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/mh_update_wdays"
                )
            elif component == "wlk":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/wlk_update_wdays"
                )
            elif component == "flx":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/flx_update_wdays"
                )

        # update_priority
        elif action == "update_priority":

            # get the priroity from extra_attributes, valid options are: low, medium, high
            if not extra_attributes:
                raise Exception(
                    f"When request action={action}, you must provide in extra_attributes the priority parameter"
                )
            else:
                try:
                    priority = extra_attributes["priority"]
                except Exception:
                    raise Exception(
                        f"priority must be set in extra_attributes when action={action}"
                    )

            if priority not in ("low", "medium", "high"):
                raise Exception(
                    f"priority must be low, medium, or high, but got: {priority}"
                )

            # add to body
            body["priority"] = priority

            # set endpoint
            if component == "dsm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/ds_update_priority"
                )
            elif component == "dhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/dh_update_priority"
                )
            elif component == "mhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/mh_update_priority"
                )
            elif component == "wlk":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/wlk_update_priority"
                )
            elif component == "flx":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/flx_update_priority"
                )

        # update_lag_policy
        elif action == "update_lag_policy":

            # from extra_attributes, extract and check allow_adaptive_delay (optional)
            allow_adaptive_delay = extra_attributes.get("allow_adaptive_delay", None)
            if allow_adaptive_delay:
                if allow_adaptive_delay not in ("true", "false"):
                    raise Exception(
                        f"allow_adaptive_delay must be true or false, but got: {allow_adaptive_delay}"
                    )
                body["allow_adaptive_delay"] = allow_adaptive_delay

            # from extra_attributes, extract and check data_lag_alert_kpis (optional)
            data_lag_alert_kpis = extra_attributes.get("data_lag_alert_kpis", None)
            if data_lag_alert_kpis:
                if data_lag_alert_kpis not in (
                    "all_kpis",
                    "lag_ingestion_kpi",
                    "lag_event_kpi",
                ):
                    raise Exception(
                        f"data_lag_alert_kpis must be all_kpis, lag_ingestion_kpi, or lag_event_kpi, but got: {data_lag_alert_kpis}"
                    )
                body["data_lag_alert_kpis"] = data_lag_alert_kpis

            # from extra_attributes, extract and check data_max_delay_allowed (optional)
            data_max_delay_allowed = extra_attributes.get(
                "data_max_delay_allowed", None
            )
            if data_max_delay_allowed:
                if not isinstance(data_max_delay_allowed, int):
                    raise Exception(
                        f"data_max_delay_allowed must be an integer, but got: {data_max_delay_allowed}"
                    )
                body["data_max_delay_allowed"] = data_max_delay_allowed

            # from extra_attributes, extract and check data_max_lag_allowed (optional)
            data_max_lag_allowed = extra_attributes.get("data_max_lag_allowed", None)
            if data_max_lag_allowed:
                if not isinstance(data_max_lag_allowed, int):
                    raise Exception(
                        f"data_max_lag_allowed must be an integer, but got: {data_max_lag_allowed}"
                    )
                body["data_max_lag_allowed"] = data_max_lag_allowed

            # from extra_attributes, extract and check data_override_lagging_class (optional)
            data_override_lagging_class = extra_attributes.get(
                "data_override_lagging_class", None
            )
            if data_override_lagging_class:
                if data_override_lagging_class not in ("true", "false"):
                    raise Exception(
                        f"data_override_lagging_class must be true or false, but got: {data_override_lagging_class}"
                    )
                body["data_override_lagging_class"] = data_override_lagging_class

            # from extra_attributes, extract and check future_tolerance (optional)
            future_tolerance = extra_attributes.get("future_tolerance", None)
            if future_tolerance:
                if not isinstance(future_tolerance, int):
                    raise Exception(
                        f"future_tolerance must be an integer, but got: {future_tolerance}"
                    )
                body["future_tolerance"] = future_tolerance

            # from extra_attributes, extract and check splk_dhm_alerting_policy
            splk_dhm_alerting_policy = extra_attributes.get(
                "splk_dhm_alerting_policy", None
            )
            if splk_dhm_alerting_policy:
                if component != "dhm":
                    raise Exception(
                        f"splk_dhm_alerting_policy is only valid for dhm component, but got: {component}"
                    )

                if splk_dhm_alerting_policy not in (
                    "all_kpis",
                    "lag_ingestion_kpi",
                    "lag_event_kpi",
                ):
                    raise Exception(
                        f"splk_dhm_alerting_policy must be all_kpis, lag_ingestion_kpi, or lag_event_kpi, but got: {splk_dhm_alerting_policy}"
                    )
                body["splk_dhm_alerting_policy"] = splk_dhm_alerting_policy

            # set endpoint
            if component == "dsm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/ds_update_lag_policy"
                )
            elif component == "dhm":
                target_endpoint = (
                    f"/services/trackme/v2/splk_{component}/write/dh_update_lag_policy"
                )
            else:
                raise Exception(
                    f'Component "{component}" does not support action "{action}"'
                )

        # update_dcount_host
        elif action == "update_dcount_host":

            # this action is valid for dsm only
            if component != "dsm":
                raise Exception(
                    f'Component "{component}" does not support action "{action}"'
                )

            # we expect:
            # min_dcount_field: The dictinct count metric to be used for this entity,
            # valid options are: avg_dcount_host_5m, latest_dcount_host_5m, perc95_dcount_host_5m,
            # stdev_dcount_host_5m, global_dcount_host
            # min_dcount_host: minimal accepted number of distinct count hosts, must be an integer or the string any

            # get the min_dcount_host from extra_attributes
            try:
                min_dcount_host = extra_attributes["min_dcount_host"]
                if not isinstance(min_dcount_host, int):
                    if min_dcount_host != "any":
                        raise Exception(
                            f'min_dcount_host must be an integer or the keyworkd "any" to disable it, but got: {min_dcount_host}'
                        )
                body["min_dcount_host"] = min_dcount_host

            except Exception:
                raise Exception(
                    f"min_dcount_host must be set in extra_attributes when action={action}"
                )

            # get the min_dcount_field from extra_attributes
            if min_dcount_host != "any":
                if not extra_attributes:
                    raise Exception(
                        f"When request action={action}, you must provide in extra_attributes the min_dcount_field parameter"
                    )
                else:
                    try:
                        min_dcount_field = extra_attributes["min_dcount_field"]
                    except Exception:
                        raise Exception(
                            f"min_dcount_field must be set in extra_attributes when action={action}"
                        )

                    if min_dcount_field not in (
                        "avg_dcount_host_5m",
                        "latest_dcount_host_5m",
                        "perc95_dcount_host_5m",
                        "stdev_dcount_host_5m",
                        "global_dcount_host",
                    ):
                        raise Exception(
                            "min_dcount_field must be avg_dcount_host_5m, latest_dcount_host_5m, "
                            f"perc95_dcount_host_5m, stdev_dcount_host_5m, or global_dcount_host, but got: {min_dcount_field}"
                        )

                    body["min_dcount_field"] = min_dcount_field

            # set endpoint (this action is only for dsm)
            target_endpoint = (
                "/services/trackme/v2/splk_dsm/write/ds_update_min_dcount_host"
            )

        # update_manual_tags
        elif action == "update_manual_tags":

            # this action is valid for dsm only
            if component != "dsm":
                raise Exception(
                    f'Component "{component}" does not support action "{action}"'
                )

            # we expect:
            # tags_manual: A comma seperated list of tags to be applied to the entities, to purge all manual tags, send an empty string

            # get the tags_manual from extra_attributes
            try:
                tags_manual = extra_attributes["tags_manual"]
                if not isinstance(tags_manual, str):
                    raise Exception(
                        f"tags_manual must be a string, but got: {tags_manual}"
                    )
                body["tags_manual"] = tags_manual

            except Exception:
                raise Exception(
                    f"tags_manual must be set in extra_attributes when action={action}"
                )

            # set endpoint (this action is only for dsm)
            target_endpoint = (
                "/services/trackme/v2/splk_dsm/write/ds_update_manual_tags"
            )

        # make rest call
        ret_val, response = self._make_rest_call(
            target_endpoint,
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("Manage TrackMe entity successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_logical_group_manage(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        tenant_id = param["tenant_id"]
        action = param["action"]

        # Optional values should use the .get() function
        object_group_name = param.get("object_group_name", None)
        object_list = param.get("object_list", None)
        object_group_min_green_percent = param.get(
            "object_group_min_green_percent", None
        )
        update_comment = param.get("update_comment", None)

        # init body
        body = {
            "tenant_id": tenant_id,
        }

        if object_group_min_green_percent:
            body["object_group_min_green_percent"] = object_group_min_green_percent

        # add update_comment
        if update_comment:
            body["update_comment"] = update_comment

        # handle action
        allowed_actions = [
            "show",
            "associate",
            "unassociate",
        ]

        if action not in allowed_actions:
            raise Exception(
                f"Invalid action={action}, valid actions are: {allowed_actions}"
            )

        # set endpoint
        if action == "show":
            target_endpoint = (
                "/services/trackme/v2/splk_logical_groups/logical_groups_collection"
            )
        elif action in ("associate", "unassociate"):

            if action == "associate":
                body["action"] = action
                body["object_group_name"] = object_group_name
                body["object_list"] = object_list
                if object_group_min_green_percent:
                    body["object_group_min_green_percent"] = (
                        object_group_min_green_percent
                    )

            elif action == "unassociate":
                body["action"] = action
                body["object_group_name"] = object_group_name
                body["object_list"] = object_list

            target_endpoint = "/services/trackme/v2/splk_logical_groups/write/logical_groups_associate_group"

        # make rest call
        ret_val, response = self._make_rest_call(
            target_endpoint,
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        for item in response:
            action_result.add_data(item)

        self.save_progress("Manage TrackMe logical group successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_logical_group_get_group_for_entity(self, param):
        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        tenant_id = param["tenant_id"]
        filter_object = param["filter_object"]

        # init body
        body = {
            "tenant_id": tenant_id,
        }

        # set endpoint
        target_endpoint = (
            "/services/trackme/v2/splk_logical_groups/logical_groups_collection"
        )

        # we will first retrieve and parse the logical groups and seach for this entity
        entity_associated_logical_groups = []

        # make rest call
        ret_val, response = self._make_rest_call(
            target_endpoint,
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        for item in response:
            object_group_name = item.get("object_group_name")
            object_group_key = item.get("_key")
            object_group_members = item.get("object_group_members", [])

            # loop through object_group_members
            for member in object_group_members:
                if member == filter_object:
                    entity_associated_logical_groups.append(
                        {
                            "object_group_name": object_group_name,
                            "object_group_key": object_group_key,
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

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(entity_associated_logical_groups)

        # add data
        if len(entity_associated_logical_groups) > 0:
            for item in entity_associated_logical_groups:
                action_result.add_data(item)

        else:  # entity has no group
            action_result.add_data(
                {
                    "object_group_name": None,
                    "object_group_key": None,
                    "object_group_members": [],
                    "object_group_min_green_percent": None,
                    "object_group_mtime": None,
                    "object_group_mtime_human": None,
                }
            )

        self.save_progress(
            "Manage TrackMe get logical group information for TrackMe entity successful"
        )
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_smart_status(self, param):

        self.save_progress(
            "In action handler for: {0}".format(self.get_action_identifier())
        )

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Parameters
        tenant_id = param["tenant_id"]
        component = param["component"]
        object_value = param["object"]

        # body
        body = {
            "tenant_id": tenant_id,
            "object": object_value,
        }

        # target_endpoint
        target_endpoint = None
        if component == "dsm":
            target_endpoint = "/services/trackme/v2/splk_smart_status/ds_smart_status"
        elif component == "dhm":
            target_endpoint = "/services/trackme/v2/splk_smart_status/dh_smart_status"
        elif component == "mhm":
            target_endpoint = "/services/trackme/v2/splk_smart_status/mh_smart_status"
        elif component == "wlk":
            target_endpoint = "/services/trackme/v2/splk_smart_status/wlk_smart_status"
        elif component == "flx":
            target_endpoint = "/services/trackme/v2/splk_smart_status/flx_smart_status"

        # make rest call
        ret_val, response = self._make_rest_call(
            target_endpoint,
            action_result,
            method="post",
            body=json.dumps(body),
            params=None,
            headers=None,
        )

        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Return success

        # Add a dictionary that is made up of the most important values from data into the summary
        summary = action_result.update_summary({})

        # resp_data
        # self.debug_print(f'response: {response}')
        summary["trackme_response"] = json.dumps(response)

        # add data
        action_result.add_data(response)

        self.save_progress("SmartStatus run successful")
        return action_result.set_status(phantom.APP_SUCCESS)

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "ack_get":
            ret_val = self._handle_ack_get(param)

        if action_id == "ack_manage":
            ret_val = self._handle_ack_manage(param)

        if action_id == "maintenance_status":
            ret_val = self._handle_maintenance_status(param)

        if action_id == "maintenance_enable":
            ret_val = self._handle_maintenance_enable(param)

        if action_id == "maintenance_disable":
            ret_val = self._handle_maintenance_disable(param)

        if action_id == "tenants_ops_status":
            ret_val = self._handle_tenants_ops_status(param)

        if action_id == "remote_accounts_check_connectivity":
            ret_val = self._handle_remote_accounts_check_connectivity(param)

        if action_id == "ml_outliers_train_models":
            ret_val = self._handle_ml_outliers_train_models(param)

        if action_id == "ml_outliers_run_monitor":
            ret_val = self._handle_ml_outliers_run_monitor(param)

        if action_id == "ml_outliers_reset_models":
            ret_val = self._handle_ml_outliers_reset_models(param)

        if action_id == "ml_outliers_get_models":
            ret_val = self._handle_ml_outliers_get_models(param)

        if action_id == "ml_outliers_add_period_exclusion":
            ret_val = self._handle_ml_outliers_add_period_exclusion(param)

        if action_id == "component_get_entity":
            ret_val = self._handle_component_get_entity(param)

        if action_id == "component_manage_entity":
            ret_val = self._handle_component_manage_entity(param)

        if action_id == "logical_group_get_group_for_entity":
            ret_val = self._handle_logical_group_get_group_for_entity(param)

        if action_id == "logical_group_manage":
            ret_val = self._handle_logical_group_manage(param)

        if action_id == "smart_status":
            ret_val = self._handle_smart_status(param)

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        return ret_val

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        """
        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        self._base_url = config.get("base_url")
        self._splunk_url = config.get("splunk_url")
        self._verify_ssl = config.get("verify_ssl")
        self._splunk_token = config.get("splunk_token")
        self._headers = {"Authorization": f"Bearer {self._splunk_token}"}

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = TrackmeConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=False)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=False, data=data, headers=headers)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = TrackmeConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    exit(0)


if __name__ == "__main__":
    main()
