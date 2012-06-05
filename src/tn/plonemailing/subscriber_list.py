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
import z3c.form
import zope.component
import zope.publisher


def precondition(subscriber_list, name, object):
    if subscriber.ISubscriberSchema.providedBy(object):
        subscriber.check_email_uniqueness(subscriber_list, name, object)


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
                    u"confirmation). Provide a table with columns email and "
                    u"format (\"html\" or \"text\"), in this order, without "
                    u"headers.")
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
        errors = self._import(file.data, data['encoding'])

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

    def _import(self, data, encoding):
        all_errors = []
        dialect = csv.Sniffer().sniff(data[:512])
        reader = csv.reader(StringIO(data), dialect)

        add_view = self.context.restrictedTraverse(
            '++add++tn.plonemailing.subscriber'
        )
        add_form = add_view.form_instance

        try:
            for idx, row in enumerate(reader):
                if len(row) != 2:
                    all_errors.append(dict(number=idx + 1, email='',
                                           error=_(u'Invalid line format.')))
                    continue

                email, format = row

                request = zope.publisher.browser.TestRequest()
                alsoProvides(request, z3c.form.interfaces.IFormLayer)
                request.form['form.widgets.title']  = email.decode(encoding)
                request.form['form.widgets.format'] = format.decode(encoding).lower()
                add_form.request = request
                add_form.update()

                data, errors = add_form.extractData()
                if errors:
                    messages = []
                    for view in errors:
                        messages.append(unicode(view.error))
                    all_errors.append(dict(number=idx + 1, email=email,
                                           error=u', '.join(messages)))
                    continue

                # This doesn't verify preconditions.
                obj = add_form.createAndAdd(data)

                try:
                    # Check the precondition now explicitly, since now there's
                    # an id set in the object.
                    checkObject(self.context, obj.id, obj)
                except Invalid, e:
                    all_errors.append(dict(number=idx + 1, email=email,
                                           error=unicode(e)))
                    # Precondition was not satisfied.  Remove the subscriber.
                    del self.context[obj.id]
                    continue

                self.all_failed = False

        except csv.Error:
            all_errors.append(dict(number=reader.line_num, email='',
                                   error=_(u'File is not a proper CSV.')))

        return all_errors

    def redirect_to_context(self):
        self.request.response.redirect(self.context.absolute_url())
