from Products.MailHost.interfaces import IMailHost
from tn.plonemailing import interfaces
from tn.plonemailing.mailhost import getMailHost
from zope.app.testing import placelesssetup

try:
    from zope.component.hooks import setSite
except ImportError:
    from zope.site.hooks import setSite

import stubydoo
import unittest
import zope.interface
import zope.component


@stubydoo.assert_expectations
class TestMailHost(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)
        self.portal = self.make_portal()
        setSite(self.portal)
        self.provide_mailhost(self.make_mailhost('MailHost'))

        self.portal['folder'] = stubydoo.double()

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
        self.assertTrue(getMailHost() is self.portal['MailHost'])

    def test_special_mailhost_marked(self):
        other_mailhost = self.make_mailhost('OtherMailHost')
        zope.interface.alsoProvides(other_mailhost, interfaces.IMailHost)

        self.assertTrue(getMailHost() is other_mailhost)
