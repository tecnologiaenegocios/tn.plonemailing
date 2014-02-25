from five import grok
from plone.batching import Batch
from plone.batching.browser import BatchView
from plone.memoize import instance
from Products.ATContentTypes.interfaces import IATFolder
from Products.CMFPlone.utils import pretty_title_or_id
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from tn.plonemailing.interfaces import IBrowserLayer
from tn.plonemailing.interfaces import IPossibleNewsletterAttributes
from zope.component import getMultiAdapter
from zope.i18n import translate
from ZTUtils import make_query

import plone.api


class TableBatchView(BatchView):
    def make_link(self, pagenumber):
        batchlinkparams = self.request.form.copy()
        if 'nolayout' in batchlinkparams:
            del batchlinkparams['nolayout']
        return '%s?%s' % (self.request.ACTUAL_URL,
                          make_query(batchlinkparams,
                                     {'pagenumber': pagenumber}))


class View(grok.View):
    grok.context(IATFolder)
    grok.layer(IBrowserLayer)
    grok.name('newsletter-listing')
    grok.require('zope2.View')

    def update(self):
        self.pagesize = int(self.request.get('pagesize', 20))
        self.pagenumber = int(self.request.get('pagenumber', 1))
        self.show_all = self.request.get('show_all', '').lower() == 'true'
        self.sort_on = self.request.get('sort_on', 'sortable_last_sent')
        self.sort_order = self.request.get('sort_order', 'descending')

    def render(self):
        if self.request.get('nolayout', '').lower() == 'true':
            return self.render_table()
        return self.render_full()

    render_table = ViewPageTemplateFile('newsletterlistingtable.pt')
    render_full = ViewPageTemplateFile('newsletterlisting.pt')

    @property
    def title(self):
        return pretty_title_or_id(context=self.context, obj=self.context)

    @property
    def url(self):
        return self.context.absolute_url() + '/' + self.__name__

    @property
    def show_all_url(self):
        return self.url + '?show_all=true'

    @property
    @instance.memoize
    def batch(self):
        pagesize = self.pagesize
        if self.show_all:
            pagesize = len(self.get_items())
        return Batch.fromPagenumber(self.get_items(), pagesize=pagesize,
                                    pagenumber=self.pagenumber)

    @property
    def batching(self):
        return TableBatchView(self.context, self.request)(self.batch)

    @property
    def within_batch_size(self):
        return len(self.get_items()) <= self.pagesize

    @instance.memoize
    def get_items(self):
        search = plone.api.portal.get_tool('portal_catalog').__call__

        plone_utils = plone.api.portal.get_tool('plone_utils')
        get_icon = getMultiAdapter((self.context, self.request),
                                   name=u'plone_layout').getIcon
        _localize_time = getMultiAdapter((self.context, self.request),
                                         name=u'plone').toLocalizedTime
        _get_state_title = plone.api.portal.get_tool('portal_workflow').\
            getTitleForStateOnType
        portal_types = plone.api.portal.get_tool('portal_types')
        normalize = plone_utils.normalizeString

        query = dict(
            object_provides=IPossibleNewsletterAttributes.__identifier__,
            path='/'.join(self.context.getPhysicalPath()),
            sort_on=self.sort_on,
            sort_order=self.sort_order,
        )

        def get_state_title(item):
            return _get_state_title(item.review_state, item.portal_type)

        def localize_time(time, **kw):
            if time:
                return _localize_time(time, **kw)

        def get_type_title_msgid(obj):
            fti = portal_types.get(obj.portal_type)
            if fti is not None:
                return fti.Title()
            return obj.portal_type

        return [
            dict(
                url=item.getURL(),
                href_title=u'%s: %s' % (
                    translate(get_type_title_msgid(item),
                              context=self.request),
                    safe_unicode(item.Description)
                ),
                title=safe_unicode(pretty_title_or_id(plone_utils, item)),
                issuing_date=localize_time(item.last_sent, long_format=True),
                icon=get_icon(item),
                type_class='contenttype-' + normalize(item.portal_type),
                state_title=get_state_title(item),
                state_class='state-' + normalize(item.review_state),
                table_row_class='even' if (i + 1) % 2 == 0 else 'odd',
            )
            for i, item in enumerate(search(query))
        ]
