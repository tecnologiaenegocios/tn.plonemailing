from plone.app.dexterity.behaviors.metadata import IPublication
from tn.plonemailing import subscriber
from tn.plonemailing import subscriber_list
from z3c.form.interfaces import IFormLayer
from zope.app.testing import placelesssetup

import datetime
import stubydoo
import unittest
import zope.component
import zope.container.folder
import zope.interface
import zope.publisher.browser


class Publication(object):
    zope.component.adapts(None)
    zope.interface.implements(IPublication)

    def __init__(self, context):
        self.context = context

    def _set_expires(self, value):
        self.context.expires = value

    def _get_expires(self):
        return self.context.expires

    expires = property(_get_expires, _set_expires)

    def _set_effective(self, value):
        self.context.effective = value

    def _get_effective(self):
        return self.context.effective

    effective = property(_get_effective, _set_effective)


class AddForm(object):

    def __init__(self, context):
        self.context = context
        self.request = None
        self.prefix = 'prefix.'

    def update(self):
        self.track_update(self.req_email(), self.req_format())

    def extractData(self):
        return (dict(email=self.req_email(), format=self.req_format()), None)

    def createAndAdd(self, data):
        obj = stubydoo.double(**data)
        obj.id = 'the subscriber id'
        return obj

    def track_update(self, req_email, req_format):
        pass

    def req_email(self):
        return self.request.form['prefix.widgets.title']

    def req_format(self):
        return self.request.form['prefix.widgets.format']


@stubydoo.assert_expectations
class TestSubscriberAdder(unittest.TestCase):

    def setUp(self):
        placelesssetup.setUp(self)
        self.context = zope.container.folder.Folder()
        self.request = stubydoo.double(form={})
        self.add_form = AddForm(self.context)

        self.adder = subscriber_list.SubscriberAdder(self.context,
                                                     self.request,
                                                     self.add_form)

        dates_locale = stubydoo.double()
        self.request.locale = stubydoo.double(dates=dates_locale)

        self.parsed_datetime = datetime.datetime.now()
        self.date_short_fmt = stubydoo.double(
            parse=lambda f, x: self.parsed_datetime
        )

        stubydoo.stub(dates_locale, 'getFormatter').\
                with_args('date', 'short').and_return(self.date_short_fmt)
        stubydoo.stub(dates_locale, 'getFormatter').\
                with_args('date', 'medium').\
                and_return(stubydoo.double(parse='ignored'))
        stubydoo.stub(dates_locale, 'getFormatter').\
                with_args('dateTime', 'short').\
                and_return(stubydoo.double(parse='ignored'))
        stubydoo.stub(dates_locale, 'getFormatter').\
                with_args('dateTime', 'medium').\
                and_return(stubydoo.double(parse='ignored'))

        zope.component.provideAdapter(Publication)

    def tearDown(self):
        placelesssetup.tearDown()

    def test_add_should_set_a_request_in_form(self):
        self.adder.add('email', 'format', None, None)
        self.assertTrue(self.adder.add_form.request is not None)
        self.assertTrue(IFormLayer.providedBy(self.adder.add_form.request))

    def test_add_should_update_form_after_setting_values_in_request(self):
        stubydoo.expect(self.add_form.track_update).\
                with_args('email', 'format')
        self.adder.add('email', 'format', None, None)

    def test_add_should_not_left_values_in_request(self):
        self.adder.add('email', 'format', None, None)
        self.assertTrue(self.request.form.get('prefix.widgets.title') is None)
        self.assertTrue(self.request.form.get('prefix.widgets.format') is None)

    def test_add_returns_error_messages_from_form(self):
        def fn():
            return (dict(email='email', format='format'),
                    [stubydoo.double(error=RuntimeError('foo')),
                     stubydoo.double(error=RuntimeError('bar'))])
        stubydoo.stub(self.add_form.extractData).and_run(fn)

        errors = self.adder.add('email', 'format', None, None)
        self.assertEquals(errors, 'foo, bar')

    def test_add_adds_subscriber_with_form_data(self):
        obj = stubydoo.double()
        obj.id = 'the subscriber id'

        stubydoo.stub(self.add_form.extractData).\
                and_return(('the data', None))
        stubydoo.expect(self.add_form.createAndAdd).\
                with_args('the data').and_return(obj)

        self.adder.add('email', 'format', None, None)

    def test_add_should_set_subscriber_activation_date(self):
        obj = stubydoo.double()
        obj.id = 'the subscriber id'

        stubydoo.stub(self.add_form.extractData).\
                and_return(('the data', None))
        stubydoo.stub(self.add_form.createAndAdd).\
                with_args('the data').and_return(obj)

        self.adder.add('email', 'format', 'activation', None)

        self.assertEquals(subscriber.getSubscriberActivation(obj),
                          self.parsed_datetime)

    def test_add_should_set_subscriber_deactivation_date(self):
        obj = stubydoo.double()
        obj.id = 'the subscriber id'

        stubydoo.stub(self.add_form.extractData).\
                and_return(('the data', None))
        stubydoo.stub(self.add_form.createAndAdd).\
                with_args('the data').and_return(obj)

        self.adder.add('email', 'format', None, 'deactivation')

        self.assertEquals(subscriber.getSubscriberDeactivation(obj),
                          self.parsed_datetime)
