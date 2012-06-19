from five import grok
from plone.directives import form
from plone.app.dexterity.behaviors import metadata
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage
from tn.plonemailing import _
from tn.plonemailing import interfaces
from z3c.form import button
from z3c.form import util
from z3c.form import validator
from z3c.form.interfaces import IValidator
from zope import schema
from zope.event import notify
from zope.interface import Interface, Invalid
from zope.lifecycleevent import Attributes, ObjectModifiedEvent
try:
    from zope.component.hooks import getSite
except ImportError:
    from zope.site.hooks import getSite

import datetime
import re


is_email_re = re.compile(r'^[A-Z0-9._%+-]+@(?:[A-Z0-9-]+\.)+[A-Z]{2,4}$',
                         re.IGNORECASE)
def is_email(value):
    if is_email_re.match(value):
        return True
    raise Invalid(u'E-mail address is not valid.')

formats = schema.vocabulary.SimpleVocabulary([
    schema.vocabulary.SimpleTerm(value=u'html', title=_(u'HTML')),
    schema.vocabulary.SimpleTerm(value=u'text', title=_(u'Text')),
])


class ISubscriberSchema(form.Schema):

    title = schema.TextLine(title=_(u'E-mail'), constraint=is_email)
    format = schema.Choice(title=_(u'Format'), vocabulary=formats)


class EmailValidator(validator.SimpleFieldValidator, grok.MultiAdapter):
    grok.adapts(Interface, Interface, Interface,
                util.getSpecification(ISubscriberSchema['title']), Interface)
    grok.provides(IValidator)

    def validate(self, value):
        super(EmailValidator, self).validate(value)
        subscriber = type('subscriber', (object,), dict(title=value))

        if ISubscriberSchema.providedBy(self.context):
            container = self.context.__parent__
            checkEmailUniqueness(container, self.context.__name__, subscriber)
            return

        checkEmailUniqueness(self.context, None, subscriber)


def checkEmailUniqueness(container, name, subscriber):
    email = subscriber.title
    portal = getSite()
    path = '/'.join(container.getPhysicalPath())
    catalog = getToolByName(portal, 'portal_catalog')
    items = catalog(object_provides=ISubscriberSchema.__identifier__,
                    path=path,
                    Title=email)

    if not items:
        return

    if name and len(items) == 1 and items[0].getId == name:
        return

    raise Invalid(_(u'E-mail address is not unique in this folder.'))


def activateSubscriber(subscriber, time=None, container=None):
    time = time or datetime.datetime.now()
    publication = metadata.IPublication(subscriber)
    publication.effective = time
    notify_modified(subscriber, container,
                    (metadata.IPublication, 'effective'))

def getSubscriberActivation(subscriber):
    publication = metadata.IPublication(subscriber)
    return publication.effective

def deactivateSubscriber(subscriber, time=None, container=None):
    time = time or datetime.datetime.now()
    publication = metadata.IPublication(subscriber)
    publication.expires = time
    notify_modified(subscriber, container,
                    (metadata.IPublication, 'expires'))

def getSubscriberDeactivation(subscriber):
    publication = metadata.IPublication(subscriber)
    return publication.expires

def notify_modified(subscriber, container=None, *interfaces_attributes):
    descriptions = [Attributes(params[0], *params[1:])
                    for params in interfaces_attributes]
    # Some people may call stuff like .restrictedTraverse('@@some-view') in the
    # subscriber object in an event hander, so wrap it in its container in
    # order to make it provide .REQUEST through acquisition (otherwise
    # .restrictedTraverse('@@some-view') will fail).  Of course we can do this
    # only if we know the container on which this subscriber is being added.
    if container is not None:
        subscriber = subscriber.__of__(container)
    event = ObjectModifiedEvent(subscriber, *descriptions)
    notify(event)


class SubscriberAdapter(grok.Adapter):
    grok.context(ISubscriberSchema)
    grok.implements(interfaces.ISubscriber)

    @property
    def name(self):
        return None

    @property
    def email(self):
        return self.context.title

    @property
    def format(self):
        return self.context.format

    @property
    def preferences_url(self):
        return None

    @property
    def removal_url(self):
        return self.context.absolute_url() + '/@@deactivate'


class Activate(form.SchemaForm):
    grok.context(ISubscriberSchema)
    grok.require('zope2.View')

    schema = Interface
    ignoreContext = True

    @property
    def label(self):
        return _(u'activate_subscriber_title_message',
                 default=u'Subscription confirmation for ${email}',
                 mapping=dict(email=self.context.title))

    @property
    def description(self):
        return _(u'activate_subscriber_description_message',
                 default=u'Please confirm subscription in ${list_title} list.',
                 mapping=dict(list_title=self.context.__parent__.title))

    def update(self):
        self.request.set('disable_border', True)
        return super(Activate, self).update()

    @button.buttonAndHandler(_(u'Activate'))
    def handleActivate(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        activateSubscriber(self.context)

        IStatusMessage(self.request).add(_(
            u'subscription_confirmed',
            default=_(u'Subscription of ${email} has been confirmed.'),
            mapping=dict(email=self.context.title)
        ))
        self.request.response.redirect(getSite().absolute_url())


class Deactivate(form.SchemaForm):
    grok.context(ISubscriberSchema)
    grok.require('zope2.View')

    schema = Interface
    ignoreContext = True

    @property
    def label(self):
        return _(u'deactivate_subscriber_title_message',
                 default=u'Removal confirmation for ${email}',
                 mapping=dict(email=self.context.title))

    @property
    def description(self):
        return _(u'deactivate_subscriber_description_message',
                 default=u'Please confirm removal from ${list_title} list.',
                 mapping=dict(list_title=self.context.__parent__.title))

    def update(self):
        self.request.set('disable_border', True)
        return super(Deactivate, self).update()

    @button.buttonAndHandler(_(u'Deactivate'))
    def handleDeactivate(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        deactivateSubscriber(self.context)

        IStatusMessage(self.request).add(_(
            u'subscription_removal_confirmed',
            default=_(u'Removal of ${email} from list ${list} has been confirmed.'),
            mapping=dict(email=self.context.title,
                         list=self.context.__parent__.title)
        ))
        self.request.response.redirect(getSite().absolute_url())
