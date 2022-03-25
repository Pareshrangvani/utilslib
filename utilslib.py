import requests
from json_logic.builtins import BUILTINS
from enums import HttpMethodEnum
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from mysql_mgr import *
from datetime import datetime, date, timedelta
import dateutil.parser as parser
import string
import random
import shortuuid
import hashlib
from json_logic import jsonLogic

DT_FMT_HMSf = '%H%M%S%f'


def invoke_http_request(endpoint, method, headers, payload=None, json_data=None, timeout=61):
    """ here two exception block. one is for request exception and other is for json decoder exception.
    RequestException raise when some error occur in API response
    JSONDecodeError: sometimes we don't know our API response is in json format or not so, when we return
    response.json() it raise error if it not json format.
    """
    _request = requests_retry_session()
    _request.headers.update({
        **headers
    })
    try:
        response = None
        if method == HttpMethodEnum.GET.value:
            response = _request.get(url=endpoint, data=payload, timeout=timeout)
        if method == HttpMethodEnum.POST.value:
            response = _request.post(url=endpoint, data=payload, json=json_data, timeout=timeout)
        if method == HttpMethodEnum.PUT.value:
            response = _request.put(url=endpoint, data=payload, timeout=timeout)
        if method == HttpMethodEnum.DELETE.value:
            response = _request.delete(url=endpoint, data=payload, timeout=timeout)
        log_failed_http_request(endpoint, response.text, response.status_code)
        return response.json(), response.status_code
    except requests.exceptions.RequestException:
        print('Error raised while invoking %s', endpoint)
        raise
    except json.decoder.JSONDecodeError:
        print('JSON Decode Error raised while invoking %s', endpoint)
        return response, response.status_code


def requests_retry_session(
        retries=3,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
        session=None):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def log_failed_http_request(endpoint, response, status_code):
    if not is_success_request(status_code):
        msg = 'Http {} | Error-{} : {}'.format(endpoint, status_code, response)
        print('Error raised ', msg)


def is_success_request(status_code):
    return 200 <= status_code <= 299


def date_within_next(date, number, period):
    if period == "days":
        return datetime.utcnow() <= str_to_datetime(date) <= (
                datetime.utcnow() + timedelta(days=int(number)))
    elif period == "weeks":
        return datetime.utcnow() <= str_to_datetime(date) <= (
                datetime.utcnow() + timedelta(weeks=int(number)))


def date_within_last(date, number, period):
    if period == "days":
        return (datetime.utcnow() - timedelta(
            days=int(number))) <= str_to_datetime(date) <= datetime.utcnow()
    elif period == "weeks":
        return (datetime.utcnow() - timedelta(
            weeks=int(number))) <= str_to_datetime(date) <= datetime.utcnow()


