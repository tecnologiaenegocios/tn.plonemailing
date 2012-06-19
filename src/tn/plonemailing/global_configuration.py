from five import grok
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces import IPloneSiteRoot
from tn.plonemailing import _
from tn.plonemailing import interfaces
from zope.component import getUtility


class Configuration(grok.GlobalUtility):
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


class ControlPanelForm(RegistryEditForm):
    schema = interfaces.IConfiguration


class ControlPanelView(ControlPanelFormWrapper, grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('cmf.ManagePortal')
    grok.name('plonemailing-controlpanel')

    label = _(u'TN Plone Mailing settings')
    form = ControlPanelForm
