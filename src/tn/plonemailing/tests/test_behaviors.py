from Products.CMFCore.utils import getToolByName
from tn.plonemailing import behaviors
from tn.plonemailing import interfaces
from zope.app.testing import placelesssetup

import datetime
import stubydoo
import plone.app.controlpanel.mail
import unittest
import zope.annotation
import zope.interface
import zope.intid
import zope.component


class IntIds(object):
    zope.interface.implements(zope.intid.interfaces.IIntIds)

    def getId(self, obj):
        return hash(obj)


intids = IntIds()


@stubydoo.assert_expectations
class TestNewsletterFromContent(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)

        self.context = stubydoo.double()

        # The persistency of NewsletterFromContent attributes is done in an
        # annotation.
        self.annotations = {}

        @zope.component.adapter(None)
        @zope.interface.implementer(zope.annotation.interfaces.IAnnotations)
        def context_annotations(obj):
            return self.annotations
        zope.component.provideAdapter(context_annotations)

        self.adapted = behaviors.NewsletterFromContent(self.context)

    def tearDown(self):
        placelesssetup.tearDown()

    def test_provides_behavior_interface(self):
        self.assertTrue(
            behaviors.INewsletterFromContent.providedBy(self.adapted)
        )

    def test_subscribers(self):
        double = stubydoo.double
        stub = stubydoo.stub

        sub1, sub2, sub3, sub4 = double(), double(), double(), double()
        obj1 = double()
        obj2 = double()

        obj1_sub_provider = double(subscribers=[sub1, sub2])
        obj2_sub_provider = double(subscribers=[sub3, sub4])

        stub(obj1, '__conform__').with_args(interfaces.ISubscriberProvider).\
            and_return(obj1_sub_provider)
        stub(obj2, '__conform__').with_args(interfaces.ISubscriberProvider).\
            and_return(obj2_sub_provider)

        obj1_rel = double(to_object=obj1)
        obj2_rel = double(to_object=obj2)

        self.adapted.possible_subscriber_providers = [obj1_rel, obj2_rel]

        self.assertEquals(set(self.adapted.subscribers),
                          set((sub1, sub2, sub3, sub4)))

    # The confusing code below will generate a test to prove that initially
    # these attributes are empty, and that they are stored in an annotation.

    def make_test(attr):
        def test_value_empty(self):
            self.assertTrue(getattr(self.adapted, attr) is None)

        def test_value_persistency(self):
            setattr(self.adapted, attr, 'the value')
            new_adapted = behaviors.NewsletterFromContent(self.context)
            self.assertEquals(getattr(new_adapted, attr), 'the value')

        return (test_value_empty, test_value_persistency)

    for attr in ('author_address', 'author_name',
                 'sender_address', 'sender_name',
                 'reply_to_address', 'reply_to_name',
                 'subject'):
        a, b = make_test(attr)
        locals()['test_%s_initially_empty' % attr] = a
        locals()['test_%s_is_persisted' % attr] = b
        del a, b
    del make_test

    def test_possible_subscriber_providers_is_empty(self):
        self.assertEquals(self.adapted.possible_subscriber_providers, [])

    def test_possible_subscriber_providers_is_persisted(self):
        self.adapted.possible_subscriber_providers = 'the value'
        new_adapted = behaviors.NewsletterFromContent(self.context)
        self.assertEquals(new_adapted.possible_subscriber_providers,
                          'the value')

    def test_possible_subscriber_providers_is_saved_in_an_attribute(self):
        self.adapted.possible_subscriber_providers = 'the value'
        self.assertEquals(
            self.context.
            _newsletter_from_content_possible_subscriber_providers,
            'the value'
        )


