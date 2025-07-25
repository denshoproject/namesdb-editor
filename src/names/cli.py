DESCRIPTION = """"""

HELP = """
Sample usage:

    # Import data from CSV
    $ namesdb import far far-records.csv

    # Copy SQLite3 database, removing Django-specific tables
    $ namesdb exportdb

    # Create and destroy Elasticsearch indexes
    $ namesdb create -H localhost:9200
    $ namesdb destroy -H localhost:9200 --confirm

    # Check status
    $ namesdb status -H localhost:9200

    # Publish records to Elasticsearch
    $ namesdb post -H localhost:9200 person
    $ namesdb post -H localhost:9200 farrecord
    $ namesdb post -H localhost:9200 wrarecord
    
    # Print Elasticsearch URL for record
    $ namesdb url -H localhost:9200 person 0a1b2c3d4e
    
    # Get record JSON from Elasticsearch
    $ namesdb get -H localhost:9200 person 0a1b2c3d4e
    
    # Delete records from Elasticsearch
    $ namesdb delete -H localhost:9200 person 0a1b2c3d4e

Note: You can set environment variables for HOSTS and INDEX.:

    $ export ES_HOSTS=localhost:9200

"""

from datetime import datetime, date
from http import HTTPStatus
import json
from pathlib import Path
import os
import shutil
import sqlite3
import sys

import click
from dateutil import parser
# Django must be initialized before settings can be accessed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'editor.settings')
import django
django.setup()
from django.conf import settings
import httpx
from tqdm import tqdm

from . import batch
from . import csvfile
from . import docstore
from . import fileio
from . import models
from . import noidminter
from . import publish
from namesdb_public import models as models_public
from ireizo_public import models as models_ireizo

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--debug','-d', is_flag=True, default=False)
def namesdb(debug):
    """namesdb - Tools for working with FAR and WRA records

    \b
    See "namesdb help" for examples.
    """
    if debug:
        click.echo('Debug mode is on')

@namesdb.command()
def help():
    """Detailed help and usage examples
    """
    click.echo(HELP)

@namesdb.command()
def conf():
    """Print configuration settings.
    
    More detail since you asked.
    """
    click.echo(f'namesdb will use the following settings:')
    click.echo(f'CONFIG_FILES:            {settings.CONFIG_FILES}')
    click.echo(f"DATABASES[names]NAME     {settings.DATABASES['names']['NAME']}")
    click.echo(f'NAMESDB_HOST:            {settings.DOCSTORE_HOST}')
    click.echo(f'DOCSTORE_SSL_CERTFILE:   {settings.DOCSTORE_SSL_CERTFILE}')
    click.echo(f'DOCSTORE_USERNAME:       {settings.DOCSTORE_USERNAME}')
    click.echo(f'DOCSTORE_PASSWORD:       {settings.DOCSTORE_PASSWORD}')
    click.echo(f'NOIDMINTER_URL:          {settings.NOIDMINTER_URL}')
    click.echo(f'NOIDMINTER_USERNAME:     {settings.NOIDMINTER_USERNAME}')
    click.echo(f'NOIDMINTER_PASSWORD:     {settings.NOIDMINTER_PASSWORD}')
    click.echo('')

@namesdb.command()
@click.argument('model')
def schema(model):
    """Print schema for specified model
    """
    class_ = models.MODEL_CLASSES[model]
    fields = models.model_fields(class_)
    schema = models.format_model_fields(fields)
    click.echo(schema)

