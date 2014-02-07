from five import grok
from persistent.dict import PersistentDict
from plone.directives import form
from plone.memoize.instance import memoize
from plone.supermodel import model
from Products.CMFCore.interfaces import IDublinCore
from Products.CMFCore.utils import getToolByName
from tn.plonemailing import _
from tn.plonemailing import interfaces
from z3c.form.browser.orderedselect import SequenceChoiceSelectFieldWidget
from z3c.relationfield.interfaces import IHasRelations
from zope.annotation.interfaces import IAnnotations
from zope.intid.interfaces import IIntIds

import inspect
import plone.app.controlpanel
import z3c.relationfield
import zope.component
import zope.interface


NEWSLETTER_PROPERTIES_KEY = 'tn.plonemailing.newsletter-properties'


@grok.provider(zope.schema.interfaces.IContextSourceBinder)
def possiblePossibleSubscriberProviders(context):
    terms = []
    term_factory = zope.schema.vocabulary.SimpleVocabulary.createTerm
    identifier = interfaces.IPossibleSubscriberProvider.__identifier__
    catalog = getToolByName(context, 'portal_catalog')
    intids = zope.component.getUtility(IIntIds)
    for item in catalog(object_provides=identifier):
        obj = item.getObject()
        obj_id = intids.getId(obj)
        title = item.Title if isinstance(item.Title, unicode) \
            else item.Title.decode('utf-8')
        terms.append(term_factory(obj, obj_id, title))
    return zope.schema.vocabulary.SimpleVocabulary(terms)


def SequenceSelectFieldWidget(field, request):
    return SequenceChoiceSelectFieldWidget(field, field.value_type, request)


base_newsletter = interfaces.INewsletterAttributes


class INewsletterFromContent(model.Schema, interfaces.ISubscriberProvider):
    """Transform a content into a newsletter.
    """

    form.fieldset(
        'newsletter',
        label=_(u'Newsletter'),
        fields=('possible_subscriber_providers',
                'author_address', 'author_name',
                'sender_address', 'sender_name',
                'reply_to_address', 'reply_to_name',
                'subject'),
    )

    form.widget(possible_subscriber_providers=SequenceSelectFieldWidget)
    possible_subscriber_providers = z3c.relationfield.RelationList(
        title=_(u'Subscriber providers'),
        description=_(u'The subscriber providers to which this content '
                      u'should be sent.'),
        required=False,
        value_type=z3c.relationfield.RelationChoice(
            source=possiblePossibleSubscriberProviders
        )
    )

    author_address = zope.schema.TextLine(
        title=_(u'Author e-mail address'),
        description=_(u'The e-mail address of the author of the newsletter.  '
                      u'If none is provided, the address '
                      u'set as the site\'s contact form address will be '
                      u'used.'),
        required=False,
    )

    author_name = zope.schema.TextLine(
        title=_(u'Author name'),
        description=_(u'The name of the author of the newsletter.  '
                      u'This is the name which will appear in the in '
                      u'the mailbox of the subscriber.'),
        required=False,
    )

    sender_address = zope.schema.TextLine(
        title=_(u'Sender e-mail address'),
        description=_(u'The e-mail address of the sender of the newsletter.  '
                      u'This '
                      u'should match the authentication address used to send '
                      u'the newsletter (otherwise you may have delivery '
                      u'problems for some subscribers).  If none is provided, '
                      u'the "Author e-mail address" is used.'),
        required=False,
    )

    sender_name = zope.schema.TextLine(
        title=_(u'Sender name'),
        description=_(u'The name of the sender of the newsletter.  If none is '
                      u'provided, the "Author name" is used.'),
        required=False
    )

    reply_to_address = zope.schema.TextLine(
        title=_("Reply e-mail address"),
        description=_(u'The e-mail address where replies should go to.  '
                      u'Leave blank '
                      u'to not set a reply address.'),
        required=base_newsletter['reply_to_address'].required,
    )

    reply_to_name = zope.schema.TextLine(
        title=_("Reply person name"),
        description=_(u'The name of the person whom replies should go to.'),
        required=base_newsletter['reply_to_name'].required,
    )

    subject = zope.schema.TextLine(
        title=_(u'Subject'),
        description=_(u'The subject of the newsletter.  If none is provided '
                      u'the title of the content is used.'),
        required=False,
    )


