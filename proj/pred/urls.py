from django.conf.urls import url

#import modules for spyne (wsdl interface)
from spyne.protocol.soap import Soap11
from spyne.server.django import DjangoView

#import modules for authentication
from django.contrib.auth.decorators import login_required

from proj.pred import views

urlpatterns = [
    url(r'^$', views.index, name='pred.index'),
    url(r'^submit-seq/$', views.submit_seq, name='pred.submit_seq'),
    url(r'^thanks/$', views.thanks, name='pred.thanks'),
    url(r'^queue/$', views.get_queue, name='pred.get_queue'),
    url(r'^running/$', views.get_running, name='pred.get_running'),
    url(r'^finished/$', views.get_finished_job, name='pred.get_finished_job'),
    url(r'^failed/$', views.get_failed_job, name='pred.get_failed_job'),
    url(r'^download/$', views.download, name='pred.download'),
    url(r'^privacy/$', views.privacy, name='pred.privacy'),
    url(r'^help-wsdl-api/$', views.help_wsdl_api, name='pred.help_wsdl_api'),
    url(r'^help/$', views.get_help, name='pred.get_help'),
    url(r'^news/$', views.get_news, name='pred.get_news'),
    url(r'^serverstatus/$', views.get_serverstatus, name='pred.get_serverstatus'),
    url(r'^reference/$', views.get_reference, name='pred.get_reference'),
    url(r'^example/$', views.get_example, name='pred.get_example'),
    url(r'^oldserver/$', views.oldserver, name='pred.oldserver'),
    url(r'^result/(?P<jobid>[^\/]+)/$', views.get_results, name='pred.get_results'),
    url(r'^result/(?P<jobid>[^\/]+)/(?P<seqindex>seq_[0-9]+)/$',
        views.get_results_eachseq, name='pred.get_results_eachseq'),
    url(r'^login/', login_required(views.login), name="pred.login"),

# for spyne wsdl
    url(r'^api_submitseq/', DjangoView.as_view(application=views.app_submitseq)),

]


