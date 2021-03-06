from datetime import datetime
from tn.plonemailing import newsletter
from tn.plonemailing import interfaces
from zope.app.testing import placelesssetup
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

import premailer
import stubydoo
import unittest
import zope.component
import zope.interface


class GlobalConfiguration(object):
    zope.interface.implements(interfaces.IConfiguration)

    def __init__(self, **kw):
        for attr, value in kw.items():
            setattr(self, attr, value)


class TestNewsletter(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)

        self.configuration = GlobalConfiguration(
            subscriber_name_xpath=u'',
            add_subscriber_preferences=False,
            subscriber_preferences_url_xpath=u'',
            subscriber_preferences_html=u'',
            add_subscriber_removal=True,
            subscriber_removal_url_xpath=u'',
            subscriber_removal_html=u'',
            inline_styles=False,
        )
        zope.component.provideUtility(self.configuration)

        self.newsletter_attributes = stubydoo.double()
        self.context = stubydoo.double()
        request = object()
        self.newsletter = newsletter.Newsletter(self.context,
                                                request,
                                                self.newsletter_attributes)

        self.message_factory = stubydoo.double(__call__=lambda x, c: c)

        @zope.component.adapter(None, None, None, None)
        @zope.interface.implementer(interfaces.IMessageFactory)
        def message_factory_factory(context, request, newsletter, subscriber):
            return self.message_factory

        zope.component.provideAdapter(message_factory_factory)

    def tearDown(self):
        placelesssetup.tearDown()


class TestNewsletterAttributes(TestNewsletter):

    def test_attributes_from_newsletter_attributes(self):
        for attribute in ('author_address', 'author_name',
                          'sender_address', 'sender_name',
                          'reply_to_address', 'reply_to_name',
                          'subject', 'html'):
            value = object()
            setattr(self.newsletter_attributes, attribute, value)
            self.assertEquals(getattr(self.newsletter, attribute), value)


class TestNewsletterInterpolations(TestNewsletter):

    def setUp(self):
        super(TestNewsletterInterpolations, self).setUp()
        self.subscriber = stubydoo.double(
            name=u'',
            preferences_url=u'',
            removal_url=u'',
            format=u'',
        )


class TestSubscriberNameInterpolation(TestNewsletterInterpolations):

    def setUp(self):
        super(TestSubscriberNameInterpolation, self).setUp()
        self.configuration.subscriber_name_xpath = \
            "//*[contains(concat(' ', @class, ' '), ' subscriber-name ')]"
        self.subscriber.name = u'Name'

    def test_interpolation_without_placeholder(self):
        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"
        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_with_placeholder(self):
        self.newsletter_attributes.html = u'<html><body>'\
            u'<p>Welcome, <span class="subscriber-name">John Doe</span></p>'\
            u'</body></html>'

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p>Welcome, <span class="subscriber-name">Name</span></p>'
            u'</body></html>'
        )

    def test_interpolation_honors_configuration(self):
        self.configuration.subscriber_name_xpath = \
            "//em[contains(concat(' ', @class, ' '), ' customer-name ')]"

        self.newsletter_attributes.html = u'<html><body>'\
            u'<p>Welcome, <em class="customer-name">John Doe</em></p>'\
            u'</body></html>'

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p>Welcome, <em class="customer-name">Name</em></p>'
            u'</body></html>'
        )


