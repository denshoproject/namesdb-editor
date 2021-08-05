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
    $ namesdb post -H localhost:9200 /tmp/namesdb-data/far-manzanar.csv
    
    # Print Elasticsearch URL for record
    $ namesdb url -H localhost:9200 person 0a1b2c3d4e
    
    # Get record JSON from Elasticsearch
    $ namesdb get -H localhost:9200 person 0a1b2c3d4e
    
    # Delete records from Elasticsearch
    $ namesdb delete -H localhost:9200 person 0a1b2c3d4e

Note: You can set environment variables for HOSTS and INDEX.:

    $ export ES_HOSTS=localhost:9200

"""

from datetime import datetime
import os
import shutil
import sqlite3
import sys

import click
# Django must be initialized before settings can be accessed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'editor.settings')
import django
django.setup()
from django.conf import settings
import requests
from tqdm import tqdm

from . import csvfile
from . import docstore
from . import fileio
from . import models
from . import publish
from namesdb_public import models as models_public


@click.group()
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
@click.option('--limit','-l', default=None)
@click.argument('model')
@click.argument('csv_path')
@click.argument('username')
def load(debug, limit, model, csv_path, username):
    """Load data from a CSV file
    """
    if limit:
        limit = int(limit)
    sql_class = models.MODEL_CLASSES[model]
    for rowd in tqdm(
            csvfile.make_rowds(fileio.read_csv(csv_path, limit)),
            desc='Writing database', ascii=True, unit='record'
    ):
        sql_class.load_rowd(rowd).save(rowd, username, note='Load from CSV')

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
def create(hosts):
    """Create specified Elasticsearch index and upload mappings.
    """
    hosts = hosts_index(hosts)
    docstore.Docstore(hosts).create_indices()

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
        hosts = hosts_index(hosts)
        docstore.Docstore(hosts).delete_indices()
    else:
        click.echo("Add '--confirm' if you're sure you want to do this.")

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
def status(hosts):
    """Print status info.
    
    More detail since you asked.
    """
    ds = docstore.Docstore(hosts)
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

@namesdb.command()
@click.option('--hosts','-H', envvar='ES_HOST', help='Elasticsearch hosts.')
@click.option('--limit','-l', help='Limit number of records.')
@click.option('--debug','-d', is_flag=True, default=False)
@click.argument('model')
def post(hosts, limit, debug, model):
    """Post data from SQL database to Elasticsearch.
    """
    model = model_w_abbreviations(model.lower().strip())
    hosts = hosts_index(hosts)
    ds = docstore.Docstore(hosts)
    if limit:
        limit = int(limit)
    
    click.echo('Gathering relations')
    related = {}
    if model == 'person':
        related['facilities'] = models.Person.related_facilities()
        related['far_records'] = models.Person.related_farrecords()
        related['wra_records'] = models.Person.related_wrarecords()
    elif model in ['farrecord', 'far']:
        related['persons'] = models.FarRecord.related_persons()
    elif model in ['wrarecord', 'wra']:
        related['persons'] = models.WraRecord.related_persons()
    
    click.echo('Loading from database')
    sql_class = models.MODEL_CLASSES[model]
    if limit:
        records = sql_class.objects.all()[:limit]
    else:
        records = sql_class.objects.all()
    for record in tqdm(
        records, desc='Writing to Elasticsearch', ascii=True, unit='record'
    ):
        record.post(related, ds)

def _make_record_url(hosts, model, record_id):
    return f'http://{hosts}/{models_public.PREFIX}{model}/_doc/{record_id}'

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
        url = _make_record_url(hosts, model, record_id)
        r = requests.get(url)
        if r.status_code == 200:
            click.echo(r.text)
        else:
            click.echo(f'{r.status_code} {r.reason}')
    else:
        hosts = hosts_index(hosts)
        ds = docstore.Docstore(hosts)
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
    hosts = hosts_index(hosts)
    ds = docstore.Docstore(hosts)
    es_class = models_public.ELASTICSEARCH_CLASSES_BY_MODEL[model]
    try:
        record = es_class.get(id=record_id, using=ds.es)
        result = record.delete(using=ds.es)
    except docstore.NotFoundError as err:
        click.echo(err)

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
    if model in ['far','wra']:
        # enable using 'far','wra' abbreviations
        model = f'{model}record'
    return model
