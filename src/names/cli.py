DESCRIPTION = """"""

HELP = """
Sample usage:

    # Export data without Django-specific tables
    $ namesdb export
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