zope.interface.alsoProvides(INewsletterFromContent, form.IFormFieldProvider)

apply = lambda fn: fn()


def add_annotations_properties(*names):
    def generate_property(name):
        def get(self):
            return self.annotations.get(name)

        def set(self, value):
            self.annotations[name] = value
        return property(get, set)
    for name in names:
        inspect.currentframe(1).f_locals[name] = generate_property(name)


class NewsletterFromContent(object):
    """Store newsletter properties in an annotation in the content object.
    """
    zope.component.adapts(IDublinCore)
    zope.interface.implements(INewsletterFromContent)

    def __init__(self, context):
        self.context = context

    add_annotations_properties('author_address', 'author_name',
                               'sender_address', 'sender_name',
                               'reply_to_address', 'reply_to_name',
                               'subject')

    # 'possible_subscriber_providers' is implemented as an attribute, in order
    # to allow cataloging by z3c.relationfield.
    @apply
    def possible_subscriber_providers():
        def get(self):
            return getattr(
                self.context,
                '_newsletter_from_content_possible_subscriber_providers',
                []
            )

        def set(self, value):
            self.context.\
                _newsletter_from_content_possible_subscriber_providers = value
        return property(get, set)

    @property
    def subscribers(self):
        for possible_provider in self.possible_subscriber_providers:
            obj = possible_provider.to_object
            provider = interfaces.ISubscriberProvider(obj)
            for subscriber in provider.subscribers:
                yield subscriber

    @property
    @memoize
    def annotations(self):
        annotations = IAnnotations(self.context)
        values = annotations.get(NEWSLETTER_PROPERTIES_KEY, None)
        if values is None:
            values = annotations[NEWSLETTER_PROPERTIES_KEY] = PersistentDict()
        return values


class NewsletterAttributes(grok.Adapter):
    grok.context(interfaces.IPossibleNewsletterAttributes)
    grok.implements(interfaces.INewsletterAttributes)

    def __init__(self, context):
        self.context = context

    @property
    def author_address(self):
        return (self.behavior().author_address or
                self.mail_settings().email_from_address)

    @property
    def author_name(self):
        return (self.behavior().author_name or
                self.mail_settings().email_from_name)

    @property
    def sender_address(self):
        return self.behavior().sender_address or self.author_address

    @property
    def sender_name(self):
        return self.behavior().sender_name or self.author_name

    @property
    def reply_to_address(self):
        return self.behavior().reply_to_address

    @property
    def reply_to_name(self):
        return self.behavior().reply_to_name

    @property
    def subject(self):
        return self.behavior().subject or self.context.title

    @property
    @memoize
    def html(self):
        return interfaces.INewsletterHTML(self.context).html

    @apply
    def last_sent():
        def get(self):
            return self.annotations.get('last_sent')

        def set(self, value):
            self.annotations['last_sent'] = value

        return property(get, set)

    @memoize
    def mail_settings(self):
        portal = getToolByName(self.context, 'portal_url').getPortalObject()
        return plone.app.controlpanel.mail.IMailSchema(portal)

    @memoize
    def behavior(self):
        return INewsletterFromContent(self.context)

    @property
    @memoize
    def annotations(self):
        annotations = IAnnotations(self.context)
        values = annotations.get(NEWSLETTER_PROPERTIES_KEY, None)
        if values is None:
            values = annotations[NEWSLETTER_PROPERTIES_KEY] = PersistentDict()
        return values


class INewsletterFromContentMarker(IHasRelations,
                                   interfaces.IPossibleNewsletterAttributes):
    """Marker interface for items which can be turned into newsletters.
    """

    # Since z3c.relationfield will do an attribute lookup to get the relations
    # to index in its catalog, this field is declared by this interface,
    # although it being just a marker provided by the object on which the
    # behavior INewsletterFromContent is assigned, which in turn populates and
    # manages this field.
    _newsletter_from_content_possible_subscriber_providers = \
        z3c.relationfield.RelationList(
            required=False,
            value_type=z3c.relationfield.RelationChoice(
                source=possiblePossibleSubscriberProviders
            )
        )
