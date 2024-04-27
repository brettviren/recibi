#!/usr/bin/env python
'''
Client interface to InspireHEP web API.
'''

# Note, pyinspirehep exists but I can't make it do quite what I want so we just
# DIY a barebones client.

from recibi import apis

api_url = 'https://inspirehep.net/api'
# https://inspirehep.net/api/{identifier-type}/{identifier-value}


def form_params(joiner=" or ", **params):
    '''
    Return &-separated URL-encoded params part but with no leading "?".

    If a param value is a list or tuple it will be joined with the value of
    joiner to form a string.

    Spaces are url-encoded
    '''
    return apis.form_params(joiner, **params)


def form_url(identifier_type="literature", identifier_value=None, params=""):
    '''
    Form an InspireHEP web API URL.
    '''
    url = api_url + '/' + identifier_type
    if identifier_value:
        url += '/' + identifier_value
    if params:
        url += "?" + params

    return url

# req = Request('https://inspirehep.net/api/literature?sort=mostrecent&q=arxiv:2404.01687%20or%20arxiv:2402.05383')
# req.add_header('Accept','application/x-bibtex')
# text = urlopen(req).read()
# print(text.decode())