class TestSubscriberPreferencesInterpolation(TestNewsletterInterpolations):

    def setUp(self):
        super(TestSubscriberPreferencesInterpolation, self).setUp()
        self.configuration.subscriber_preferences_url_xpath = \
            "//a[contains(concat(' ', @class, ' '), ' subscriber-preferences ')]/@href"
        self.subscriber.preferences_url = u'http://example.com/prefs'

    def test_interpolation_without_placeholder_if_should_not_add(self):
        self.configuration.add_subscriber_preferences = False
        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"
        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add(self):
        self.configuration.add_subscriber_preferences = True
        self.configuration.subscriber_preferences_html = \
            u'<p><a href="" class="subscriber-preferences">Prefs</a></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p>Test</p>'
            u'<p><a href="http://example.com/prefs" '
            u'class="subscriber-preferences">Prefs</a></p>'
            u'</body></html>'
        )

    def test_interpolation_without_placeholder_if_should_add_with_wrong_html(self):
        self.configuration.add_subscriber_preferences = True
        self.configuration.subscriber_preferences_html = \
            u'<p><a href="" class="other-class">Prefs</a></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add_with_multiple_wrong_elements_html(self):
        self.configuration.add_subscriber_preferences = True
        self.configuration.subscriber_preferences_html = u'<p></p><p></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add_with_bad_html(self):
        self.configuration.add_subscriber_preferences = True
        self.configuration.subscriber_preferences_html = u'bad html'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add_with_empty_html(self):
        self.configuration.add_subscriber_preferences = True
        self.configuration.subscriber_preferences_html = u''

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_with_placeholder(self):
        self.newsletter_attributes.html = u'<html><body>'\
            u'<p><a href="#" class="subscriber-preferences">Preferences</a></p>'\
            u'</body></html>'

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p><a href="http://example.com/prefs" '
            u'class="subscriber-preferences">Preferences</a></p>'
            u'</body></html>'
        )

    def test_interpolation_honors_configuration(self):
        self.configuration.subscriber_preferences_url_xpath = \
            "//em[contains(concat(' ', @class, ' '), ' customer-prefs ')]"

        self.newsletter_attributes.html = u'<html><body>'\
            u'<p>Follow <em class="customer-prefs">prefs url</em></p>'\
            u'</body></html>'

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p>Follow <em '
            u'class="customer-prefs">http://example.com/prefs</em></p>'
            u'</body></html>'
        )


class TestSubscriberRemovalInterpolation(TestNewsletterInterpolations):

    def setUp(self):
        super(TestSubscriberRemovalInterpolation, self).setUp()
        self.configuration.subscriber_removal_url_xpath = \
            "//a[contains(concat(' ', @class, ' '), ' subscriber-removal ')]/@href"
        self.subscriber.removal_url = u'http://example.com/removal'

    def test_interpolation_without_placeholder_if_should_not_add(self):
        self.configuration.add_subscriber_removal = False
        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"
        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add(self):
        self.configuration.add_subscriber_removal = True
        self.configuration.subscriber_removal_html = \
            u'<p><a href="" class="subscriber-removal">Unsubscribe</a></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p>Test</p>'
            u'<p><a href="http://example.com/removal" '
            u'class="subscriber-removal">Unsubscribe</a></p>'
            u'</body></html>'
        )

    def test_interpolation_without_placeholder_if_should_add_with_wrong_html(self):
        self.configuration.add_subscriber_removal = True
        self.configuration.subscriber_removal_html = \
            u'<p><a href="" class="other-class">Unsubscribe</a></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add_with_multiple_wrong_elements_html(self):
        self.configuration.add_subscriber_removal = True
        self.configuration.subscriber_removal_html = u'<p></p><p></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add_with_multiple_bad_html(self):
        self.configuration.add_subscriber_removal = True
        self.configuration.subscriber_removal_html = u'<p></p><p></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_without_placeholder_if_should_add_with_empty_html(self):
        self.configuration.add_subscriber_removal = True
        self.configuration.subscriber_removal_html = u'<p></p><p></p>'

        self.newsletter_attributes.html = \
            u"<html><body><p>Test</p></body></html>"

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(message_html, self.newsletter_attributes.html)

    def test_interpolation_with_placeholder(self):
        self.newsletter_attributes.html = u'<html><body>'\
            u'<p><a href="#" class="subscriber-removal">Unsubscribe</a></p>'\
            u'</body></html>'

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p><a href="http://example.com/removal" '
            u'class="subscriber-removal">Unsubscribe</a></p>'
            u'</body></html>'
        )

    def test_interpolation_honors_configuration(self):
        self.configuration.subscriber_removal_url_xpath = \
            "//em[contains(concat(' ', @class, ' '), ' customer-remove ')]"

        self.newsletter_attributes.html = u'<html><body>'\
            u'<p>Follow <em class="customer-remove">remove url</em></p>'\
            u'</body></html>'

        message_html = self.newsletter.compile(self.subscriber)
        self.assertEquals(
            message_html,
            u'<html><body>'
            u'<p>Follow <em '
            u'class="customer-remove">http://example.com/removal</em></p>'
            u'</body></html>'
        )


