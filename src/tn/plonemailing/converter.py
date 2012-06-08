from five import grok
from htmlentitydefs import entitydefs
from plone.intelligenttext.transforms import convertHtmlToWebIntelligentPlainText
from tn.plonemailing import interfaces

import lxml.html
import re

links_with_href_re = re.compile(r'(?m)<a([^<]+)href="([^<"]+)"([^<]*)>([^<]+)<\/a>',
                                re.IGNORECASE)


class HTMLConverter(grok.MultiAdapter):
    grok.adapts(None, None, interfaces.INewsletter)
    grok.implements(interfaces.IConverter)
    grok.name('html')

    content_type = 'text/html'

    def __init__(self, context, request, newsletter):
        self.context    = context
        self.request    = request
        self.newsletter = newsletter

    def convert(self, html):
        return html


class TextConverter(grok.MultiAdapter):
    grok.adapts(None, None, interfaces.INewsletter)
    grok.implements(interfaces.IConverter)
    grok.name('text')

    content_type = 'text/plain'

    def __init__(self, context, request, newsletter):
        self.context    = context
        self.request    = request
        self.newsletter = newsletter

    def convert(self, html):
        html = lxml.html.document_fromstring(html)
        body = lxml.html.tostring(html.cssselect('body')[0], encoding=unicode)
        return self._to_text(body)

    def _to_text(self, body):
        # Because plone.intelligenttext uses htmlentitydefs to convert entities
        # to text and because htmlentitydefs returns entities in latin-1, we
        # take care of entity conversion by ourselves.
        body = self._expand_entities(body)

        # Expand links to reveal their hrefs.  When link tags are stripped out
        # the user still will see the target URL.
        body = self._expand_links(body)

        return convertHtmlToWebIntelligentPlainText(body.encode('utf-8')).\
                decode('utf-8')

    def _expand_entities(self, body):
        body = body.replace('&nbsp;', ' ')
        for entity, letter in entitydefs.items():
            # Let plone.intelligenttext handle &lt; and &gt;, or else we may be
            # creating what looks like tags.
            if entity != 'lt' and entity != 'gt':
                body = body.replace('&' + entity + ';',
                                    letter.decode('latin-1'))

        return body

    def _expand_links(self, body):
        def replace(match):
            if match.group(2).strip() != match.group(4).strip():
                return '<a%shref="%s"%s>%s [%s]<\/a>' % (match.group(1),
                                                         match.group(2),
                                                         match.group(3),
                                                         match.group(4),
                                                         match.group(2))
            return match.group()
        return links_with_href_re.sub(replace, body)
