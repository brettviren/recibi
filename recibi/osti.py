#!/usr/bin/env python
'''
Client interface to InspireHEP web API.

'''

from recibi import apis
from urllib.error import HTTPError
from urllib.request import Request, urlopen


api_url = 'https://www.osti.gov/api/v1'

form_params = apis.form_params


def form_url(endpoint="records", params="", **q):
    '''
    Form an OSTI API URL.
    '''
    url = api_url + '/' + endpoint
    p = ""
    if q:
        p = form_params(**q)
    if params:
        p = "&" + params
    if p:
        url += "?" + p
    return url


def get(url, format='bibtex', **headers):
    f2h = dict(bibtex='application/x-bibtex',
               xml='application/xml',
               json='application/json')
    headers['Accept'] = f2h[format]
    return apis.get(url, **headers)