class string_containing(object):
    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, actual):
        if isinstance(actual, string_containing):
            return self.expected == actual.expected
        return self.expected in actual


@stubydoo.assert_expectations
class TestMessageCompilation(TestNewsletterInterpolations):

    def test_compile_returns_message_from_factory(self):
        message = 'The resulting message'
        self.newsletter_attributes.html = u'The original HTML'

        stubydoo.stub(self.message_factory.__call__).\
            with_args(string_containing(u'The original HTML')).\
            and_return(message)

        self.assertEquals(self.newsletter.compile(self.subscriber),
                          'The resulting message')

    def test_inline_styles(self):
        self.configuration.inline_styles = True
        self.newsletter_attributes.html = \
            u'<style>p{color:red}</style><p>Foo</p>'
        stubydoo.expect(self.message_factory.__call__).\
            to_be_called.with_args(string_containing(
                u'<p style="color:red">Foo</p>'
            ))

        self.newsletter.compile(self.subscriber)

    def test_no_inline_styles(self):
        self.configuration.inline_styles = False
        self.newsletter_attributes.html = \
            u'<style>p{color:red}</style><p>Foo</p>'
        stubydoo.expect(self.message_factory.__call__).\
            to_be_called.with_args(string_containing(
                u'<style>p{color:red}</style></head><body><p>Foo</p>'
            ))

        self.newsletter.compile(self.subscriber)


@stubydoo.assert_expectations
class TestSetLastSent(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)

        self.context = stubydoo.double()
        self.adapted = stubydoo.double()

        # This is normally registered during application startup.
        zope.component.provideHandler(zope.component.event.objectEventNotify)

        @zope.component.adapter(None)
        @zope.interface.implementer(interfaces.INewsletterAttributes)
        def newsletter_attributes_adapter(context):
            return self.adapted
        zope.component.provideAdapter(newsletter_attributes_adapter)

    def tearDown(self):
        placelesssetup.tearDown()

    def test_set_last_sent_date(self):
        newsletter.setLastSent(self.context, stubydoo.double())
        self.assertTrue(isinstance(self.adapted.last_sent, datetime))

    def test_notify_modification(self):
        @zope.component.adapter(None, IObjectModifiedEvent)
        def handler(object, event):
            self.object = object
            self.event = event
        zope.component.provideHandler(handler)

        newsletter.setLastSent(self.context, stubydoo.double())
        self.assertTrue(self.object is self.context)
        self.assertEquals(self.event.descriptions[0].attributes,
                          ('last_sent',))
        self.assertTrue(self.event.descriptions[0].interface is
                        interfaces.INewsletterAttributes)


@stubydoo.assert_expectations
class TestGetSortableLastSent(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)

        self.context = stubydoo.double()
        self.adapted = stubydoo.double()

        @zope.component.adapter(None)
        @zope.interface.implementer(interfaces.INewsletterAttributes)
        def newsletter_attributes_adapter(obj):
            return self.adapted
        zope.component.provideAdapter(newsletter_attributes_adapter)

    def tearDown(self):
        placelesssetup.tearDown()

    def test_returns_value_set_in_adapted_object(self):
        self.adapted.last_sent = u'expected value'
        self.assertEquals(newsletter.getSortableLastSent(self.context)(),
                          u'expected value')

    def test_returns_datetime_max_if_none_in_adapted_object(self):
        self.adapted.last_sent = None
        self.assertEquals(newsletter.getSortableLastSent(self.context)(),
                          datetime.max)


@stubydoo.assert_expectations
class TestGetLastSent(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)

        self.context = stubydoo.double()
        self.adapted = stubydoo.double()

        @zope.component.adapter(None)
        @zope.interface.implementer(interfaces.INewsletterAttributes)
        def newsletter_attributes_adapter(obj):
            return self.adapted
        zope.component.provideAdapter(newsletter_attributes_adapter)

    def tearDown(self):
        placelesssetup.tearDown()

    def test_returns_value_set_in_adapted_object(self):
        self.adapted.last_sent = u'expected value'
        self.assertEquals(newsletter.getLastSent(self.context)(),
                          u'expected value')

    def test_returns_none_if_none_in_adapted_object(self):
        self.adapted.last_sent = None
        self.assertEquals(newsletter.getLastSent(self.context)(), None)