@namesdb.command()
@click.option('--debug','-d', is_flag=True, default=False)
@click.option('--idfile','-i', default=None, help='Load primary keys from file (one per line)')
@click.option('--search','-s', default=None, help='Search terms: "field=TERM;field=TERM;..."')
@click.option('--searchfile','-S', default=None, help='Search terms from file.')
@click.option('--cols','-c', default=None, help='Fields to export: "family_name,given_name,..."')
@click.option('--colsfile','-C', default=None, help='Fields to export, from file.')
@click.option('--limit','-l', default=None, help='Limit number of records.')
@click.argument('model')
def dump(debug, idfile, search, searchfile, cols, colsfile, limit, model):
    """Dump model data to STDOUT
    
    \b
    You can search using Django field lookups:
    https://docs.djangoproject.com/en/4.0/ref/models/querysets/#field-lookups
    Use -s/--search to search a small number of fields from the command-line
    or -S/--searchfile to get search terms from a file.
    Search (one line):
        last_name=Morita; first_name=Noriyuki; birth_date__icontains=1932
    Search (multiple lines):
        last_name=Morita
        first_name=Noriyuki
        birth_date__icontains=1932
    Search (mixed):
        last_name=Morita; first_name=Noriyuki
        birth_date__icontains=1932
    
    \b
    Use -c/--cols to specify output columns from the command-line
    or -C/--colsfile to get from file.
    Columns (one line):
        last_name,first_name,birth_date
    Columns (multiple lines):
        last_name
        first_name
        birth_date
    Columns (mixed):
        last_name,first_name
        birth_date
    """
    # model
    model_class = models.MODEL_CLASSES[model]
    if debug: print(f'model_class {model_class}')
    EXCLUDED_FIELDS = [
        'timestamp',  # why would we export this
    ]
    model_fieldnames = [
        f[0]
        for f in models.model_fields(model_class)
        if not f[0] in EXCLUDED_FIELDS
    ]
    id_fieldname = model_fieldnames[0]
    # identifiers from file
    if idfile:
        with Path(idfile).open('r') as f:
            ids = [l.strip() for l in f.readlines()]
    else:
        ids = []
    # search
    if searchfile:
        with Path(searchfile).open('r') as f:
            search = _parse_search(f.read().strip(), debug)
    elif search:
        search = _parse_search(search, debug)
    # columns
    if colsfile:
        with Path(colsfile).open('r') as f:
            columns = _parse_columns(f.read().strip(), debug)
    elif cols:
        columns = _parse_columns(cols)
    else:
        columns = model_fieldnames
    if id_fieldname not in columns:
        columns.insert(0, id_fieldname)
    if debug: print(f'columns {columns}')
    # limit
    if limit:
        limit = int(limit)
    if debug: print(f'limit {limit}')
    # dump!
    models.dump_csv(sys.stdout, model_class, ids, search, columns, limit, debug)

def _parse_search(text, debug=False):
    if debug:
        click.echo(f'search "{text}"')
    queries = []
    for line in text.splitlines():
        for term in line.split(';'):
            queries.append(term)
    params = {}
    for terms in queries:
        if terms.strip():
            try:
                key,val = terms.strip().split('=')
                params[key.strip()] = val.strip()
            except ValueError as err:
                click.echo(f'Malformed search (see help): "{search}"')
                sys.exit(1)
    if debug:
        click.echo(f'search "{params}"')
    return params

def _parse_columns(text, debug=False):
    if debug:
        click.echo(f'cols "{text}"')
    columns = []
    for line in text.strip().splitlines():
        for term in line.strip().split(','):
            columns.append(term.strip())
    if debug:
        click.echo(f'columns "{columns}"')
    return columns

NOTE_DEFAULT = 'Load from CSV'

@namesdb.command()
@click.option('--debug','-d', is_flag=True, default=False)
@click.option('--batchsize','-b', default=settings.NOIDMINTER_BATCH_SIZE,
              help='Batch size for requesting new Person.nr_ids.')
@click.option('--offset','-o', default=0, help='Start at specified record.')
@click.option('--limit','-l', default=1_000_000, help='Limit number of records.')
@click.option('--note','-n', default=NOTE_DEFAULT,
              help=f'Optional note (default: "{NOTE_DEFAULT}".')
