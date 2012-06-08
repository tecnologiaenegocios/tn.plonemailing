from five import grok
from tn.plonemailing import interfaces
from zope.component import getMultiAdapter
from zope.component import getUtility

import inspect
import lxml.html
import zope.globalrequest


@grok.adapter(interfaces.IPossibleNewsletterAttributes)
@grok.implementer(interfaces.INewsletter)
def newsletter_dispatcher(context):
    newsletter_attributes = interfaces.INewsletterAttributes(context)
    request = zope.globalrequest.getRequest()
    return getMultiAdapter((context, request, newsletter_attributes),
                           interfaces.INewsletter)


def add_attributes_from_newsletter_attributes(*property_names):
    f_locals = inspect.currentframe(1).f_locals
    def make_fn(property_name):
        return property(lambda self: getattr(
            self.newsletter_attributes, property_name
        ))
    for property_name in property_names:
        f_locals[property_name] = make_fn(property_name)


class Newsletter(grok.MultiAdapter):
    grok.adapts(None, None, interfaces.INewsletterAttributes)
    grok.implements(interfaces.INewsletter)

    add_attributes_from_newsletter_attributes(
        'author_address',   'author_name',
        'sender_address',   'sender_name',
        'reply_to_address', 'reply_to_name',
        'subject', 'html'
    )

    def __init__(self, context, request, newsletter_attributes):
        self.context = context
        self.request = request
        self.newsletter_attributes = newsletter_attributes
        self.configuration = getUtility(interfaces.IConfiguration)

    def compile(self, subscriber):
        html = self._interpolate(subscriber)
        factory = getMultiAdapter((self.context, self.request, self, subscriber),
                                  interfaces.IMessageFactory)
        return factory(html)

    def _interpolate(self, subscriber):
        html_tree = lxml.html.document_fromstring(self.html)

        self._add_subscriber_name(html_tree, subscriber)
        self._add_preferences_url(html_tree, subscriber)
        self._add_removal_url(html_tree, subscriber)

        return lxml.html.tostring(html_tree, encoding=unicode)

    def _add_subscriber_name(self, html_tree, subscriber):
        xpath = self.configuration.subscriber_name_xpath
        self._replace_xpath(html_tree, xpath, subscriber.name)

    def _add_preferences_url(self, html_tree, subscriber):
        xpath = self.configuration.subscriber_preferences_url_xpath
        content = subscriber.preferences_url
        user_html = self.configuration.subscriber_preferences_html
        add = self.configuration.add_subscriber_preferences

        self._add_with_user_html(html_tree, xpath, content, user_html, add)

    def _add_removal_url(self, html_tree, subscriber):
        xpath = self.configuration.subscriber_removal_url_xpath
        content = subscriber.removal_url
        user_html = self.configuration.subscriber_removal_html
        add = self.configuration.add_subscriber_removal

        self._add_with_user_html(html_tree, xpath, content, user_html, add)

    def _add_with_user_html(self, html_tree, xpath, content, user_html, add):
        if not content:
            return
        done = self._replace_xpath(html_tree, xpath, content)
        if not done and add:
            user_tree = lxml.html.fromstring(user_html)
            user_done = self._replace_xpath(user_tree, xpath, content)
            body = html_tree.xpath('//body')
            if user_done and body:
                body = body[0]
                body.append(user_tree)

    def _replace_xpath(self, html_tree, xpath, content):
        done = False
        if not content:
            return done

        selection = html_tree.xpath(xpath)
        for thing in selection:
            if isinstance(thing, lxml.html.HtmlElement):
                thing.text = content
                done = True
                continue
            elif isinstance(thing, str):
                if thing.is_attribute:
                    element = thing.getparent()
                    attribute_name = xpath.split('/')[-1]
                    if attribute_name.startswith('@'):
                        attribute_name = attribute_name[1:]
                        element.attrib[attribute_name] = content
                        done = True
                        continue

        return done
