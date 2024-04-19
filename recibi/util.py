#!/usr/bin/env python
'''
Simple utility functions for recibi.
'''

import collections.abc

def is_seq(obj):
    return isinstance(obj, collections.abc.Sequence) and not isinstance(obj, str)

def listify(thing):
    if is_seq(thing):
        return thing
    return [thing]
