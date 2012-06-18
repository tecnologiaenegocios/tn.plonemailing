from five import grok
from plone.registry.interfaces import IRegistry
from tn.plonemailing import interfaces
from zope.component import getUtility


class GlobalConfiguration(grok.GlobalUtility):
    grok.implements(interfaces.IConfiguration)

    @property
    def subscriber_name_xpath(self):
        return self.from_registry('subscriber_name_xpath')

    @property
    def add_subscriber_preferences(self):
        return self.from_registry('add_subscriber_preferences')

    @property
    def subscriber_preferences_url_xpath(self):
        return self.from_registry('subscriber_preferences_url_xpath')

    @property
    def subscriber_preferences_html(self):
        return self.from_registry('subscriber_preferences_html') or u''

    @property
    def add_subscriber_removal(self):
        return self.from_registry('add_subscriber_removal')

    @property
    def subscriber_removal_url_xpath(self):
        return self.from_registry('subscriber_removal_url_xpath')

    @property
    def subscriber_removal_html(self):
        return self.from_registry('subscriber_removal_html') or u''

    def from_registry(self, key):
        return getUtility(IRegistry)['tn.plonemailing.' + key]
