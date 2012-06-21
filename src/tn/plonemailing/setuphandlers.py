from Products.CMFCore.utils import getToolByName
from tn.plonemailing import _

import logging


def setupVarious(context):
    if context.readDataFile('tn.plonemailing.marker.txt') is None:
        return
    portal = context.getSite()
    addIndexesAndMetadata(portal, context.getLogger('tn.plonemailing'))

def addIndexesAndMetadata(context, logger=None):
    portal = getToolByName(context, 'portal_url').getPortalObject()
    if logger is None:
        logger = logging.getLogger('tn.plonemailing')
    addIndexes(portal, logger)
    addIndexesAndMetadataToTopics(portal, logger)

def addIndexes(portal, logger):
    catalog = getToolByName(portal, 'portal_catalog')
    current_indexes = catalog.indexes()
    wanted_indexes  = (('sortable_last_sent', 'DateIndex'),
                       ('last_sent', 'DateIndex'))

    indexables = []
    for name, meta_type in wanted_indexes:
        if name not in current_indexes:
            catalog.addIndex(name, meta_type)
            indexables.append(name)
            logger.info("Added %s for field %s.", meta_type, name)
    if len(indexables) > 0:
        logger.info("Indexing new indexes %s.", ', '.join(indexables))
        catalog.manage_reindexIndex(ids=indexables)

def addIndexesAndMetadataToTopics(portal, logger):
    atcttool = getToolByName(portal, 'portal_atct')
    title = _(u'Issue date')
    desc  = _(u'The time and date an item was last sent')
    atcttool.addIndex('sortable_last_sent',
                      title,
                      description=desc,
                      enabled=True)
    atcttool.addMetadata('last_sent',
                         title,
                         description=desc,
                         enabled=True)
