import requests
from json_logic.builtins import BUILTINS
from enums import HttpMethodEnum
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from mysql_mgr import *
from datetime import datetime, date, timedelta
import dateutil.parser as parser

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

ops = {
    **BUILTINS,
    'starts_with': lambda data, a, b: a.startswith(b),
    'ends_with': lambda data, a, b: a.endswith(b),
    'date_between': lambda data, a, b, c: str_to_datetime(b) <= str_to_datetime(a) <= str_to_datetime(c),
    'date_within_next': lambda data, a, b, c: date_within_next(a, b, c),
    'date_within_last': lambda data, a, b, c: date_within_last(a, b, c),
    'date_after': lambda data, a, b: str_to_datetime(a) > str_to_datetime(b),
    'date_before': lambda data, a, b: str_to_datetime(a) < str_to_datetime(b),
    'date_yesterday': lambda data, a: str_to_datetime(a).date() == date.today() - timedelta(days=1),
    'date_today': lambda data, a: str_to_datetime(a).date() == date.today(),
    'date_tomorrow': lambda data, a: str_to_datetime(a).date() == date.today() + timedelta(days=1),
    'date_is_empty': lambda data, a: a == ""
}


def date_within_next(date, number, period):
    if period == "days":
        return datetime.now() <= str_to_datetime(date) <= (
                datetime.now() + timedelta(days=int(number)))
    elif period == "weeks":
        return datetime.now() <= str_to_datetime(date) <= (
                datetime.now() + timedelta(weeks=int(number)))


def date_within_last(date, number, period):
    if period == "days":
        return (datetime.now() - timedelta(
            days=int(number))) <= str_to_datetime(date) <= datetime.now()
    elif period == "weeks":
        return (datetime.now() - timedelta(
            weeks=int(number))) <= str_to_datetime(date) <= datetime.now()


def str_to_datetime(date_time, str_format="%Y-%m-%d %H:%M:%S"):
    return datetime.strptime(date_time, str_format)

def get_datetime(date_string):
    """ this function will return datetime object with 2022-01-10 00:00:00 format"""
    return parser.parse(date_string)