@click.argument('model')
@click.argument('datafile')
@click.argument('username')
def load(debug, batchsize, offset, limit, note, model, datafile, username):
    """Load data from a data file
    
    See names.models.MODEL_CLASSES
    
    \b
    Load from CSV
        namesdb load MODEL namesdb-MODEL-YYYYMMDD.csv USERNAME
    
    \b
    Load Ireizo data (retrieved using ireizo-fetch/ireizo-api-fetch-v*.py)
        namesdb load ireirecord ./output/api-people-1.json gjost
        namesdb load ireirecord ./output/api-people-2.json gjost
        namesdb load ireirecord ./output/api-people-3.json gjost
        ...
    
    \b
    Load Facility data from densho-vocab
        namesdb load facility /opt/densho-vocab/api/0.2/facility.json USERNAME
    """
    available_models = list(models.MODEL_CLASSES.keys())
    if model not in available_models:
        click.echo(f'ERROR: Bad model "{model}".')
        click.echo(f'Choices: {", ".join(available_models)}')
        sys.exit(1)
    if offset:
        offset = int(offset)
    if limit:
        limit = int(limit)
    sql_class = models.MODEL_CLASSES[model]
    if model == 'ireirecord':
        load_irei(datafile, sql_class, username, note)
    elif model == 'facility':
        load_facility(datafile, sql_class, username, note)
    else:
        load_csv(datafile, sql_class, offset, limit, username, note)

def load_csv(datafile, sql_class, offset, limit, username, note):
    prepped_data = sql_class.prep_data()
    rowds = csvfile.make_rowds(
        fileio.read_csv(datafile, offset, limit)
    )
    num = len(rowds)
    processed = 0
    failed = []
    noids = []
    if sql_class.__name__ == 'Person':  # How many NOIDs are needed
        # rowds with empty 'nr_id' fields
        noids_to_get = len(list(filter(lambda rowd: not rowd['nr_id'], rowds)))
        if noids_to_get:
            # get from ddridservice in batch
            click.echo(f"Getting {noids_to_get} NRIDS")
            noids = noidminter.get_noids(noids_to_get)
    noids_assigned = 0
    for n,rowd in enumerate(tqdm(
            rowds, desc='Writing database', ascii=True, unit='record'
    )):
        if (sql_class.__name__ == 'Person') and not rowd['nr_id']:
            rowd['nr_id'] = noids.pop(0)
            noids_assigned += 1
        try:
            o,prepped_data = sql_class.load_rowd(rowd, prepped_data)
            if o:
                o.save(username=username, note=note)
        except:
            err = sys.exc_info()[0]
            click.echo(f'FAIL {rowd} {err}')
            failed.append( (n,rowd, err) )
            raise
        processed = processed + 1
        if processed > limit:
            break
    if failed:
        click.echo('FAILED ROWS')
    for f in failed:
        click.echo(f)

def load_facility(datafile, sql_class, username, note):
    """Load data files from densho-vocab/api/0.2/facility.json
    """
    with Path(datafile).open('r') as f:
        rowds = json.loads(f.read())['terms']
    for n,rowd in enumerate(rowds):
        try:
            o = sql_class.load_from_vocab(rowd)
            if o:
                o.save()
        except:
            err = sys.exc_info()[0]
            click.echo(f'FAIL {rowd} {err}')
            raise

@namesdb.command()
@click.option('--debug','-d', is_flag=True, default=False)
@click.option('--fetchdate','-F', default=date.today(),
              help='(YYYY-MM-DD) Date data was fetched if not today.')
@click.option('--dryrun','-D', is_flag=True, default=False,
              help="Don't write to database.")
