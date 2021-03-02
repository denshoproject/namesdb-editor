import logging
import sys

from . import docstore
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

def get_records(ds, model, limit=None, debug=False):
    model = model.lower().strip()
    sql_class = models.MODEL_CLASSES[model]
    es_class = models.ELASTICSEARCH_CLASSES_BY_MODEL[model]
    fieldnames = models.FIELDS_BY_MODEL[model]
    if limit:
        records = sql_class.objects.all()[:limit]
    else:
        records = sql_class.objects.all()
    return records,es_class

def post_record(model, record, es_class, ds):
    data = record.dict()
    record_id = data["id"]
    #logging.info(f'{n+1}/{num_rows} {record_id}')
    document = es_class.from_dict(record_id, data)
    result = document.save(
        index=ds.index_name(model), using=ds.es
    )
    if result not in ['created', 'updated']:
        logging.info(f'result {result}')
