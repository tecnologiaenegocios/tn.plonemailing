from email import message
from email import utils
from five import grok
from tn.plonemailing import interfaces
from zope.component import getMultiAdapter

import email.header
import os
import quopri
import random
import re
import time


class BaseMessageFactory(object):
    def __init__(self, context, request, newsletter, subscriber):
        self.context    = context
        self.request    = request
        self.newsletter = newsletter
        self.subscriber = subscriber

    def __call__(self, content):
        msg = build_message_root(self.newsletter, self.subscriber)
        self._configure_message(msg, content)
        add_message_id(msg)
        return msg


class TextMessageFactory(grok.MultiAdapter, BaseMessageFactory):
    grok.adapts(None, None, interfaces.INewsletter, interfaces.ISubscriber)
    grok.implements(interfaces.IMessageFactory)
    grok.name(u'text')

    def _configure_message(self, message, content):
        configure_text_message(self.context,
                               self.request,
                               self.newsletter,
                               message,
                               content)


class MultipartMessageFactory(grok.MultiAdapter, BaseMessageFactory):
    grok.adapts(None, None, interfaces.INewsletter, interfaces.ISubscriber)
    grok.implements(interfaces.IMessageFactory)
    grok.name(u'__multipart__')

    def _configure_message(self, message, content):
        configure_multipart_message(self.context,
                                    self.request,
                                    self.newsletter,
                                    self.subscriber,
                                    message,
                                    content)


@grok.adapter(None, None, interfaces.INewsletter, interfaces.ISubscriber,
              name=u'html')
@grok.implementer(interfaces.IMessageFactory)
def HTMLMessageFactory(context, request, newsletter, subscriber):
    return getMultiAdapter(
        (context, request, newsletter, subscriber),
        interfaces.IMessageFactory,
        name=u'__multipart__'
    )


def build_message_root(newsletter, subscriber):
    msg = message.Message()
    add_address_header(msg, 'From',
                       newsletter.author_name,
                       newsletter.author_address)
    msg['To']   = utils.formataddr((subscriber.name, subscriber.email))
    msg['Date'] = utils.formatdate()

    if newsletter.subject:
        msg['Subject'] = email.header.make_header(
            [(newsletter.subject, 'utf-8')], header_name='Subject'
        )

    if subscriber.removal_url:
        msg['List-Unsubscribe'] = '<%s>' % subscriber.removal_url

    msg['Mime-Version'] = '1.0'

    if (newsletter.reply_to_address and
            newsletter.reply_to_address != newsletter.author_address):
        add_address_header(msg, 'Reply-To',
                           newsletter.reply_to_name,
                           newsletter.reply_to_address)

    if (newsletter.sender_address and
            newsletter.sender_address != newsletter.author_address):
        add_address_header(msg, 'Sender',
                           newsletter.sender_name,
                           newsletter.sender_address)

    return msg


def configure_multipart_message(context,
                                request,
                                newsletter,
                                subscriber,
                                message_root,
                                content):
    message_root['Content-Type'] = 'multipart/alternative'
    message_root['Content-Transfer-Encoding'] = '7bit'
    text_part = make_part(context, request, newsletter, content,
                          format=u'text')
    extended_part = make_part(context, request, newsletter, content,
                              format=subscriber.format)
    message_root.attach(text_part)
    message_root.attach(extended_part)


def configure_text_message(context, request, newsletter, msg, content):
    conversion = getMultiAdapter((context, request, newsletter),
                                 interfaces.IContentConversion, name=u'text')
    set_part_payload(msg, conversion.content_type, conversion.apply(content))


def make_part(context, request, newsletter, content, format):
    conversion = getMultiAdapter((context, request, newsletter),
                                 interfaces.IContentConversion, name=format)
    part = message.Message()
    set_part_payload(part, conversion.content_type, conversion.apply(content))
    part['Content-Disposition'] = 'inline'
    return part


def set_part_payload(part, content_type, content):
    part.add_header('Content-Type', content_type, charset='utf-8')
    part['Content-Transfer-Encoding'] = 'quoted-printable'
    part.set_payload(quopri.encodestring(content.encode('utf-8')))


def add_address_header(part, header_name, name, address):
    parts = []
    if name:
        parts.append((name, 'utf-8'))
    parts.append(("<%s>" % address, 'ascii'))
    part[header_name] = unicode(
        email.header.make_header(parts, header_name=header_name)
    )


domain_re = re.compile(r'.*@([^@]+)$')


def add_message_id(message):
    randmax = 0x7fffffff
    sender_address = extract_sender(message)
    domain = domain_re.search(sender_address).group(1)
    message['Message-Id'] = "<%s.%d.%d@%s>" % (time.strftime('%Y%m%d%H%M%S'),
                                               os.getpid(),
                                               random.randrange(0, randmax),
                                               domain)


def extract_sender(message):
    addresses = []

    if message['Sender']:
        addresses.extend(extract_addresses(message['Sender']))
    if message['From']:
        addresses.extend(extract_addresses(message['From']))

    if not addresses:
        raise ValueError('No valid sender found in message.')

    return addresses[0]


def extract_addresses(header):
    if isinstance(header, email.header.Header):
        header = unicode(header)
    parts = [part.strip() for part in unicode(header).split(',')]
    return [addr for name, addr in utils.getaddresses(parts)]