def str_to_datetime(date_time, str_format="%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(date_time, str_format)


def get_datetime(date_string):
    """ this function will return datetime object with 2022-01-10 00:00:00 format"""
    return parser.parse(date_string)


def get_unique_key():
    """
    This method is used to get 32 bit unique key
    Steps:
        1. Get current timestamp in "%H%M%S%f" string format
        2. Select random string of 8 char and add with timestamp
        3. Generate 12 bit random string using shortuuid
    :return: 32 bit Unique key
    """

    timestamp = datetime.now().strftime(DT_FMT_HMSf)
    random_str = timestamp + ''.join(random.choice(string.digits + string.ascii_letters) for _ in range(8))
    uuid_str = shortuuid.ShortUUID().random(length=12)
    return '{}{}'.format(uuid_str, random_str)


ops = {
    **BUILTINS,
    'starts_with': lambda data, a, b: a.startswith(b),
    'ends_with': lambda data, a, b: a.endswith(b),
    'date_between': lambda data, a, b, c: str_to_datetime(b) <= str_to_datetime(a) <= str_to_datetime(c),
    'date_within_next': lambda data, a, b, c: date_within_next(a, b, c),
    'date_within_last': lambda data, a, b, c: date_within_last(a, b, c),
    'date_after': lambda data, a, b: str_to_datetime(a) > str_to_datetime(b),
    'date_before': lambda data, a, b: str_to_datetime(a) < str_to_datetime(b),
    'date_yesterday': lambda data, a: str_to_datetime(a).date() == datetime.utcnow().date() - timedelta(days=1),
    'date_today': lambda data, a: str_to_datetime(a).date() == datetime.utcnow().date(),
    'date_tomorrow': lambda data, a: str_to_datetime(a).date() == datetime.utcnow().date() + timedelta(days=1),
    'date_is_empty': lambda data, a: a == ""
}


def buildquery(json_object):
    if 'field' in json_object.keys():
        # In this case the json_object is an object which describes a single query
        if json_object.get("operator") != 'BETWEEN':
            return json_object.get("field") + " " + json_object.get("operator") + " '" + json_object.get("value") + "' "
        else:
            return json_object.get("field") + " " + json_object.get("operator") + " '" + json_object.get(
                "value") + "' " + 'AND' + " '" + json_object.get("value2") + "' "

    # else it is an "condition+filters" JSON - Object
    else:
        i = 0
        # result = "("
        result = ""
        filter_array = json_object.get("filters")
        while i < len(filter_array):
            # Add (maybe nested) expression
            result += " " + buildquery(filter_array[i]) + " "

            # if we are already at the end of our filters array, do not add condition string
            # or we WOULD end up with something like ( a OR b OR c OR )

            if i != len(filter_array) - 1:
                result += json_object.get("condition")
            i = i + 1
        # result += ")"
        return result


module_id_dict = {'Campaigns': '1', 'Invoice': '2', 'SalesOrder': '3', 'PurchaseOrder': '4', 'Quotes': '5', 'Faq': '6',
                  'Vendors': '7', 'PriceBooks': '8', 'Calendar': '9', 'Leads': '10', 'Accounts': '11', 'Contacts': '12',
                  'Potentials': '13', 'Products': '14', 'Documents': '15', 'Emails': '16', 'HelpDesk': '17',
                  'Events': '18', 'Users': '19', 'Groups': '20', 'Currency': '21', 'DocumentFolders': '22',
                  'CompanyDetails': '23', 'Services': '24', 'ServiceContracts': '25', 'PBXManager': '26',
                  'ProjectMilestone': '27', 'ProjectTask': '28', 'Project': '29', 'Assets': '30', 'ModComments': '31',
                  'SMSNotifier': '32', 'LineItem': '33', 'Tax': '34', 'ProductTaxes': '35', 'PolicyPlan': '36',
                  'Commission': '37', 'AgentCommission': '38', 'VTERoundRobin': '41', 'VTESLALog': '42',
                  'VTEButtons': '43', 'VTEEmailPreview': '46', 'VReports': '49', 'RepliedSMSLog': '51',
                  'VTELabelEditor': '55', 'ToolbarIcons': '68', 'VTEFeedback': '88', 'AgentCommissionCFG': '90',
                  'Predicting': '91', 'Notifications': '95'}


def get_session_name(user_access_key, vtiger_url, vtiger_username):
    # get challenge
    headers = {'content-type': 'application/json'}

    challenge_url = '{vtiger_url}/webservice.php?operation=getchallenge&username={vtiger_username}'.format(
        vtiger_url=vtiger_url, vtiger_username=vtiger_username)

    response, status = invoke_http_request(challenge_url, 'GET', headers=headers)

    if status == 200 and response.get('result', ''):
        token = response.get('result').get('token')

        # get md5 encoded access key

        access_key = token + user_access_key
        result = hashlib.md5(access_key.encode())
        access_key_encoded = result.hexdigest()

        # login
        login_url = "{vtiger_url}/webservice.php".format(vtiger_url=vtiger_url)
        payload = 'operation=login&username={vtiger_username}&accessKey={access_key}'.format(
            access_key=access_key_encoded, vtiger_username=vtiger_username)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        response, status = invoke_http_request(login_url, 'POST', headers, payload)

        if status == 200 and response.get('result', ''):
            return response.get('result').get('sessionName')


def trigger_workflow(workflow, event_type, data, service_url):
    """ call API to trigger any workflow
        Required params: 1. workflow 2. event_type 3. data"""

    headers = {'content_type': 'application/json'}
    data['eventtype'] = event_type

    endpoint = '{service_url}/api/v1/trigger_external_workflow'.format(service_url=service_url)

    if data:
        payload = {
            "workflow": workflow,
            "data": data
        }

    response, status = invoke_http_request(endpoint, 'POST', headers, json_data=payload, timeout=61)
    print("response", response, "status", status)


def json_logic_replace_data(rule, data, string_data=None, json_data=None):
    replace_data = jsonLogic(rule, data, ops)
    it = iter(replace_data)
    res_dct = dict(zip(it, it))

    if string_data:
        for key, val in res_dct.items():
            string_data = string_data.replace(key, str(val))

        return string_data
    elif json_data:

        str_json_data = json.dumps(json_data)
        for key, val in res_dct.items():
            str_json_data = str_json_data.replace(key, str(val))
        json_data = json.loads(str_json_data)
        return json_data


def run_external_workflow(conf, external_workflow_config, vtiger_access):
    """ this function will get check if conditions are satisfied for triggering external workflow or not.
        input:  1.conf : conf object
                2.external_workflow_config : config dictionary containing workflow, event_type, search_object
        1. get configs and create query.
        2. replace data using json logic.
        3. call trigger workflow function if conditions are satisfied.
        """

    data = conf.get('data', '')
    workflow = external_workflow_config.get('workflow', '')
    event_type = external_workflow_config.get('event_type', '')

    search_object = external_workflow_config.get('search_object', '')

    if search_object and search_object.get('condition_object', ''):
        rule = search_object.get('rule', '')

        # prepare query
        condition = buildquery(search_object.get('condition_object'))
        module = search_object.get('search_module').get('name')
        limit = str(search_object.get('fetch_record'))

        order_by = search_object.get('sort').get('column') + " " + search_object.get('sort').get('type', "")

        query = 'SELECT * FROM {module} WHERE {condition} order by {order_by} LIMIT {limit};'.format(
            module=module,
            condition=condition,
            order_by=order_by,
            limit=limit)

        # replace variable name with data using JSON_LOGIC.

        if rule:
            query = json_logic_replace_data(rule, conf, query)

        if vtiger_access.get('user_access_key', ''):
            session_name = get_session_name(vtiger_access.get('user_access_key'), vtiger_access.get('vtiger_url'),
                                            vtiger_access.get('vtiger_username'))
            if not session_name:
                print("unable to get session id from dev server. Please try again")
                return None

            url = '{vtiger_url}/webservice.php?operation=query&sessionName={sessionName}&query={query}'.format(
                sessionName=session_name, query=query, vtiger_url=vtiger_access.get('vtiger_url'))
            headers = {'content-type': 'application/json'}
            request_type = 'GET'
            response, status = invoke_http_request(url, request_type, headers)

            if response:
                # trigger only if condition is satisfied
                if response.get('result') and workflow and event_type:
                    trigger_workflow(workflow, event_type, response.get('result')[0], vtiger_access.get('service_url'))
    elif workflow and event_type and data:
        # trigger without condition
        trigger_workflow(workflow, event_type, data, vtiger_access.get('service_url'))


def trigger_set_value_task(set_value_fields, conf, rule, session_name, vtiger_access):
    """   this function will execute revise query on vtiger for setting values
            params:
            1.set_value_fields : json object which have list of json payload of values to be set
            2.conf : conf object
            3.rule : json logic rule
            4.session_name : vtiger session
            3.vtiger_access : json object containing vtiger credentials

            Execution:
            1. get configs and create query and replace data using json logic.
            2. execute revise API on vtiger
            """

    id = conf.get('data').get('id', '')
    record_module = 'Leads'
    module = module_id_dict.get(record_module, '')
    if id and record_module:

        id = module + 'x' + id
        element = {"id": str(id)}

        for record in set_value_fields:
            name = record.get('name')
            type = record.get('type')
            value = record.get('value')

            if type == 'static' and rule:
                value = json_logic_replace_data(rule, conf, string_data=value)
                element[str(name)] = str(value)

            elif type == 'function' and rule:
                value = json_logic_replace_data(rule, conf, string_data=value)
                element[str(name)] = str(eval(value))

        # call set value API
        payload = {'operation': 'revise', 'sessionName': session_name, 'element': json.dumps(element)}
        url = '{vtiger_url}/webservice.php'.format(vtiger_url=vtiger_access.get('vtiger_url'))
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        request_type = 'POST'

        response, status = invoke_http_request(url, request_type, headers, payload=payload)

        if is_success_request(status_code):
            return response
        else:
            print("something went wrong while invoking revise API for set value. status:", status, "response:",
                  response)
            return None


def invoke_set_value_task(conf, set_value_configs, vtiger_access):
    """   this function will execute set value task.
            params:
            1.conf : conf object
            2.set_value_configs : conf dictionary containing rule, search_module_object, set_value_fields
            3.vtiger_access : json object containing vtiger credentials

            Execution:
            1. get configs and create query and replace data using json logic.
            2. check if conditions are satisfied using get query.
            3. call trigger_set_value_task function if conditions are satisfied.
            """

    set_value_fields = set_value_configs.get('set_value_fields', '')
    search_module_object = set_value_configs.get('search_module_object', '')
    rule = set_value_configs.get('rule', '')

    session_name = ''
    if vtiger_access.get('user_access_key', ''):
        session_name = get_session_name(vtiger_access.get('user_access_key'), vtiger_access.get('vtiger_url'),
                                        vtiger_access.get('vtiger_username'))
        if not session_name:
            print("unable to get session id from vtiger server. Please try again")
            return None

    if search_module_object and search_module_object.get('condition_object', ''):
        condition = buildquery(search_module_object.get('condition_object'))

        module = search_module_object.get('name')

        limit = str(search_module_object.get('fetch_record', ''))

        # prepare query using search_module_object

        order_by = ''
        if search_module_object.get('sort', ''):
            order_by = search_module_object.get('sort').get('column') + " " + search_module_object.get('sort').get(
                'type', "")

        if limit and order_by:
            query = 'SELECT * FROM {module} WHERE {condition} order by {order_by} LIMIT {limit};'.format(
                module=module,
                condition=condition,
                order_by=order_by,
                limit=limit)
        elif limit:
            query = 'SELECT * FROM {module} WHERE {condition} LIMIT {limit};'.format(
                module=module,
                condition=condition,
                limit=limit)
        elif order_by:
            query = 'SELECT * FROM {module} WHERE {condition} order by {order_by};'.format(
                module=module,
                condition=condition,
                order_by=order_by,
            )
        else:
            query = 'SELECT * FROM {module} WHERE {condition};'.format(
                module=module,
                condition=condition,
            )

        query = json_logic_replace_data(rule, conf, string_data=query)

        url = '{vtiger_url}/webservice.php?operation=query&sessionName={sessionName}&query={query}'.format(
            sessionName=session_name, query=query, vtiger_url=vtiger_access.get('vtiger_url'))
        headers = {'content-type': 'application/json'}
        request_type = 'GET'
        response, status = invoke_http_request(url, request_type, headers)

        if response:
            if response.get('result') and set_value_fields:
                set_value_response = trigger_set_value_task(set_value_fields, conf, rule, session_name, vtiger_access)
                return set_value_response

    elif set_value_fields:

        set_value_response = trigger_set_value_task(set_value_fields, conf, rule, session_name, vtiger_access)
        return set_value_response


def invoke_web_service_task(conf, web_service_configs):
    """ Web service task:
        params:
        1. conf: conf object
        2. web_service_configs: json object containing web service task configurations

        Execution:
        1. get request object and rule from conf
        2. replace data using json_logic
        3. get request parameters and invoke http request"""

    rule = web_service_configs.get('rule', '')
    request_object = web_service_configs.get('request_object', '')

    json_logic_replace_data(rule, conf, json_data=request_object)

    if request_object and rule:

        request_object = json_logic_replace_data(rule, conf, json_data=request_object)
        url = request_object.get("url")
        headers = request_object.get("header")
        request_type = request_object.get("type")
        payload = request_object.get("payload")

        if payload:
            response, status = invoke_http_request(url, request_type, headers, payload)
        else:
            response, status = invoke_http_request(url, request_type, headers)
        if is_success_request(status):
            return response


def invoke_conditional_task(conf, condition, true_task, false_task):
    """ this will execute conditional task.
        params:
        1. conf: conf object
        2. condition: condition object
        3. true_task: task to be triggered if condition is true
        4. false_task: task to be triggered if condition is false
        """
    is_valid = jsonLogic(condition, conf, ops)

    if is_valid:
        return true_task
    else:
        return false_task
