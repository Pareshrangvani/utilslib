import requests

from enums import HttpMethodEnum
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
        from app import app
        app.logger.error(msg)


def is_success_request(status_code):
    return 200 <= status_code <= 299
