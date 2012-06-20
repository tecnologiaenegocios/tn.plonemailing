from tn.plonemailing.tests import base


class TestInstallation(base.TestCase):

    def afterSetUp(self):
        self.catalog = self.portal.portal_catalog
        self.atcttool = self.portal.portal_atct

    def test_last_sent_index_addded(self):
        self.assertTrue('last_sent' in self.catalog.indexes())

    def test_last_sent_index_addded_to_topics(self):
        self.assertTrue('last_sent' in self.atcttool.topic_indexes)

    def test_last_sent_metadata_column_added(self):
        self.assertTrue('last_sent' in self.catalog.schema())

    def test_last_sent_metadata_column_addded_to_topics(self):
        self.assertTrue('last_sent' in self.atcttool.topic_metadata)