@click.argument('output')
@click.argument('username')
def loadirei(debug, fetchdate, dryrun, output, username):
    """Load data files from JSONL output from irei-fetch

    \b
    OUTPUT
    - Data is downloaded from Irei using ireizo-api-fetch.py
      and ireizo-pubsite-fetch.py
    - Directory containing Irei API and wall data e.g. output/20240118
    - File containing Irei API and wall data
      e.g. output/20240118/api-people-19.json

    \b
    Expectations
    - An output directory contains both API and wall data
    - all data is in JSONL

    \b
    Usage
    export TODAY=`date +%Y%m%d`
    namesdb loadirei /opt/ireizo-fetch/output/$TODAY/ gjost | tee -a log/$TODAY-irei-import.log
    """
    if fetchdate:
        fetchdate = parser.parse(fetchdate)
    if Path(output).is_dir():
        paths = sorted(Path(output).iterdir())
    elif Path(output).is_file():
        paths = [Path(output)]
    rowds_api = []
    rowds_wall = []
    for n,path in enumerate(paths):
        if not '.jsonl' in path.name:
            continue
        with path.open('r') as f:
            rowds = [json.loads(line) for line in f.readlines()]
        if 'api-people' in path.name:
            for rowd in rowds:
                rowds_api.append(rowd)
        elif 'pubsite-people' in path.name:
            for rowd in rowds:
                rowds_wall.append(rowd)
    click.echo(
        f"{n} files - {len(rowds_api)} API records - {len(rowds_wall)} wall records"
    )
    # merge data and save objects
    irei_records = models.IreiRecord.load_irei_data(rowds_api, rowds_wall)
    click.echo(f"{len(irei_records)=}")
    start = datetime.now()
    n = 0
    num = len(irei_records.keys())
    updated = 0
    for irei_id,rowd in irei_records.items():
        n += 1
        feedback = models.IreiRecord.save_record(
            rowd, fetchdate=fetchdate, dryrun=dryrun
        )
        if feedback:
            updated += 1
            click.echo(f"{n}/{num} {irei_id} {feedback}")
    click.echo(f"{updated} updated in {datetime.now() - start}")

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
def create(hosts):
    """Create specified Elasticsearch index and upload mappings.
    """
    docstore.DocstoreManager(
        models.INDEX_PREFIX, hosts_index(hosts), settings
    ).create_indices()

def hosts_index(hosts):
    if not hosts:
        click.echo('Set host using --host or the ES_HOST environment variable.')
        sys.exit(1)
    return publish.make_hosts(hosts)

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.option('--confirm', is_flag=True,
              help='Yes I really want to delete this index.')
def destroy(hosts, confirm):
    """Destroy specified Elasticsearch index and all its records.
    
    Think twice before you do this, then think again.
    """
    """Delete indices (requires --confirm).
    
    \b
    It's meant to sound serious. Also to not clash with 'delete', which
    is for individual documents.
    """
    if confirm:
        docstore.DocstoreManager(
            models.INDEX_PREFIX, hosts_index(hosts), settings
        ).delete_indices()
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
def status(hosts):
    """Print status info.
    
    More detail since you asked.
    """
    ds = docstore.Docstore(models.INDEX_PREFIX, hosts_index(hosts), settings)
    s = ds.status()
    
    print('------------------------------------------------------------------------',0)
    print('Elasticsearch')
    # config file
    print('DOCSTORE_HOST  (default): %s' % hosts)
    
    try:
        pingable = ds.es.ping()
        if not pingable:
            print("Can't ping the cluster!")
            return
    except elasticsearch.exceptions.ConnectionError:
        print("Connection error when trying to ping the cluster!")
        return
    print('ping ok')
    
    print('Indexes')
    index_names = ds.es.indices.stats()['indices'].keys()
    for i in index_names:
        print('- %s' % i)


