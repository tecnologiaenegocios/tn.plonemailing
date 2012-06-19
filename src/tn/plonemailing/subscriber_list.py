from cStringIO import StringIO
from five import grok
from plone.directives import form
from plone.namedfile.field import NamedFile
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage
from tn.plonemailing import _
from tn.plonemailing import interfaces
from tn.plonemailing import subscriber
from z3c.form import button
from z3c.relationfield.interfaces import IHasRelations
from zope import schema
from zope.container.constraints import checkObject
from zope.interface import alsoProvides
from zope.interface import Invalid

import csv
import datetime
import z3c.form
import zope.component
import zope.i18n.format
import zope.publisher


def precondition(subscriber_list, name, object):
    if subscriber.ISubscriberSchema.providedBy(object):
        subscriber.checkEmailUniqueness(subscriber_list, name, object)


class ISubscriberListSchema(form.Schema,
                            IHasRelations,
                            interfaces.IPossibleSubscriberProvider):

    title = schema.TextLine(title=_(u'Name'))

    description = schema.Text(
        title=_(u'A short summary'),
        required=False,
    )

    def __setitem__(name, subscriber):
        """Add a subscriber.
        """
    __setitem__.precondition = precondition


class SubscriberProvider(grok.Adapter):
    grok.context(ISubscriberListSchema)
    grok.implements(interfaces.ISubscriberProvider)

    def subscribers(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        items = catalog(
            object_provides=subscriber.ISubscriberSchema.__identifier__,
            path='/'.join(self.context.getPhysicalPath()),
            show_inactive=False
        )
        for item in items:
            yield interfaces.ISubscriber(item.getObject())


encodings = schema.vocabulary.SimpleVocabulary([
    schema.vocabulary.SimpleTerm(value=u'utf-8', title=u'UTF-8'),
    schema.vocabulary.SimpleTerm(value=u'latin-1', title=u'Latin-1'),
])


class IImportFormSchema(form.Schema):

    file = NamedFile(title=_(u'File'))

    encoding = schema.Choice(
        title=_(u'Encoding'),
        vocabulary=encodings,
        default='utf-8',
    )


class CSVImportForm(form.SchemaForm):
    grok.name('import')
    grok.context(ISubscriberListSchema)
    grok.require('cmf.ModifyPortalContent')

    schema = IImportFormSchema
    label = _(u'CSV import')
    description = _(u"Use this form to input a batch of subscribers (without "
                    u"confirmation). Provide a CSV table with columns email "
                    u"and format (\"html\" or \"text\"), in this order, "
                    u"without headers.  Optionally, you can add one more "
                    u'column to inform an deactivation date for the '
                    u'subscriber.  Also, a fourth column may be added to '
                    u'indicate an activation date.')
    ignoreContext = True
    invalid_subscribers = []
    all_failed = True

    @button.buttonAndHandler(_(u'Import'))
    def handleImport(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        file = data['file']
        importer = CSVImporter(self.context, self.request)
        errors = importer(file.data, data['encoding'])

        if errors:
            self.status = _(u'One or more subscribers could not be imported.')
            self.invalid_subscribers = errors
            return

        IStatusMessage(self.request).add(_(u'All subscribers imported.'),
                                         type=u'info')
        self.redirect_to_context()

    @button.buttonAndHandler(_(u"Cancel"))
    def handleCancel(self, action):
        self.redirect_to_context()

    def redirect_to_context(self):
        self.request.response.redirect(self.context.absolute_url())


class CSVImporter(object):

    def __init__(self, context, request, add_form=None):
        self.context = context
        self.request = request

        if not add_form:
            add_view = self.context.restrictedTraverse(
                '++add++tn.plonemailing.subscriber'
            )
            add_form = add_view.form_instance
        self.add_form = add_form


    def __call__(self, data, encoding):
        all_errors = []
        dialect = csv.Sniffer().sniff(data[:512])
        reader = csv.reader(StringIO(data), dialect)

        adder = SubscriberAdder(self.context, self.request, self.add_form)

        try:
            for idx, row in enumerate(reader):
                if not 2 <= len(row) <= 4:
                    all_errors.append(dict(number=idx + 1, email='',
                                           error=_(u'Invalid line format.')))
                    continue

                row = list(row) + (4 - len(row)) * [None]
                email, format, deactivation, activation = row
                email = email.decode(encoding)
                format = format.decode(encoding)

                error = adder.add(email, format, activation, deactivation)
                if error:
                    all_errors.append(dict(number=idx + 1, email=email,
                                           error=error))
                    continue
                self.all_failed = False

        except csv.Error:
            all_errors.append(dict(number=reader.line_num, email='',
                                   error=_(u'File is not a proper CSV.')))

        return all_errors


class SubscriberAdder(object):

    def __init__(self, context, request, add_form):
        self.context = context
        self.request = request
        self.add_form = add_form

    def add(self, email, format, activation, deactivation):
        try:
            activation = self.parse_datetime(activation)
            deactivation = self.parse_datetime(deactivation)
        except Invalid, e:
            return unicode(e)

        data, errors = self.get_add_data(email, format)
        if errors:
            messages = []
            for view in errors:
                messages.append(unicode(view.error))
            return u', '.join(messages)

        obj, error = self.add_subscriber_to_context(data)
        if error is not None:
            return error

        self.set_activation(obj, activation, deactivation)

    def parse_datetime(self, datestr):
        if not datestr:
            return None
        locale = self.request.locale

        parsers = [
            locale.dates.getFormatter('date', 'short').parse,
            locale.dates.getFormatter('date', 'medium').parse,
            locale.dates.getFormatter('dateTime', 'short').parse,
            locale.dates.getFormatter('dateTime', 'medium').parse,
        ]

        def to_datetime(date_or_datetime):
            if isinstance(date_or_datetime, datetime.datetime):
                return date_or_datetime
            date = date_or_datetime
            return datetime.datetime(date.year, date.month, date.day)

        for parser in parsers:
            try:
                return to_datetime(parser(datestr))
            except zope.i18n.format.DateTimeParseError:
                continue
        raise Invalid(_(u'Invalid date format.'))

    def get_add_data(self, email, format):
        prefix = self.add_form.prefix
        request = zope.publisher.browser.TestRequest()

        request.form[prefix + 'widgets.title']  = email
        request.form[prefix + 'widgets.format'] = format.lower()
        alsoProvides(request, z3c.form.interfaces.IFormLayer)

        self.add_form.request = request
        self.add_form.update()

        return self.add_form.extractData()

    def add_subscriber_to_context(self, data):
        # This doesn't verify preconditions.
        obj = self.add_form.createAndAdd(data)

        try:
            # Check the precondition now explicitly, since now there's
            # an id set in the object.
            checkObject(self.context, obj.id, obj)
        except Invalid, e:
            # Precondition was not satisfied.  Remove the subscriber.
            del self.context[obj.id]
            return (obj, unicode(e))

        return (obj, None)

    def set_activation(self, obj, activation, deactivation):
        if activation:
            subscriber.activateSubscriber(obj, activation,
                                          container=self.context)
        if deactivation:
            subscriber.deactivateSubscriber(obj, deactivation,
                                            container=self.context)
