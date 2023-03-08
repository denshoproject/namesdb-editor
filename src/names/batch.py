from collections import namedtuple
from pathlib import Path

from django.conf import settings
from django.db import connections

from elastictools import docstore, search
from .converters import text_to_rolepeople, rolepeople_to_text
from . import docstore
from . import fileio
from . import models
from namesdb_public import models as models_public

PERSONS_DEFAULT_DICT = {'namepart':''}


def search_multi(csvfile, method, show_headers):
    """Consume output of `ddrnames export` suggest Person records for each name
    
    @param csvfile: str path to csvfile
    @param method: str 'elastic' or 'sql'
    @param headers: bool show_headers
    """
    def format_result(oid, item, n, preferred_name, nr_id, score):
        result = f'"{oid}", "{namepart}", {n}, "{preferred_name}", "{nr_id}", {score}'
        return f'{result}, "{rolepeople_to_text([item])}"'
    if show_headers:
        yield '"objectid", "namepart", "n", "preferred_name", "nr_id", "score", "sample"'
    for row in fileio.read_csv(csvfile):
        items = []
        oid,fieldname,names = row
        # skip headers (TODO better to *read* headers)
        if (oid == 'id') and (fieldname == 'fieldname'):
            continue
        if names == '':
            continue
        # text_to_rolepeople?
        data = text_to_rolepeople(names, PERSONS_DEFAULT_DICT)
        # if we have an nr_id, just get the Person
        for item in data:
            item['oid'] = oid
            item['fieldname'] = fieldname
            items.append(item)
        if method == 'elastic':
            es_class = models_public.ELASTICSEARCH_CLASSES_BY_MODEL['person']
            search = fulltext_search_elastic
            prep_names = prep_names_wildcard
        elif method == 'sql':
            search = fulltext_search_sql
            prep_names = prep_names_simple
        for item in items:
            oid = item.pop('oid')
            fieldname = item.pop('fieldname')
            namepart = item['namepart']
            if 'nr_id' in item.keys():
                # exact match
                if method == 'elastic':
                    record = es_class.get(nr_id, request=None)
                elif method == 'sql':
                    record = get_sql(item['nr_id'])
                n,preferred_name,nr_id,score = (
                    0,record['preferred_name'],item['nr_id'],100.0
                )
                yield format_result(oid, item, n, preferred_name, nr_id, score)
            else:
                # fulltext search
                for n,preferred_name,nr_id,score in search(
                        prep_names(item['namepart'])
                ):
                    item['nr_id'] = nr_id
                    yield format_result(
                        oid, item, n, preferred_name, nr_id, score
                    )

def prep_names_wildcard(names):
    """Surround each name word with wildcards e.g. "*yasui* *sachi*"."""
    return ' '.join([f'*{name}*' for name in names.replace(',', '').split(' ')])

def prep_names_simple(names):
    """Just remove all punctuation e.g. "yasui sachi"."""
    return ''.join([c.lower() for c in names if c.isalpha() or c.isspace()])

def get_elastic(nr_id):
    """Get record from Elasticsearch by nr_id
    @returns for n,preferred_name,nr_id,score for each row
    """
    return models_public.ELASTICSEARCH_CLASSES_BY_MODEL['person'].get(
        nr_id, request=None
    )

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

def get_sql(nr_id):
    p = models.Person.objects.get(nr_id=nr_id)
    return {'nr_id': p.nr_id, 'preferred_name': p.preferred_name}

def fulltext_search_sql(names, limit=25):
    """SQL fulltext search for names in namesdb_public
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
