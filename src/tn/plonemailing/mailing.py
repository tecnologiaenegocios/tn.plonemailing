from five import grok
from Products.MailHost.interfaces import IMailHost
from tn.plonemailing.behaviors import INewsletterFromContent
from tn.plonemailing import interfaces
from zope.event import notify

try:
    from zope.component.hooks import getSite
    getSite  # pyflakes / flake8
except ImportError:
    from zope.site.hooks import getSite

import zope.component


class NewsletterSentEvent(object):
    grok.implements(interfaces.INewsletterSentEvent)

    def __init__(self, newsletter, subscriber, message):
        self.object     = newsletter.context
        self.newsletter = newsletter
        self.subscriber = subscriber
        self.message    = message


class Mailing(grok.GlobalUtility):
    """See `interfaces.IMailing`.
    """
    grok.implements(interfaces.IMailing)

    def send(self, context, suppress_events=False,
             subscribers=None, mailhost=None):

        newsletter = interfaces.INewsletter(context)
        mailhost   = mailhost or self.get_mail_host()

        subscribers = subscribers or self.iter_subscribers(context)
        for subscriber in subscribers:
            message = newsletter.compile(subscriber)
            mailhost.send(message)
            if not suppress_events:
                notify(NewsletterSentEvent(newsletter, subscriber, message))

    def iter_subscribers(self, context):
        return INewsletterFromContent(context).subscribers

    def get_mail_host(self):
        site = getSite()
        for id in site.objectIds():
            candidate = site[id]
            if interfaces.IMailHost.providedBy(candidate):
                return candidate
        return zope.component.getUtility(IMailHost)
