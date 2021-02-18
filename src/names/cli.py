DESCRIPTION = """"""

HELP = """
Sample usage:

    # Export data without Django-specific tables
    $ namesdb export

    # Create and destroy Elasticsearch indexes
    $ namesdb create -H localhost:9200
    $ namesdb destroy -H localhost:9200 --confirm

    # Check status
    $ namesdb status -H localhost:9200

Note: You can set environment variables for HOSTS and INDEX.:

    $ export ES_HOSTS=localhost:9200
    $ export ES_INDEX=namesdb-dev

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

from . import docstore
from . import publish


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
@click.option('--debug','-d', is_flag=True, default=False)
def export(debug):
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
