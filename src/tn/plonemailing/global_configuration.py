from five import grok
from tn.plonemailing import _
from tn.plonemailing import interfaces

class GlobalConfiguration(grok.GlobalUtility):
    grok.implements(interfaces.IConfiguration)

    subscriber_name_xpath = \
            u"//*[contains(concat(' ', @class, ' '), ' subscriber-name ')]"

    add_subscriber_preferences = False
    subscriber_preferences_url_xpath = \
            u"//a[contains(concat(' ', @class, ' '), ' subscriber-preferences ')]/@href"
    subscriber_preferences_html = u''

    add_subscriber_removal = True
    subscriber_removal_url_xpath = \
            u"//a[contains(concat(' ', @class, ' '), ' subscriber-removal ')]/@href"
    subscriber_removal_html = _(
        u'<p>To unsubscribe yourself from this mailing list access <a '
        u'href="#" class="subscriber-removal">this link</a> and confirm '
        u'your unsubscription.</p>'
    )
