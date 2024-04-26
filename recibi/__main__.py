#!/usr/bin/env python

import re
import click

from recibi.matching import string_match, number_match
from recibi.bib import load, dump, sort, trans, merge_patch
import recibi.inspire as api
import logging
logging.basicConfig(filename='/dev/stderr', level=logging.INFO)
logger = logging.getLogger("recibi")
info = logger.info
debug = logger.debug

@click.group()
def cli():
    pass


@cli.command("parse")
@click.option("-m", "--match", default=[r"(ar[Xx]iv:(\d+)\.(\d+))"], multiple=True,
              help="Thing to match, default finds arxiv IDs")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.argument("text")
def parse_for_arxiv(output, match, text):
    '''
    Given a text, output bits that match.

    Matches are formed by re.findall() taking the first item.

    Multiple matches are treated as logical OR.

    Example:

    recibi parse -m '(ar[Xx]iv:(\d+)\.(\d+))' file.txt > file.ids
    '''
    with open(output, "w") as out:
        text = open(text).read()
        for pat in match:
            for one in re.findall(pat, text):
                if one:
                    out.write(one[0] + "\n")


@cli.command("csv")
@click.option("-d", "--delim", default=",",
              help='The column delimiter (eg "," for CSV, "\t" for TSV')
@click.option("-c", "--columns", default='title,collaboration,organization,note,author,year',
              help="Comma-separated list of bibtex attributes in order of columns")
@click.option("-s", "--skip", default=1,
              help="Number of leading rows to skip")
@click.option("-k", "--kind", default="conference",
              help="The kind of BibTeX entry")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.argument('textfiles', nargs=-1)
def csv(delim, columns, skip, kind, output, textfiles):
    '''
    Transform a columnar file to bib entries.
    '''
    if delim.lower() == 'tab':
        delim = '\t'
    columns = columns.split(",")
    dump(sort(trans(textfiles, columns, kind, delim, skip)), output)


@cli.command("merge")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.argument('bibfiles', nargs=-1, type=click.Path())
def merge(output, bibfiles):
    '''
    Merge bibliography files.
    '''
    dump(sort(load(bibfiles, merge=merge_patch)), output)


@cli.command("filter")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.option("-m", "--match", default=[], multiple=True,
              help="Match fields with <field>:<re>, multiple act as AND")
@click.option("-n", "--number", default=[], multiple=True,
              help="Match fields with <field>:<test>, multiple act as AND")
@click.argument('bibfiles', nargs=-1, type=click.Path())
def filter(output, match, number, bibfiles):
    '''
    Output matching records.

    Matches are specified on a per-field basis and all must match to match an
    entry.

    Matches regex against string with -m/--match and are case insensitive.

    Numerical comparison provides an operation with -n/--number.

    The special field name "key" can be used to match against the entry key.

    Example:

        -m collaboration:dune -n year:>2018

    Input file may be "-" to indicate stdin.
    '''

    matches = tuple([m.split(":", 1) for m in match])
    numbers = tuple([n.split(":", 1) for n in number])

    def do_filt(key, entry):
        if not number_match(key, entry, numbers):
            return
        if not string_match(key, entry, matches):
            return
        return key, entry

    dump(load(bibfiles, mutate=do_filt), output);


@cli.command("tag")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.option("-t", "--tag", multiple=True,
              help="A value to add to the 'keywords' field")
@click.option("-T", "--transfer", multiple=True,
              help="Transfer given field to a keyword")
@click.argument('bibfiles', nargs=-1, type=click.Path())
def tag(output, tag, transfer, bibfiles):
    '''
    Add tag(s) to the "keywords" field.

    An input file name of "-" is interpreted to be stdin.
    '''
    tags = ','.join(tag)

    def squash(val):
        return val.lower().replace(" ", "").replace("-", "")

    def add_tag(key, entry):
        old = entry.fields.get("keywords", None)
        if not old:
            new = tags
        else:
            new = old + "," + tags

        # make unique and sorted
        new = set(new.split(','))

        for field in transfer:
            val = entry.fields.get(field, None)
            if val is None:
                continue
            new.add(squash(val))
        new = list([n for n in new if n])
        new.sort()
        new = ','.join(new)
        entry.fields['keywords'] = new

        return (key, entry)

    dump(load(bibfiles, mutate=add_tag), output)

@cli.command("inspire")
@click.option("-o", "--output", default="/dev/stdout",
              help="Output file")
@click.option("-T", "--type", default="literature",
              help="Set the 'identifier-type' URL location")
@click.option("-V", "--value", default=None,
              help="Set the 'identifier-value' URL location (optional)")
@click.option("-F", "--format", default="bibtex", type=click.Choice(["bibtex","json"]),
              help="Set the format for the output")
@click.option("-q", "--queries", type=click.Path(), multiple=True,
              help="Give a file with q= search terms, one per line")
@click.option("-s", "--sort", default="mostrecent",
              help="Set the sort order for search results, this is identifier-type-specific")
@click.option("-S", "--size", default=10,
              help="Set number of search results, max is 1000")
@click.option("-P", "--page", default=1,
              help="Set page of search results, default is 1")
@click.option("--query-join", default="or",
              help="Set the Boolean operator for joining multiple args to the q= search queries")
@click.option("--maxn", default=10,
              help="Max number of search queries per GET")
@click.argument("query", nargs=-1)
def inspire(output, type, value, format, queries, sort, size, page, query_join, maxn, query):
    '''
    Access InspireHEP web API.

    See eg. https://github.com/inspirehep/rest-api-doc
    
    Example:

        recibi inspire arxiv:2404.01687 arxiv:2402.05383

    A query term of "-" that is given as a command argument is interpreted to
    read stdin as if it were a file of query terms.

    Default format is bibtex however some identifier-types will return JSON regardless.

    Pagination is not supported.

    Take in mind InspireHEP has a rate limit.  This command will make 1 query.
    '''
    query = list(query)
    queries = list(queries)

    if "-" in query:
        queries.append("/dev/stdin")
        query.remove("-")

    if size > 1000:
        size = 1000


    for one in queries:
        for line in open(one).readlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            query.append(line)

    # unique and well ordered
    query = list(set(query))
    query.sort()

    chunks = list()
    for group in [query[x:x+maxn] for x in range(0, len(query), maxn)]:
        params = api.form_params(q=group, sort=sort,
                                 size=str(size), page=str(page), format=format)
        url = api.form_url(type, value, params)
        text = api.get(url)
        chunks.append(text)

    with open(output,"w") as out:
        out.write('\n'.join(chunks))

@cli.command("search")
@click.option("-o", "--output", default="/dev/stdout",
              help='Output file')
@click.option("-s", "--search", multiple=True,
              help="Search terms like field=regex")
@click.argument("bibfiles", nargs=-1)
def search(output, search, bibfiles):
    '''
    Search a bib file for matching entries.

    Search terms are in form 'field:regex' where the special field "key" may be
    used to match the entry key.  All search terms given must match for an entry
    to be emitted.
    '''
    terms = [(field, re.compile(regex, re.IGNORECASE))
             for field, regex in map(lambda s: s.split("=", 1), search)]

    def findit(key, entry):

        # must run the gauntlet 
        for field, regex in terms:
            if field == 'key':
                if re.match(regex, key):
                    continue
            elif field in entry.fields:
                if re.search(regex, entry.fields[field]):
                    continue
            return              # entry has no field

        return (key, entry)
    dump(load(bibfiles, mutate=findit), output)


def main():
    cli()

if '__main__' == __name__:
    main()
