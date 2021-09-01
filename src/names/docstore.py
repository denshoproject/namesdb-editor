import logging
logger = logging.getLogger(__name__)
from ssl import create_default_context
import sys

from django.conf import settings

from elasticsearch import Elasticsearch, TransportError, NotFoundError
import elasticsearch_dsl
logging.getLogger("elasticsearch").setLevel(logging.WARNING)

from . import models

DOCSTORE_TIMEOUT = 5
INDEX_PREFIX = 'names'

def get_elasticsearch():
    # TODO simplify this once everything is using SSL/passwords
    if settings.DOCSTORE_SSL_CERTFILE and settings.DOCSTORE_PASSWORD:
        context = create_default_context(cafile=settings.DOCSTORE_SSL_CERTFILE)
        context.check_hostname = False
        return Elasticsearch(
            settings.DOCSTORE_HOST,
            scheme='https', ssl_context=context,
            port=9200,
            http_auth=(settings.DOCSTORE_USERNAME, settings.DOCSTORE_PASSWORD),
        )
    elif settings.DOCSTORE_SSL_CERTFILE:
        context = create_default_context(cafile=settings.DOCSTORE_SSL_CERTFILE)
        context.check_hostname = False
        return Elasticsearch(
            settings.DOCSTORE_HOST,
            scheme='https', ssl_context=context,
            port=9200,
        )
    else:
        return Elasticsearch(
            settings.DOCSTORE_HOST,
            scheme='http',
            port=9200,
        )


class Docstore():
    hosts = None
    facets = None
    es = None

    def __init__(self, hosts=settings.DOCSTORE_HOST):
        self.hosts = hosts
        self.es = get_elasticsearch()
    
    def index_name(self, model):
        return '{}{}'.format(INDEX_PREFIX, model)
    
    def __repr__(self):
        return "<%s.%s %s:%s*>" % (
            self.__module__, self.__class__.__name__, self.hosts, INDEX_PREFIX
        )
    
    def health(self):
        try:
            return self.es.cluster.health()
        except TransportError as err:
            print(err)
            sys.exit(1)
    
    def index_exists(self, indexname):
        """
        """
        self.health()
        return self.es.indices.exists(index=indexname)
    
    def status(self):
        """Returns status information from the Elasticsearch cluster.
        
        >>> docstore.Docstore().status()
        {
            u'indices': {
                u'ddrpublic-dev': {
                    u'total': {
                        u'store': {
                            u'size_in_bytes': 4438191,
                            u'throttle_time_in_millis': 0
                        },
                        u'docs': {
                            u'max_doc': 2664,
                            u'num_docs': 2504,
                            u'deleted_docs': 160
                        },
                        ...
                    },
                    ...
                }
            },
            ...
        }
        """
        self.health()
        return self.es.indices.stats()
    
    def index_names(self):
        """Returns list of index names
        """
        return [name for name in self.status()['indices'].keys()]
    
    def create_indices(self):
        """Create indices for each model defined in namesdb/models.py
        
        See also ddr-defs/repo_models/elastic.py
        """
        self.health()
        statuses = []
        for i in models.ELASTICSEARCH_CLASSES['all']:
            status = self.create_index(
                self.index_name(i['doctype']),
                i['class']
            )
            statuses.append(status)
        return statuses
    
    def create_index(self, indexname, dsl_class):
        """Creates the specified index if it does not already exist.
        
        Uses elasticsearch-dsl classes defined in namesdb/models.py
        See also ddr-defs/repo_models/elastic.py
        
        @param indexname: str
        @param dsl_class: elasticsearch_dsl.Document class
        @returns: JSON dict with status codes and responses
        """
        logger.debug('creating index {}'.format(indexname))
        if self.index_exists(indexname):
            status = '{"status":400, "message":"Index exists"}'
            logger.debug('Index exists')
            #print('Index exists')
        else:
            index = elasticsearch_dsl.Index(indexname)
            #print('index {}'.format(index))
            index.aliases(default={})
            #print('registering')
            out = index.document(dsl_class).init(index=indexname, using=self.es)
            if out:
                status = out
            elif self.index_exists(indexname):
                status = {
                    "name": indexname,
                    "present": True,
                }
            #print(status)
            #print('creating index')
        return status
    
    def delete_indices(self):
        """Deletes indices for each model defined in namesdb/models.py
        
        See also ddr-defs/repo_models/elastic.py
        """
        self.health()
        statuses = []
        for i in models.ELASTICSEARCH_CLASSES['all']:
            status = self.delete_index(
                self.index_name(i['doctype'])
            )
            statuses.append(status)
        return statuses
    
    def delete_index(self, indexname):
        """Delete the specified index.
        
        @returns: JSON dict with status code and response
        """
        logger.debug('deleting index: %s' % indexname)
        if self.index_exists(indexname):
            status = self.es.indices.delete(index=indexname)
        else:
            status = {
                "name": indexname,
                "status": 500,
                "message": "Index does not exist",
            }
        logger.debug(status)
        return status
