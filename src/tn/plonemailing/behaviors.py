from five import grok
from persistent.dict import PersistentDict
from plone.memoize.instance import memoize
from plone.directives import form
from Products.CMFCore.interfaces import IDublinCore
from Products.CMFCore.utils import getToolByName
from tn.plonemailing import _
from tn.plonemailing import interfaces
from z3c.form.browser.orderedselect import SequenceChoiceSelectFieldWidget
from z3c.relationfield import RelationChoice
from z3c.relationfield import RelationList
from z3c.relationfield.interfaces import IHasRelations
from zope.annotation.interfaces import IAnnotations
from zope.intid.interfaces import IIntIds

import inspect
import plone.app.controlpanel
import zope.component
import zope.interface


NEWSLETTER_PROPERTIES_KEY = 'tn.plonemailing.newsletter-properties'

@grok.provider(zope.schema.interfaces.IContextSourceBinder)
def possibleSubscriberProviders(context):
    terms        = []
    term_factory = zope.schema.vocabulary.SimpleVocabulary.createTerm
    identifiers  = [interfaces.IPossibleSubscriberProvider.__identifier__,
                    interfaces.ISubscriberProvider.__identifier__]
    catalog      = getToolByName(context, 'portal_catalog')
    intids       = zope.component.getUtility(IIntIds)
    for item in catalog(object_provides=identifiers):
        obj = item.getObject()
        obj_id = intids.getId(obj)
        title = item.Title if isinstance(item.Title, unicode) \
                else item.Title.decode('utf-8')
        terms.append(term_factory(obj, obj_id, title))
    return zope.schema.vocabulary.SimpleVocabulary(terms)

def SequenceSelectFieldWidget(field, request):
    return SequenceChoiceSelectFieldWidget(field, field.value_type, request)


base_newsletter = interfaces.INewsletterAttributes
class INewsletterFromContent(form.Schema):
    """Transform a content into a newsletter.
    """

    form.fieldset(
        'lists',
        label=_(u'Subscriber lists'),
        fields=('newsletter_from_content_lists',),
    )

    form.widget(newsletter_from_content_lists=SequenceSelectFieldWidget)
    newsletter_from_content_lists = RelationList(
        title=_(u'Lists'),
        description=_(u'The lists to which this content should be sent.'),
        required=False,
        value_type=RelationChoice(source=possibleSubscriberProviders)
    )

    form.fieldset(
        'newsletter',
        label=_(u'Newsletter'),
        fields=('author_address',   'author_name',
                'sender_address',   'sender_name',
                'reply_to_address', 'reply_to_name',
                'subject'),
    )

    author_address = zope.schema.TextLine(
        title=_(u'Author e-mail address'),
        description=_(u'The address of the author of the newsletter.  If none '
                      u'is provided, the address of the user which is the '
                      u'author of this newsletter will be used.  If the user '
                      u'has no e-mail set in its preferences, the address '
                      u'set as the contact form\'s address will be used.'),
        required=False,
    )

    author_name = zope.schema.TextLine(
        title=_(u'Author name'),
        description=_(u'The name of the author of the newsletter.  If none is '
                      u'provided, the full name of the user which is the '
                      u'author of this newsletter will be used.  If the user '
                      u'has no full name set in its preferences, none will be '
                      u'used.  This is the name which will appear in the in '
                      u'the mailbox of the subscriber.'),
        required=False,
    )

    sender_address = zope.schema.TextLine(
        title=_(u'Sender address'),
        description=_(u'The address of the sender of the message.  This '
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
        title=_("Reply address"),
        description=_(u'The address where replies should go to.  Leave blank '
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

    html = zope.interface.Attribute("The HTML representation of the content")


zope.interface.alsoProvides(INewsletterFromContent, form.IFormFieldProvider)

apply = lambda fn: fn()

def add_annotations_property(name, get_default=lambda self: None):
    def get(self):
        return self.annotations.get(name, None) or get_default(self)
    def set(self, value):
        self.annotations[name] = value
    prop = property(get, set)
    inspect.currentframe(1).f_locals[name] = prop


class NewsletterFromContent(object):
    """Store newsletter properties in an annotation in the content object.
    """
    zope.interface.implements(INewsletterFromContent)
    zope.component.adapts(IDublinCore)

    def __init__(self, context):
        self.context = context
        self.html    = interfaces.INewsletterHTML(context).html
        portal = getToolByName(context, 'portal_url').getPortalObject()
        self.mail_settings = plone.app.controlpanel.mail.IMailSchema(portal)

    @apply
    def author_address():
        def get(self):
            return (self.annotations.get('author_address', None) or
                    self.mail_settings.email_from_address)
        def set(self, value):
            self.annotations['author_address'] = value
        return property(get, set)

    @apply
    def author_name():
        def get(self):
            return (self.annotations.get('author_name', None) or
                    self.mail_settings.email_from_name)
        def set(self, value):
            self.annotations['author_name'] = value
        return property(get, set)

    @apply
    def sender_address():
        def get(self):
            return self.annotations.get('sender_address', self.author_address)
        def set(self, value):
            self.annotations['sender_address'] = value
        return property(get, set)

    @apply
    def sender_name():
        def get(self):
            return self.annotations.get('sender_name', self.author_name)
        def set(self, value):
            self.annotations['sender_name'] = value
        return property(get, set)

    add_annotations_property('reply_to_address')
    add_annotations_property('reply_to_name')
    add_annotations_property('subject', lambda self: self.context.title)

    # 'newsletter_from_content_lists' is implemented as an attribute, in order
    # to allow cataloging by z3c.relationfield.
    @apply
    def newsletter_from_content_lists():
        def get(self):
            return self.context.newsletter_from_content_lists
        def set(self, value):
            self.context.newsletter_from_content_lists = value
        return property(get, set)

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
        behavior = INewsletterFromContent(context)
        for property_name in ('author_address',   'author_name',
                              'sender_address',   'sender_name',
                              'reply_to_address', 'reply_to_name',
                              'subject', 'html'):
            setattr(self, property_name, getattr(behavior, property_name))


class INewsletterFromContentMarker(IHasRelations,
                                   interfaces.IPossibleNewsletterAttributes):
    """Marker interface for items which can be turned into newsletters.
    """
