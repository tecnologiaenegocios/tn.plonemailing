from Products.CMFCore.utils import getToolByName
from Products.MailHost.MailHost import MailHost
from tn.plonemailing import interfaces
from zope.location.interfaces import ISite
from zope.interface import noLongerProvides

def install(context):
    portal = getToolByName(context, 'portal_url').getPortalObject()
    sm = ISite(portal).getSiteManager()
    add_local_mail_host_utility(portal, sm)

def uninstall(context):
    portal = getToolByName(context, 'portal_url').getPortalObject()
    sm = ISite(portal).getSiteManager()
    del_local_mail_host_utility(portal, sm)

def add_local_mail_host_utility(portal, sm):
    utility = sm.queryUtility(interfaces.IMailHost, default=None)
    if utility is None:
        for obj_id in portal.objectIds():
            obj = portal[obj_id]
            if not isinstance(obj, MailHost):
                continue
            if not interfaces.IMailHost.providedBy(obj):
                continue
            sm.registerUtility(obj, provided=interfaces.IMailHost)

def del_local_mail_host_utility(portal, sm):
    utility = sm.queryUtility(interfaces.IMailHost, default=None)
    if utility is not None:
        sm.unregisterUtility(utility, provided=interfaces.IMailHost)
        for obj_id in portal.objectIds():
            obj = portal[obj_id]
            if interfaces.IMailHost.providedBy(obj):
                noLongerProvides(obj, interfaces.IMailHost)
