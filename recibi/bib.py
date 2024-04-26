#!/usr/bin/env python

import re
import csv
import hashlib
from .util import listify
from pybtex.database.input import bibtex
from pybtex.database import Entry, BibliographyData, parse_string
from dateutil.parser import parse as parse_date

import logging
logger = logging.getLogger("recibi")
warn = logger.warn
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
        "∓": "-/+",
        "±": "+/-",
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


def sort(bib):
    out = BibliographyData()
    entries = list(bib.entries.items())
    entries.sort()
    out.add_entries(entries)
    # for key, entry in entries:
    #     out.add_entry(key, entry)
    return out


def hash_entry(entry, fields=('author','title','year','note','organization','collaboration')):
    '''
    Return a hash of entry formed with letters.
    '''
    h = hashlib.sha1()
    for field in fields:
        string = entry.fields.get(field, field)
        h.update(string.encode())
    d = h.digest()
    s = ""
    for i in range(0,4):
        x = d[i] % 52
        if x >= 26:
            s += chr(ord('A') + x - 26)
        else:
            s += chr(ord('a') + x)
    return s


def generate_key(entry):
    last = entry.fields['author'].split(',')[0].strip().split(' ')[-1]
    year = entry.fields['year']
    rnd = hash_entry(entry)[:3]  # mimic InspireHEP
    return f'{last}:{year}{rnd}'


def clean_cell(col, cell):
    cell = replace_unicode(cell)
    if col == 'year':
        return str(parse_date(cell.replace('.',' ')).year)
    if col == 'author':
        return cell.replace(',', ' and ')
    return cell


def trans(infiles, columns, kind, delim='\t', skip=0):
    '''
    Load infiles as delim-separated values and return bibs.
    '''
    # inspired by d.jaffe's gglcsvtobibtex.py 
    entries = dict()
    for infile in infiles:
        rows = list(csv.reader(open(infile), delimiter=delim))
        for row in rows[skip:]:
            if not row or not row[0]:
                continue
            entry = Entry(kind)
            for col,cell in zip(columns, row):
                if not col:
                    continue
                entry.fields[col] = clean_cell(col, cell)
            key = generate_key(entry)
            if key in entries:
                warn(f'duplicate key "{key}", skipping: {entry}')
                continue
            entries[key] = entry
    out = BibliographyData()
    for key, entry in entries.items():
        out.add_entry(key, entry)
    return out


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


default_header='''
DO NOT EDIT THIS FILE.  IT IS FULLY GENERATED.  ANY EDITS MAY BE LOST.
'''
default_trailer='''
DO NOT EDIT THIS FILE.  IT IS FULLY GENERATED.  ANY EDITS MAY BE LOST.
'''
def dump(bib, output, fmt='bibtex',
         header=default_header, trailer=default_trailer):
    '''
    Serialize bib object to output.

    A empty file name or "-" is treated as stdout.
    '''
    if not output or output == '-':
        output = '/dev/stdout'
    with open(output, "w") as outfile:
        if fmt == 'bibtex':
            outfile.write(header + '\n')
        outfile.write(bib.to_string(fmt))
        if fmt == 'bibtex':
            outfile.write(trailer + '\n')
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
