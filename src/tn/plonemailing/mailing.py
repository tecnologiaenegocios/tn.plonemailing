from five import grok
from Products.MailHost.interfaces import IMailHost
from tn.plonemailing.behaviors import INewsletterFromContent
from tn.plonemailing import interfaces
from zope.component.event import dispatch
from zope.event import notify

try:
    from zope.component.hooks import getSite
    getSite # pyflakes
except ImportError:
    from zope.site.hooks import getSite

import zope.component


class NewsletterSentEvent(object):
    grok.implements(interfaces.INewsletterSentEvent)

    def __init__(self, newsletter, subscriber, message):
        self.newsletter = newsletter
        self.subscriber = subscriber
        self.message    = message


@grok.subscribe(interfaces.INewsletterSentEvent)
def dispatch_to_context(event):
    dispatch(event.newsletter.context, event)


class Mailing(grok.GlobalUtility):
    """See `interfaces.IMailing`.
    """
    grok.implements(interfaces.IMailing)

    def send(self, context, subscribers=None, mailhost=None):
        newsletter = interfaces.INewsletter(context)
        mailhost = mailhost or self.getMailHost()
        subscribers = subscribers or self.iterSubscribers(context)
        for subscriber in subscribers:
            message = newsletter.compile(subscriber)
            mailhost.send(message)
            notify(NewsletterSentEvent(newsletter, subscriber, message))

    def iterSubscribers(self, context):
        behavior = INewsletterFromContent(context)
        for possible_provider in behavior.possible_subscriber_providers:
            provider = interfaces.ISubscriberProvider(possible_provider)
            for subscriber in provider.subscribers():
                yield subscriber

    def getMailHost(self):
        site = getSite()
        for id in site.objectIds():
            candidate = site[id]
            if interfaces.IMailHost.providedBy(candidate):
                return candidate
        return zope.component.getUtility(IMailHost)