TEST_DATA = {
    'person': [
        '88922/nr007bb08',  # Sumida Chimata
        '88922/nr009tb36',  # Nagatomi Shinjo
        '88922/nr015xj9z',  # Mitsuko Isoshima
        '88922/nr009p41d',  # Florence Nobuko Kuwata
        '88922/nr009pw68',  # Akio Matsumoto
        '88922/nr009dd8h',  # Fumiko Hayashida
        '88922/nr009s43n',  # Moritani Tatsukichi
        '88922/nr012cq3s',  # Kazuko Kay Nakao
    ],
    'farrecord': [
        'rohwer1-9215',   # Sumida Chimata
        'manzanar1-5772',  # Nagatomi Shinjo
        'minidoka1-2836',  # Mitsuko Isoshima
        'manzanar1-4281',  # Florence Nobuko Kuwata
        'manzanar1-4564',  # Akio Matsumoto
        'manzanar1-1461',  # Fumiko Hayashida
        'manzanar1-5360',  # Moritani Tatsukichi
        'manzanar1-7724',  # Kazuko Kay Nakao
    ],
    'wrarecord': [
        '82360',  # Sumida Chimata
        '54456',  # Nagatomi Shinjo
        '24142',  # Mitsuko Isoshima
        '41400',  # Florence Nobuko Kuwata
        '44050',  # Akio Matsumoto
        '14485',  # Fumiko Hayashida
        '51394',  # Moritani Tatsukichi
        '72862',  # Kazuko Kay Nakao
    ],
    'ireirecord': [
        '956ce608-1388-4c5a-bc6b-e3c77969d7c8',  # Sumida Chimata
        '47d685ad-a416-4192-a3c2-09e6a67c03c6',  # Nagatomi Shinjo
        'd7e283ae-4816-4c13-a2ce-ad296303be3f',  # Mitsuko Isoshima
        '9691522b-dee8-400e-812a-fca2ef3f4885',  # Florence Nobuko Kuwata
        'a6f91266-c2ea-47cb-943c-5b8653dba7f0',  # Akio Matsumoto
        '527cbf49-01aa-41ed-aecb-0d95dc71b378',  # Fumiko Hayashida
        '6c26e163-7127-430e-9a0c-3e61a964fda1',  # Moritani Tatsukichi
        '315332aa-a0c5-4547-a0a8-81d2120bf8f6',  # Kazuko Kay Nakao
    ],
}

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.option('--limit','-l', default=200_000, help='Limit number of records.')
@click.option('--id','-id', default=None, help='Post the specified ID.')
@click.option('--file','-f', default=None, help='Post records with IDs from file.')
@click.option('--since','-s', default=None, help='Post records updated since date.')
@click.option('--test','-T', is_flag=True, default=False, help='Post test data.')
@click.option('--debug','-d', is_flag=True, default=False)
@click.argument('model')
def post(hosts, limit, id, file, since, test, debug, model):
    """Post data from SQL database to Elasticsearch.
    """
    # check inputs
    MODELS = [
        'person', 'farrecord', 'far', 'wrarecord', 'wra', 'farpage',
        'personlocation', 'facility', 'location',
        'ireirecord', 'irei',
    ]
    if model not in MODELS:
        click.echo(f'Sorry, model has to be one of {MODELS}')
        sys.exit(1)
    model = model_w_abbreviations(model.lower().strip())
    ds = docstore.DocstoreManager(
        models.INDEX_PREFIX, hosts_index(hosts), settings
    )
    if file:
        file = Path(file)
        if not (file.exists() and file.is_file() and os.access(file, os.R_OK)):
            click.echo(f'ERROR: Not a readable file: "{file}".')
            sys.exit(1)
    if since:
        if not model in ['person','farrecord','wrarecord','ireirecord']:
            click.echo(f'ERROR: --since not implemented for {model}.')
            sys.exit(1)
        try:
            since = parser.parse(since)
        except parser._parser.ParserError as err:
            click.echo(f"ERROR: Bad arg for --since: {err}")
            sys.exit(1)
    if limit:
        limit = int(limit)

    # load related info
    click.echo('Gathering relations')
    related = {}
    if model == 'person':
        related['far_records'] = models.Person.related_farrecords()
        related['wra_records'] = models.Person.related_wrarecords()
        related['family'] = models.Person.related_family()
    elif model in ['farrecord', 'far']:
        related['persons'] = models.FarRecord.related_persons()
        related['family'] = models.FarRecord.related_family()
    elif model in ['wrarecord', 'wra']:
        related['persons'] = models.WraRecord.related_persons()
        related['family'] = models.WraRecord.related_family()
    elif model in ['ireirecord', 'irei']:
        related['persons'] = models.IreiRecord.related_persons()
    elif model == 'personlocation':
        related['persons'] = models.PersonLocation.related_persons()
        related['locations'] = models.PersonLocation.related_locations()
        related['facilities'] = models.PersonLocation.related_facilities()

    # select records to post
    click.echo('Loading from database')
    sql_class = models.MODEL_CLASSES[model]
    # TODO stretching this metaphor too far - revise
    if test:
        if model == 'person':
            records = sql_class.objects.filter(nr_id__in=TEST_DATA['person'])
        elif model == 'personlocation':
            records = sql_class.objects.filter(person_id__in=TEST_DATA['person'])
        elif model == 'farrecord':
            records = sql_class.objects.filter(
                far_record_id__in=TEST_DATA['farrecord']
            )
        elif model == 'wrarecord':
            records = sql_class.objects.filter(
                wra_record_id__in=TEST_DATA['wrarecord']
            )
        elif model == 'ireirecord':
            records = sql_class.objects.filter(
                irei_id__in=TEST_DATA['ireirecord']
            )
        else:
            print(f"ERR test in {TEST_DATA.keys()}"); sys.exit(1)
    else:
        # specific record
        if id:
            if model == 'person':
                records = sql_class.objects.filter(nr_id=id)[:limit]
            elif model == 'personlocation':
                records = sql_class.objects.filter(person_id=id)[:limit]
            elif model == 'farrecord':
                records = sql_class.objects.filter(far_record_id=id)[:limit]
            elif model == 'wrarecord':
                records = sql_class.objects.filter(wra_record_id=id)[:limit]
            elif model == 'ireirecord':
                records = sql_class.objects.filter(irei_id=id)[:limit]
        # records with IDs in FILE
        elif file:
            with file.open('r') as f:
                ids = [line.strip() for line in f.readlines()]
            if model == 'person':
                records = sql_class.objects.filter(nr_id__in=ids)
            elif model == 'personlocation':
                records = sql_class.objects.filter(person_id__in=ids)
            elif model == 'farrecord':
                records = sql_class.objects.filter(far_record_id__in=ids)
            elif model == 'wrarecord':
                records = sql_class.objects.filter(wra_record_id__in=ids)
            elif model == 'ireirecord':
                records = sql_class.objects.filter(irei_id__in=ids)
        # records updated since DATE(TIME)
        elif since:
            records = sql_class.objects.filter(timestamp__gte=since)[:limit]
        # everything
        else:
            records = sql_class.objects.all()[:limit]

    # now post them
    # TODO refactor use elasticsearch.helpers.bulk
    failed = []
    for record in tqdm(
        records, desc='Writing to Elasticsearch', ascii=True, unit='record'
    ):
        try:
            record.post(related, ds)
        except:
            failed.append(record)
    if failed:
        click.echo(f"FAIL {record}")

