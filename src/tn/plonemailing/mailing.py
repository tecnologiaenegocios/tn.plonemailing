from five import grok
from tn.plonemailing.behaviors import INewsletterFromContent
from tn.plonemailing import interfaces
from tn.plonemailing.mailhost import getMailHost
from zope.component.event import dispatch
from zope.event import notify


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
        return getMailHost()
