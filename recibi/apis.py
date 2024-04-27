#!/usr/bin/env python
'''
General utility functions for accessing web APIs.
'''


from urllib.error import HTTPError
from urllib.request import Request, urlopen

import logging
logger = logging.getLogger("recibi")
warn = logger.warn
debug = logger.debug


def form_params(joiner=",", **params):
    '''
    Return &-separated URL-encoded params part but with no leading "?".

    If a param value is a list or tuple it will be joined with the value of
    joiner to form a string.

    Spaces are url-encoded
    '''
    if not params:
        return ""
    parts = list()
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            v = joiner.join(v)
        v = v.strip().replace(" ", "%20")
        parts.append(f'{k}={v}')
    return "&".join(parts)


def get(url, **headers):
    '''
    Perform HTTP GET on url and return text.
    '''

    req = Request(url)
    for key, val in headers.items():
        req.add_header(key, val)
        print(f'Header: {key} {val}')

    debug(req)

    try:
        res = urlopen(req)
    except HTTPError as err:
        warn(f'bad URL: {url}. {err}')
        raise
    if res.getcode() == 200:
        return res.read().decode()
    raise IOError(f'HTTP GET error {res.getcode()} for {url}')
