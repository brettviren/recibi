#!/usr/bin/env python
'''
Client interface to InspireHEP web API.
'''

# Note, pyinspirehep exists but I can't make it do quite what I want so we just
# DIY a barebones client.

from urllib.request import Request, urlopen

api_url = 'https://inspirehep.net/api'
# https://inspirehep.net/api/{identifier-type}/{identifier-value}


def form_params(joiner=" or ", **params):
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


def get(url):
    '''
    Perform HTTP GET on url and return text.
    '''

    req = Request(url)
    # if fmt == 'bibtex':
    #     req.add_header('Accept','application/x-bibtex')
    res = urlopen(req)
    if res.getcode() == 200:
        return res.read().decode()
    raise IOError(f'HTTP GET error {res.getcode()} for {url}')



# req = Request('https://inspirehep.net/api/literature?sort=mostrecent&q=arxiv:2404.01687%20or%20arxiv:2402.05383')
# req.add_header('Accept','application/x-bibtex')
# text = urlopen(req).read()
# print(text.decode())
