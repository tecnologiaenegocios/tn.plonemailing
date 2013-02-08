from plone.registry.interfaces import IRegistry
from tn.plonemailing import global_configuration
from tn.plonemailing.interfaces import IConfiguration
from tn.plonemailing.interfaces import validate_html
from zope.app.testing import placelesssetup

import unittest
import zope.interface
import zope.component


config_prefix = IConfiguration.__identifier__ + '.'


class TestConfiguration(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)
        self.registry = dict()
        zope.component.provideUtility(self.registry, provides=IRegistry)
        self.configuration = global_configuration.Configuration()

    def tearDown(self):
        placelesssetup.tearDown()

    def test_subscriber_name_xpath_is_fetched_from_registry(self):
        self.registry[config_prefix + 'subscriber_name_xpath'] = u'//foo'
        self.assertEquals(self.configuration.subscriber_name_xpath,
                          u'//foo')

    def test_add_subscriber_prefs_is_fetched_from_registry(self):
        self.registry[config_prefix + 'add_subscriber_preferences'] = True
        self.assertTrue(self.configuration.add_subscriber_preferences)
        self.registry[config_prefix + 'add_subscriber_preferences'] = False
        self.assertFalse(self.configuration.add_subscriber_preferences)

    def test_subscriber_prefs_url_xpath_is_fetched_from_registry(self):
        self.registry[config_prefix + 'subscriber_preferences_url_xpath'] = \
            u'//foo'
        self.assertEquals(self.configuration.subscriber_preferences_url_xpath,
                          u'//foo')

    def test_subscriber_prefs_html_is_fetched_from_registry(self):
        self.registry[config_prefix + 'subscriber_preferences_html'] = \
            u'<p>Foo</p>'
        self.assertEquals(self.configuration.subscriber_preferences_html,
                          u'<p>Foo</p>')

    def test_subscriber_prefs_html_is_blank_if_none_in_registry(self):
        self.registry[config_prefix + 'subscriber_preferences_html'] = None
        self.assertEquals(self.configuration.subscriber_preferences_html, u'')

    def test_add_subscriber_removal_is_fetched_from_registry(self):
        self.registry[config_prefix + 'add_subscriber_removal'] = True
        self.assertTrue(self.configuration.add_subscriber_removal)
        self.registry[config_prefix + 'add_subscriber_removal'] = False
        self.assertFalse(self.configuration.add_subscriber_removal)

    def test_subscriber_removal_url_xpath_is_fetched_from_registry(self):
        self.registry[config_prefix + 'subscriber_removal_url_xpath'] = \
            u'//foo'
        self.assertEquals(self.configuration.subscriber_removal_url_xpath,
                          u'//foo')

    def test_subscriber_removal_html_is_fetched_from_registry(self):
        self.registry[config_prefix + 'subscriber_removal_html'] = \
            u'<p>Foo</p>'
        self.assertEquals(self.configuration.subscriber_removal_html,
                          u'<p>Foo</p>')

    def test_subscriber_removal_html_is_blank_if_none_in_registry(self):
        self.registry[config_prefix + 'subscriber_removal_html'] = None
        self.assertEquals(self.configuration.subscriber_removal_html, u'')

    def test_inline_styles_is_fetched_from_registry(self):
        self.registry[config_prefix + 'inline_styles'] = True
        self.assertTrue(self.configuration.inline_styles)
        self.registry[config_prefix + 'inline_styles'] = False
        self.assertFalse(self.configuration.inline_styles)


class TestConfigurationHTMLValidation(unittest.TestCase):

    def test_good_html_works_fine(self):
        self.assertTrue(validate_html(u'<p></p>') is True)

    def test_complains_with_empty_html(self):
        self.assertRaises(
            zope.interface.Invalid,
            validate_html,
            u''
        )

    def test_complains_with_multiple_elements_html(self):
        self.assertRaises(
            zope.interface.Invalid,
            validate_html,
            u'<p></p><p></p>'
        )


class TestGet(unittest.TestCase):

    def test_get(self):
        placelesssetup.setUp(self)
        configuration = object()
        zope.component.provideUtility(configuration, provides=IConfiguration)

        self.assertTrue(global_configuration.get() is configuration)

        placelesssetup.tearDown()
