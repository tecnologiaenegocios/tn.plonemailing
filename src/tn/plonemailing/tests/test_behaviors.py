# encoding: utf-8

from tn.plonemailing import behaviors
from tn.plonemailing import interfaces
from zope.app.testing import placelesssetup
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.schema.interfaces import IVocabularyTokenized

import stubydoo
import plone.app.controlpanel.mail
import unittest
import zope.annotation
import zope.interface
import zope.intid
import zope.component


class CollectionIncluding(object):
    """A matcher for collections including required values.
    """
    def __init__(self, *required_values):
        self.required_values = set(required_values)
    def __eq__(self, actual_values):
        if isinstance(actual_values, CollectionIncluding):
            return self.required_values == actual_values.required_values
        return set(actual_values).issuperset(self.required_values)


class IntIds(object):
    zope.interface.implements(zope.intid.interfaces.IIntIds)
    def getId(self, obj):
        return hash(obj)


intids = IntIds()


@stubydoo.assert_expectations
class TestPossibleLists(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)
        zope.component.provideUtility(intids)

        self.catalog = stubydoo.double(__call__=lambda x:None)
        self.context = stubydoo.double(portal_catalog=self.catalog)

        self.possible_list = stubydoo.double()
        self.brain = stubydoo.double(getObject=lambda x: self.possible_list,
                                     Title=u'the title')

        stubydoo.stub(self.catalog.__call__).with_args(
            object_provides=CollectionIncluding(
                interfaces.ISubscriberProvider.__identifier__,
                interfaces.IPossibleSubscriberProvider.__identifier__
            )
        ).and_return([self.brain])

        behaviors.possibleSubscriberProviders(self.context)

    def tearDown(self):
        placelesssetup.tearDown()

    def test_vocabulary_is_returned(self):
        vocabulary = behaviors.possibleSubscriberProviders(self.context)
        self.assertTrue(IVocabularyTokenized.providedBy(vocabulary))

    def test_vocabulary_term_has_titles(self):
        vocabulary = behaviors.possibleSubscriberProviders(self.context)
        term = vocabulary.getTermByToken(str(hash(self.possible_list)))
        self.assertTrue(ITitledTokenizedTerm.providedBy(term))

    def test_vocabulary_term_values_are_the_actual_objects(self):
        vocabulary = behaviors.possibleSubscriberProviders(self.context)
        term = vocabulary.getTermByToken(str(hash(self.possible_list)))
        self.assertTrue(term.value is self.possible_list)

    def test_terms_with_titles_as_utf8_byte_strings(self):
        self.brain.Title = 'UTF-8 string á'
        vocabulary = behaviors.possibleSubscriberProviders(self.context)
        term = vocabulary.getTermByToken(str(hash(self.possible_list)))

        self.assertTrue(term.title == self.brain.Title.decode('utf-8'))

    def test_terms_with_titles_as_unicode_strings(self):
        self.brain.Title = u'á'
        vocabulary = behaviors.possibleSubscriberProviders(self.context)
        term = vocabulary.getTermByToken(str(hash(self.possible_list)))

        self.assertTrue(term.title == self.brain.Title)


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

    for attr in ('author_address',   'author_name',
                 'sender_address',   'sender_name',
                 'reply_to_address', 'reply_to_name',
                 'subject'):
        a, b = make_test(attr)
        locals()['test_%s_initially_empty' % attr] = a
        locals()['test_%s_is_persisted' % attr] = b
        del a, b
    del make_test


    def test_subscriber_providers_is_empty(self):
        self.assertEquals(self.adapted.subscriber_providers, [])

    def test_subscriber_providers_is_persisted(self):
        self.adapted.subscriber_providers = 'the value'
        new_adapted = behaviors.NewsletterFromContent(self.context)
        self.assertEquals(new_adapted.subscriber_providers, 'the value')

    def test_subscriber_providers_is_saved_in_an_attribute(self):
        self.adapted.subscriber_providers = 'the value'
        self.assertEquals(
            self.context._newsletter_from_content_subscriber_providers,
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
        self.context.portal_url = stubydoo.double(getPortalObject=lambda x:portal)

        zope.interface.alsoProvides(portal,
                                    plone.app.controlpanel.mail.IMailSchema)

        self.behavior = stubydoo.double()

        @zope.component.adapter(None)
        @zope.interface.implementer(behaviors.INewsletterFromContent)
        def newsletter_from_content(context):
            return self.behavior
        zope.component.provideAdapter(newsletter_from_content)

        self.adapted = behaviors.NewsletterAttributes(self.context)

    def tearDown(self):
        placelesssetup.tearDown()

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
        self.behavior.subject = None
        self.context.title = u'The content title'
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


@stubydoo.assert_expectations
class TestMarkerHasRelations(unittest.TestCase):
    def runTest(self):
        from z3c.relationfield.interfaces import IHasRelations
        self.assertTrue(IHasRelations in
                        behaviors.INewsletterFromContentMarker.__iro__)