@stubydoo.assert_expectations
class TestNewsletterAttributesAdapter(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)
        zope.component.provideUtility(intids)

        portal = stubydoo.double(
            email_from_address="the site's email address",
            email_from_name="the site's name"
        )

        self.context = stubydoo.double()
        self.context.portal_url = stubydoo.double(
            getPortalObject=lambda x: portal
        )

        zope.interface.alsoProvides(portal,
                                    plone.app.controlpanel.mail.IMailSchema)

        self.behavior = stubydoo.double()

        @zope.component.adapter(None)
        @zope.interface.implementer(behaviors.INewsletterFromContent)
        def newsletter_from_content(context):
            return self.behavior
        zope.component.provideAdapter(newsletter_from_content)

        @zope.component.adapter(None)
        @zope.interface.implementer(zope.annotation.interfaces.IAnnotations)
        def annotations_adapter(context):
            annotations = getattr(context, '_annotations', None)
            if annotations is None:
                context._annotations = dict()
            return context._annotations
        zope.component.provideAdapter(annotations_adapter)

        self.adapted = behaviors.NewsletterAttributes(self.context)

        self.original_getToolByName_code = getToolByName.func_code
        getToolByName_stup = lambda context, name: getattr(context, name)
        getToolByName.func_code = getToolByName_stup.func_code

    def tearDown(self):
        placelesssetup.tearDown()
        getToolByName.func_code = self.original_getToolByName_code

    def test_resulting_object_formally_provides_newsletter_attributes(self):
        self.assertTrue(
            interfaces.INewsletterAttributes.providedBy(self.adapted)
        )

    # Author address

    def test_author_address_from_site_if_none_in_behavior(self):
        self.behavior.author_address = None

        self.assertEquals(self.adapted.author_address,
                          "the site's email address")

    def test_author_address_from_site_if_blank_in_behavior(self):
        self.behavior.author_address = u''

        self.assertEquals(self.adapted.author_address,
                          "the site's email address")

    def test_uses_author_address_if_set_in_behavior(self):
        self.behavior.author_address = "the author's email address"

        self.assertEquals(self.adapted.author_address,
                          "the author's email address")

    # Author name

    def test_author_name_from_site_if_none_in_behavior(self):
        self.behavior.author_name = None
        self.assertEquals(self.adapted.author_name, "the site's name")

    def test_author_name_from_site_if_blank_in_behavior(self):
        self.behavior.author_name = u''
        self.assertEquals(self.adapted.author_name, "the site's name")

    def test_uses_author_name_if_set_in_behavior(self):
        self.behavior.author_name = "the author's name"
        self.assertEquals(self.adapted.author_name, "the author's name")

    # Sender address

    def test_sender_address_from_site_if_is_none_in_behavior(self):
        self.behavior.sender_address = None
        self.behavior.author_address = None

        self.assertEquals(self.adapted.sender_address,
                          "the site's email address")

    def test_sender_address_from_site_if_is_blank_in_behavior(self):
        self.behavior.sender_address = None
        self.behavior.author_address = u''

        self.assertEquals(self.adapted.sender_address,
                          "the site's email address")

    def test_uses_sender_address_if_author_address_is_set_in_behavior(self):
        self.behavior.sender_address = None
        self.behavior.author_address = "the author's email address"

        self.assertEquals(self.adapted.sender_address,
                          "the author's email address")

    def test_uses_sender_address_if_set_in_behavior(self):
        self.behavior.sender_address = "the sender's email address"

        self.assertEquals(self.adapted.sender_address,
                          "the sender's email address")

    # Sender name

    def test_sender_name_from_site_if_is_none_in_behavior(self):
        self.behavior.sender_name = None
        self.behavior.author_name = None
        self.assertEquals(self.adapted.sender_name, "the site's name")

    def test_sender_name_from_site_if_is_blank_in_behavior(self):
        self.behavior.sender_name = None
        self.behavior.author_name = u''
        self.assertEquals(self.adapted.sender_name, "the site's name")

    def test_uses_sender_name_if_author_name_is_set_in_behavior(self):
        self.behavior.sender_name = None
        self.behavior.author_name = "the author's name"
        self.assertEquals(self.adapted.sender_name, "the author's name")

    def test_uses_sender_name_if_set_in_behavior(self):
        self.behavior.sender_name = "the sender's name"
        self.assertEquals(self.adapted.sender_name, "the sender's name")

    # Reply-To address

    def test_reply_to_address_is_none_if_not_set_in_behavior(self):
        self.behavior.reply_to_address = None
        self.assertTrue(self.adapted.reply_to_address is None)

    def test_uses_reply_to_address_if_set_in_behavior(self):
        self.behavior.reply_to_address = "the reply email address"

        self.assertEquals(self.adapted.reply_to_address,
                          "the reply email address")

    # Reply-To name

    def test_reply_to_name_is_none_if_not_set_in_behavior(self):
        self.behavior.reply_to_name = None
        self.assertTrue(self.adapted.reply_to_name is None)

    def test_uses_reply_name_if_set_in_behavior(self):
        self.behavior.reply_to_name = "the reply name"

        self.assertEquals(self.adapted.reply_to_name, "the reply name")

    # Subject

    def test_uses_content_title_if_set_to_none_in_behavior(self):
        self.context.title = u'The content title'
        self.behavior.subject = None
        self.assertEquals(self.adapted.subject, u'The content title')

    def test_uses_content_title_if_set_to_blank_in_behavior(self):
        self.context.title = u'The content title'
        self.behavior.subject = u''
        self.assertEquals(self.adapted.subject, u'The content title')

    def test_uses_subject_if_set_in_behavior(self):
        self.context.title = u'The content title'
        self.behavior.subject = u'A custom subject'
        self.assertEquals(self.adapted.subject, u'A custom subject')

    # HTML

    def test_html_is_obtained_from_adapter(self):
        @zope.component.adapter(None)
        @zope.interface.implementer(interfaces.INewsletterHTML)
        def newsletter_html(obj):
            return stubydoo.double(html=u'The HTML code')
        zope.component.provideAdapter(newsletter_html)

        self.assertEquals(self.adapted.html, u'The HTML code')

    # Last sent

    def test_last_sent_defaults_to_none(self):
        self.assertTrue(self.adapted.last_sent is None)

    def test_last_sent_can_be_directly(self):
        a_datetime = datetime.datetime.now()
        self.adapted.last_sent = a_datetime
        self.assertEquals(self.adapted.last_sent, a_datetime)

    def test_is_persisted(self):
        a_datetime = datetime.datetime.now()
        self.adapted.last_sent = a_datetime

        new_adapted = behaviors.NewsletterAttributes(self.context)
        self.assertEquals(new_adapted.last_sent, a_datetime)


@stubydoo.assert_expectations
class TestMarkerHasRelations(unittest.TestCase):
    def runTest(self):
        from z3c.relationfield.interfaces import IHasRelations
        self.assertTrue(IHasRelations in
                        behaviors.INewsletterFromContentMarker.__iro__)
