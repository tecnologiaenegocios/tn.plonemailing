from Products.MailHost.interfaces import IMailHost
from tn.plonemailing import behaviors
from tn.plonemailing import interfaces
from tn.plonemailing import mailing
from zope.app.testing import placelesssetup

try:
    from zope.component.hooks import setSite
    setSite # pyflakes
except ImportError:
    from zope.site.hooks import setSite

import stubydoo
import unittest
import zope.component
import zope.interface


class TestMailingBase(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)

        self.mailhost = stubydoo.double()

        class IPossibleSubscriberProvider(zope.interface.Interface): pass
        self.subscriber = stubydoo.double()
        self.subscribers = [self.subscriber]
        self.newsletter = stubydoo.double()
        self.message = stubydoo.double()

        stubydoo.stub(self.newsletter, 'compile').with_args(self.subscriber).\
                and_return(self.message)
        stubydoo.stub(self.mailhost, 'send').with_args(self.message)

        @zope.component.adapter(None)
        @zope.interface.implementer(interfaces.INewsletter)
        def newsletter_adapter(context):
            self.newsletter.context = context
            return self.newsletter
        zope.component.provideAdapter(newsletter_adapter)

        self.context = stubydoo.double()
        self.mailing = mailing.Mailing()

    def tearDown(self):
        placelesssetup.tearDown()

    def configure_newsletter_from_content_behavior(self):

        possible_subscriber_provider = stubydoo.double()

        subscriber_provider = stubydoo.double(
            subscribers=lambda _self: self.subscribers
        )
        self.behavior = stubydoo.double(
            possible_subscriber_providers=[possible_subscriber_provider]
        )

        @zope.component.adapter(None)
        @zope.interface.implementer(behaviors.INewsletterFromContent)
        def behavior_adapter(context):
            return self.behavior
        zope.component.provideAdapter(behavior_adapter)

        @zope.component.adapter(interfaces.IPossibleSubscriberProvider)
        @zope.interface.implementer(interfaces.ISubscriberProvider)
        def subscriber_provider_adapter(subscribers):
            return subscriber_provider
        zope.component.provideAdapter(subscriber_provider_adapter)

        zope.interface.alsoProvides(possible_subscriber_provider,
                                    interfaces.IPossibleSubscriberProvider)


@stubydoo.assert_expectations
class TestMailingSend(TestMailingBase):

    def test_send(self):
        stubydoo.expect(self.mailhost, 'send').with_args(self.message)
        self.mailing.send(self.context,
                          subscribers=self.subscribers,
                          mailhost=self.mailhost)

    def test_send_without_specifying_subscribers(self):
        self.configure_newsletter_from_content_behavior()

        stubydoo.expect(self.mailhost, 'send').with_args(self.message)
        self.mailing.send(self.context, mailhost=self.mailhost)

    def test_send_should_fire_event(self):
        @zope.component.adapter(None, interfaces.INewsletterSentEvent)
        def handler(object, event):
            self.object = object
            self.event  = event
        zope.component.provideHandler(handler)

        # This is normally grokked during application startup.
        zope.component.provideHandler(mailing.dispatch_to_context)

        self.mailing.send(self.context, mailhost=self.mailhost,
                          subscribers=self.subscribers)

        self.assertTrue(self.object is self.context)
        self.assertTrue(self.event.newsletter is self.newsletter)
        self.assertTrue(self.event.subscriber is self.subscriber)
        self.assertTrue(self.event.message    is self.message)


@stubydoo.assert_expectations
class TestMailingIterSubscribers(TestMailingBase):

    def test_iter_subscribers(self):
        self.configure_newsletter_from_content_behavior()

        result = list(self.mailing.iterSubscribers(self.context))
        self.assertEquals(result, self.subscribers)


@stubydoo.assert_expectations
class TestMailHost(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)
        self.portal = self.make_portal()
        setSite(self.portal)
        self.provide_mailhost(self.make_mailhost('MailHost'))

        self.portal['folder'] = stubydoo.double()

        self.mailing = mailing.Mailing()

    def tearDown(self):
        placelesssetup.tearDown()

    def make_portal(self):
        portal_class = type('dict', (dict,), dict(
            objectIds=lambda self:self.keys(),
            getSiteManager=lambda self:stubydoo.double()
        ))
        return portal_class()

    def make_mailhost(self, id):
        mailhost = stubydoo.double()
        zope.interface.alsoProvides(mailhost, IMailHost)
        self.portal[id] = mailhost
        return mailhost

    def provide_mailhost(self, mailhost):
        zope.component.provideUtility(mailhost)
        return mailhost

    def test_no_special_mailhost_marked(self):
        self.assertTrue(self.mailing.getMailHost() is self.portal['MailHost'])

    def test_special_mailhost_marked(self):
        other_mailhost = self.make_mailhost('OtherMailHost')
        zope.interface.alsoProvides(other_mailhost, interfaces.IMailHost)

        self.assertTrue(self.mailing.getMailHost() is other_mailhost)
