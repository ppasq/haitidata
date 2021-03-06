from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from osgeo_importer.urls import urlpatterns as importer_urlpatterns

from geonode.urls import *

from filter.urls import api_ext
from thumbnail.views import layer_thumbnail

urlpatterns = patterns('',
   url(r'^/?$',
       TemplateView.as_view(template_name='site_index.html'),
       name='home'),
    url(r'', include(api_ext.urls)),
    url(r'^layers/(?P<layername>[^/]*)/thumbnail$', layer_thumbnail, name='layer_thumbnail2'),
 ) + urlpatterns + [
    url(r'^chart/', include('charts_app.urls')),
    url(r'^table/', include('wfs_harvest.urls')),
    url(r'^clip/', include('clip-and-ship.urls')),
    url(r'^contact/$', TemplateView.as_view(template_name='contact.html'), name='contact'),
    url(r'^tutorials/$', TemplateView.as_view(template_name='tutorials.html'), name='tutorials'),
    ]

urlpatterns += patterns(
    '',
    url(r'^i18n/', include('django.conf.urls.i18n')),
)
urlpatterns += importer_urlpatterns
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
