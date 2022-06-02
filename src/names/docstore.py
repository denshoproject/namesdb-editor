import logging
logger = logging.getLogger(__name__)

from elastictools import docstore

from . import models


class Docstore(docstore.Docstore):

    def __init__(self, index_prefix, host, settings):
        super(Docstore, self).__init__(index_prefix, host, settings)


class DocstoreManager(docstore.DocstoreManager):

    def __init__(self, index_prefix, host, settings):
        super(DocstoreManager, self).__init__(index_prefix, host, settings)

    def create_indices(self):
        return super(DocstoreManager,self).create_indices(
            models.ELASTICSEARCH_CLASSES['all']
        )

    def delete_indices(self):
        return super(DocstoreManager,self).delete_indices(
            models.ELASTICSEARCH_CLASSES['all']
        )