def _make_record_url(hosts, model, record_id):
    return f'http://{hosts}/{models.INDEX_PREFIX}{model}/_doc/{record_id}'

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.argument('model')
@click.argument('record_id')
def url(hosts, model, record_id):
    """URL of the specified Elasticsearch record
    """
    click.echo(_make_record_url(hosts, model, record_id))

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.option('--json','-j', is_flag=True, default=False)
@click.argument('model')
@click.argument('record_id')
def get(hosts, json, model, record_id):
    """Get specified Elasticsearch record JSON
    """
    model = model_w_abbreviations(model)
    if json:
        # the slash in Person.nr_id is unsafe in URLs
        record_id = record_id.replace('/', '%2F')
        url = _make_record_url(hosts, model, record_id)
        if settings.DOCSTORE_PASSWORD:
            r = httpx.get(
                url, auth=(settings.DOCSTORE_USERNAME, settings.DOCSTORE_PASSWORD)
            )
        else:
            r = httpx.get(url)
        if r.status_code == HTTPStatus.OK:
            click.echo(r.text)
        else:
            click.echo(f'{r.status_code} {r.reason}')
    else:
        ds = docstore.Docstore(models.INDEX_PREFIX, hosts_index(hosts), settings)
        es_class = models_public.ELASTICSEARCH_CLASSES_BY_MODEL[model]
        record = es_class.get(id=record_id, using=ds.es)
        click.echo(record)

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.argument('model')
@click.argument('record_id')
def delete(hosts, model, record_id):
    """Delete records in CSV file from Elasticsearch.
    """
    model = model_w_abbreviations(model)
    ds = docstore.DocstoreManager(
        models.INDEX_PREFIX, hosts_index(hosts), settings
    )
    es_class = models_public.ELASTICSEARCH_CLASSES_BY_MODEL[model]
    try:
        record = es_class.get(id=record_id, using=ds.es)
        result = record.delete(using=ds.es)
    except docstore.NotFoundError as err:
        click.echo(err)

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.option('--sql','-s', is_flag=True, default=False)
@click.option('--elastic','-e', is_flag=True, default=False)
@click.option('--noheaders','-n', is_flag=True, default=False)
@click.argument('csvfile')
def searchmulti(hosts, sql, elastic, noheaders, csvfile):
    """Reads output of `ddrnames dump` and suggests Person records for each name
    
    \b
    Run `ddrnames help` to learn how to produce source data.

    \b
    Examples:
        namesdb searchmulti /tmp/ddr-csujad-30-creators.csv --elastic
        namesdb searchmulti /tmp/ddr-csujad-30-creators.csv --sql

    \b
    This command returns CSV-formatted data with the following fields:
        ddr_id, name_text, match_name, match_nrid, match_score
    
    \b
    If you don't see results, you may need to prepare the SQLite database
    for full-text search:
        sqlite-utils enable-fts --fts5 db/namesregistry.db names_person nr_id family_name given_name given_name_alt other_names middle_name prefix_name suffix_name jp_name preferred_name
    
    \b
    If you get results but they look wrong, you may disable and re-enable
    full-text search.  Run this before the previous command
        sqlite-utils disable-fts db/namesregistry.db names_person
    """
    if elastic: method = 'elastic'
    elif sql: method = 'sql'
    else:
        click.echo('ERROR: Must choose --elastic or --sql.')
        sys.exit(1)
    for row in batch.search_multi(csvfile, method, not noheaders):
        click.echo(row)

@namesdb.command()
@click.option('--debug','-d', is_flag=True, default=False)
def exportdb(debug):
    """Copy SQLite3 database, removing Django-specific tables
    """
    src = settings.DATABASES['names']['NAME']
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    dst = os.path.join(
        os.path.dirname(src), f'namesregistry-{timestamp}.sqlite3'
    )
    # copy database file
    if debug:
        click.echo('Copying database')
        click.echo(f'cp {src} {dst}')
    shutil.copy(src,dst)
    # open copied db with sqlite3
    c = sqlite3.connect(dst).cursor()
    if debug:
        click.echo('Getting table names')
    schema = c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    if debug:
        click.echo('Dropping Django tables')
    for t in schema:
        tablename = t[0]
        if not (tablename.startswith('names_') or tablename.startswith('sqlite_')):
            query = f'DROP TABLE {tablename}'
            if debug:
                click.echo(query)
            c.execute(query)
    # clean up
    c.close()
    click.echo(dst)

def model_w_abbreviations(model):
    if model in ['far','wra','irei']:
        # enable using 'far','wra' abbreviations
        model = f'{model}record'
    return model
