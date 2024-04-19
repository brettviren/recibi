#!/usr/bin/env python

import re
from .util import listify
from pybtex.database.input import bibtex
from pybtex.database import Entry, BibliographyData, parse_string

import logging
logger = logging.getLogger("recibi")
info = logger.info
debug = logger.debug


def copy_entry(entry):
    '''
    Return a copy of the entry via serialize round-trip.
    '''
    new = parse_string(entry.to_string("bibtex"), "bibtex")
    return new.entries.popitem()[1]


def merge_patch(key, target, patch, sets=("keywords",), setdelim=','):
    '''
    Implement an extended JSON Merge Patch algorithm on bib entries.

    It extends Merge Patch by treating any fields named in "sets" as a string
    list delimited by "setdelim".  For such fields it will produce a union of
    target and patch field.  The sets are lexically ordered.
    '''
    out = copy_entry(target)
    for field in patch.fields:
        if field in sets:
            s = target.fields.get(field,"")
            if s:
                s += setdelim
            s += patch.fields[field]
            s = list(set(s.split(setdelim)))
            s.sort()
            s = setdelim.join(s)
            out.fields[field] = s
        else:
            out.fields[field] = patch.fields[field]
    return (key,out)


# from wiso/ListOfPublicationsFromInspireHEP
def replace_unicode(item):
    chars = {
        "\xa0": " ",
        "\u202f": "",
        "\u2009\u2009": " ",
        "−": "-",
        "∗": "*",
        "Λ": r"\Lambda",
    }

    def replace_chars(match):
        char = match.group(0)
        return chars[char]

    return re.sub("(" + "|".join(list(chars.keys())) + ")", replace_chars, item)


def clean_entry(entry):
    '''
    Replace unicode
    '''
    for key, val in entry.fields.items():
        entry.fields[key] = replace_unicode(val)
    return entry


def load(bibfiles=None, mutate=None, merge=None):
    '''
    Serialize bib object from bibfile(s).

    The "bibfile" may be empty or a sequence of strings or paths.  An empty
    bibfile or "-" is interpreted as stdin.

    If "mutate" is given it is a function:

        mutate(key,entry) -> None | (key,entry) | [(key,entry),...]

    If "merge" is given it is a function:

        merge(key,old,new) -> None | (key,entry) | [(key,entry),...]

    Default "mutate" is a pass-through, default "merge" returns (key,old)

    The "mutate" gives opportunity to delete, generate and modify entries.

    The "merge" gives opportunity to resolve duplicate keys.

    '''
    if not bibfiles:
        bibfiles = "-"
    bibfiles = listify(bibfiles)


    out = BibliographyData()

    for bibfile in bibfiles:
        if not bibfile or bibfile == "-":
            bibfile = "/dev/stdin"

        # parser keeps state so make it anew for each input
        parser = bibtex.Parser()
        bib = parser.parse_file(bibfile)

        for inkey, inentry in bib.entries.items():

            item = (inkey, clean_entry(inentry))

            # mutate may generate
            queue = list()
            if mutate:
                got = mutate(*item)
                if isinstance(got, tuple):
                    queue.append(got)
                elif isinstance(got, list):
                    queue += got
            else:
                queue.append(item)
            
            if not queue:
                continue

            if merge:
                for key, entry in queue:
                    if key in out.entries:
                        old = out.entries.pop(key)
                        got = merge(key, old, entry)
                        if isinstance(got, tuple):
                            got = [got]
                        if isinstance(got, list):
                            for k, e in got:
                                out.add_entry(k,e)
                    else:       # not seen, take whole
                        out.add_entry(key, entry)
            else:               # not merging, take all
                out.add_entries(queue)

    return out


def dump(bib, output, fmt='bibtex'):
    '''
    Serialize bib object to output.

    A empty file name or "-" is treated as stdout.
    '''
    if not output or output == '-':
        output = '/dev/stdout'
    with open(output, "w") as outfile:
        outfile.write(bib.to_string(fmt))
    return


def visit(bib, proc):
    '''
    Run proc on each entry of bib to make a new proc.

    Proc is called as proc(key, entry) and should return None, a tuple
    (key,entry) or a list of those tuples.  Non-None will be added to the
    produced bib.
    '''

    out = BibliographyData()

    for key, entry in bib.entries.items():
        got = proc(key, entry)
        if got is None:
            continue
        if isinstance(got, tuple) and len(got) == 2:
            got = [got]
        for one in got:
            out.add_entry(*one)

    return out
