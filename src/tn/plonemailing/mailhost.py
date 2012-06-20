from Products.MailHost.interfaces import IMailHost
from tn.plonemailing import interfaces

try:
    from zope.component.hooks import getSite
except ImportError:
    from zope.site.hooks import getSite

import zope.interface
import zope.component


def getMailHost():
    """Return the site's mailhost.

    A marked mailhost instance (with `interfaces.IMailHost`) from the
    site root is returned if found, fallback to the default mailhost
    utility.

    A marked mailhost can then be targeted to mass mailing, keeping the
    default mailhost utility for normal delivery.

    This function can be quite expensive if the site root has a lot of
    objects, but it shouldn't anyway.
    """
    site = getSite()
    for id in site.objectIds():
        candidate = site[id]
        if interfaces.IMailHost.providedBy(candidate):
            return candidate
    return zope.component.getUtility(IMailHost)
