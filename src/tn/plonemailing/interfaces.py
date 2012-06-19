from Products.MailHost import interfaces as mailhost_interfaces
from tn.plonemailing import _

import lxml.html
import lxml.etree
import zope.container.interfaces
import zope.interface
import zope.publisher.interfaces.browser
import zope.schema
import zope.sendmail


def validate_html(value):
    if not value:
        raise zope.interface.Invalid(_(u'Cannot be empty'))
    try:
        lxml.html.fragment_fromstring(value)
    except lxml.etree.LxmlError, e:
        raise zope.interface.Invalid(unicode(e))
    return True


class ISubscriber(zope.interface.Interface):
    """A subscriber.
    """

    email  = zope.schema.TextLine(title=u'E-mail')
    format = zope.schema.TextLine(title=u'Format')
    name   = zope.schema.TextLine(title=u'Name', required=False)

    preferences_url = zope.schema.TextLine(title=u'Preferences URL',
                                           required=False)
    removal_url     = zope.schema.TextLine(title=u'Removal URL',
                                           required=False)


class ISubscriberProvider(zope.interface.Interface):
    """A subscriber provider.
    """

    def subscribers():
        """An interable or iterator of the provided subscribers.

        Each value returned or yielded must be an ISubscriber.
        """


class IPossibleSubscriberProvider(zope.interface.Interface):
    """Marker interface for objects which don't provide ISubscriberProvider
    directly, but can be adapted to it.
    """


class INewsletterHTML(zope.interface.Interface):
    """Provides a newsletter body in HTML format.
    """
    html = zope.schema.Text(title=u'Body of the newsletter')


class INewsletterAttributes(zope.interface.Interface):
    """Attributes that every newsletter should have.
    """

    author_address = zope.schema.TextLine()
    author_name    = zope.schema.TextLine(required=False)

    sender_address = zope.schema.TextLine()
    sender_name    = zope.schema.TextLine(required=False)

    reply_to_address = zope.schema.TextLine(required=False)
    reply_to_name    = zope.schema.TextLine(required=False)

    subject = zope.schema.TextLine()

    html = zope.schema.Text()


class IPossibleNewsletterAttributes(zope.interface.Interface):
    """Marker interface for objects which don't provide INewsletterAttributes
    directly, but can be adapted to it.
    """


class INewsletter(INewsletterAttributes):
    """A template for producing a newsletter content for a given subscriber.
    """

    def compile(subscriber):
        """Return an email.message.Message for the given subscriber.
        """


class IConverter(zope.interface.Interface):

    content_type = zope.schema.ASCIILine(
        title=u'Content type',
        description=u'The content type this converter emits.'
    )

    newsletter = zope.interface.Attribute('The newsletter object')

    def convert():
        """Convert the newsletter content to another format.

        Return a unicode string.
        """


class IMessageFactory(zope.interface.Interface):
    """A factory for email.message.Message.
    """

    newsletter = zope.interface.Attribute('The newsletter object')
    subscriber = zope.interface.Attribute('The subscriber object')

    def __call__(content):
        """Return a email.message.Message object with the content.
        """


class IMailHost(mailhost_interfaces.IMailHost):
    """A specialized Mail Host for this package.
    """


class IConfiguration(zope.interface.Interface):
    """Main configuration of this package.
    """

    subscriber_name_xpath = zope.schema.SourceText(
        title=_(u'Subscriber name XPath selector'),
        description=_(u'The element whose text will replaced with the name '
                      u'of the subscriber.'),
        default=u"//*[contains(concat(' ', @class, ' '), ' subscriber-name ')]",
    )

    add_subscriber_preferences = zope.schema.Bool(
        title=_(u'Add subscriber preferences link'),
        description=_(u'If a link for subscriber preferences should be '
                      u'added to the end of generated newsletters.'),
        default=False,
    )

    subscriber_preferences_url_xpath = zope.schema.SourceText(
        title=_(u'Subscriber preferences URL XPath selector'),
        description=_(u'The element whose "href" attribute will be replaced. '
                      u'The replacement happens always, no matter if '
                      u'"Add subscriber preferences link" is checked.'),
        default=u"//a[contains(concat(' ', @class, ' '), ' subscriber-preferences ')]/@href",
    )

    subscriber_preferences_html = zope.schema.SourceText(
        title=_(u'Subscriber preferences HTML'),
        description=_(u'In the absense of an element under the selector for '
                      u'the preferences URL, this HTML code, '
                      u'which must contain an element selectable through the '
                      u'selector, will be used.'),
        constraint=validate_html,
        required=False
    )

    add_subscriber_removal = zope.schema.Bool(
        title=_(u'Add subscriber removal link'),
        description=_(u'If a link for subscriber removal should be '
                      u'added to the end of generated newsletters.'),
        default=True,
    )

    subscriber_removal_url_xpath = zope.schema.SourceText(
        title=_(u'Subscriber removal URL XPath selector'),
        description=_(u'The element whose "href" attribute will be replaced. '
                      u'This replacement happens always, no matter if '
                      u'"Add subscriber removal link" is checked.'),
        default=u"//a[contains(concat(' ', @class, ' '), ' subscriber-removal ')]/@href",
    )

    subscriber_removal_html = zope.schema.SourceText(
        title=_(u'Subscriber removal HTML'),
        description=_(u'In the absense of an element under the selector for '
                      u'the removal URL, this HTML code, '
                      u'which must contain an element selectable through the '
                      u'selector, will be used.'),
        default=u'<p>To unsubscribe yourself from this mailing list access '
                u'<a href="#" class="subscriber-removal">this link</a> and '
                u'confirm your unsubscription.</p>',
        constraint=validate_html,
        required=False
    )

    @zope.interface.invariant
    def check_preferences_html(obj):
        # Sometimes attributes which are not required are not even set in the
        # received object (when using z3c.form).
        if not hasattr(obj, 'subscriber_preferences_html'):
            return
        if obj.add_subscriber_preferences and not obj.subscriber_preferences_html:
            raise zope.interface.Invalid(
                _(u'Must provide a preferences HTML if a link for this is to be added.')
            )

    @zope.interface.invariant
    def check_removal_html(obj):
        # Sometimes attributes which are not required are not even set in the
        # received object (when using z3c.form).
        if not hasattr(obj, 'subscriber_removal_html'):
            return
        if obj.add_subscriber_removal and not obj.subscriber_removal_html:
            raise zope.interface.Invalid(
                _(u'Must provide a removal HTML if a link for this is to be added.')
            )
