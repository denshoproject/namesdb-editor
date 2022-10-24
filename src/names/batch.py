import csv
from collections import namedtuple
from pathlib import Path

from django.conf import settings
from django.db import connections

from elastictools import search
from . import docstore
from namesdb_public import models as models_public


def search_multi(csvfile, prep_names, search):
    """Consume output of `ddrnames export` suggest Person records for each name
    """
    with Path(csvfile).open('r') as f:
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.seek(0)
        for row in csv.reader(f, dialect):
            oid,fieldname,names = row
            # skip headers (TODO better to *read* headers)
            if (oid == 'id') and (fieldname == 'fieldname'):
                continue
            for n,preferred_name,nr_id,score in search(prep_names(names)):
                yield f'"{oid}", "{names}", {n}, "{preferred_name}", "{nr_id}", {score}'

def prep_names_wildcard(names):
    """Surround each name word with wildcards e.g. "*yasui* *sachi*"."""
    return ' '.join([f'*{name}*' for name in names.replace(',', '').split(' ')])

def prep_names_simple(names):
    """Just remove all punctuation e.g. "yasui sachi"."""
    return names.replace(',', '').replace('.', '')

def fulltext_search_elastic(names, limit=25):
    """Elasticsearch fulltext search for names in namesdb_public
    @returns for n,preferred_name,nr_id,score for each row
    """
    searcher = search.Searcher(docstore.Docstore(
        models_public.INDEX_PREFIX, settings.DOCSTORE_HOST, settings
    ))
    searcher.prepare(
        params={'fulltext': names},
        params_whitelist=['fulltext'],
        search_models=['namesperson'],
        sort=[],
        fields=models_public.SEARCH_INCLUDE_FIELDS_PERSON,
        fields_nested=[],
        fields_agg=models_public.AGG_FIELDS_PERSON,
        wildcards=True,
    )
    return [
        (n, h.preferred_name, h.nr_id, h.meta.score)
        for n,h in enumerate(searcher.execute(limit, 0).objects)
    ]

def fulltext_search_datasette(names, limit=25):
    """Datasette fulltext search for names in namesdb_public
    @returns for n,preferred_name,nr_id,score for each row
    """
    with connections['names'].cursor() as cursor:
        # TODO isn't this what JOINs are for?
        # inner query, gets rowids and ranks
        cursor.execute(f'SELECT rowid, rank FROM names_person_fts("{names}")')
        inner_rows = _namedtuplefetchall(cursor)
        rowids = ','.join([str(row.rowid) for row in inner_rows])
        ranks = {row.rowid: row.rank for row in inner_rows}
        # outer query, gets fields
        cursor.execute(f'SELECT rowid, * FROM names_person_fts WHERE rowid IN ({rowids})')
        outer_rows = _namedtuplefetchall(cursor)
        # add rank to outer query data
        persons = [
            [row.preferred_name, row.nr_id, ranks[row.rowid]] for row in outer_rows
        ]
        # sort by score and add index
        return [
            [n] + person for n,person in enumerate(
                sorted(persons, key=lambda x: x[-1])
            )
        ]

def _namedtuplefetchall(cursor):
    """Return all rows from a cursor as a namedtuple"""
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]
