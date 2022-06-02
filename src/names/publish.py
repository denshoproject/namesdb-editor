import logging
import sys

from . import models
from namesdb_public import models as pubmodels

def set_logging(level, stream=sys.stdout):
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)-8s %(message)s',
        stream=stream,
    )

LOGGING_LEVEL = 'INFO'
set_logging(LOGGING_LEVEL, stream=sys.stdout)


def make_hosts(text):
    hosts = []
    for host in text.split(','):
        h,p = host.split(':')
        hosts.append( {'host':h, 'port':p} )
    return hosts
