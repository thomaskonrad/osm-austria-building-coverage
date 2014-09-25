from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'coverage_score_viewer.views.index', name='index'),

    url(r'^states/$', 'coverage_score_viewer.views.states', name='states'),
    url(r'^districts/$', 'coverage_score_viewer.views.districts', name='districts'),
    url(r'^municipalities/$', 'coverage_score_viewer.views.municipalities', name='municipalities'),

    url(r'^details/(?P<boundary_id>\d+)$', 'coverage_score_viewer.views.show', name='show'),
    url(r'^search$', 'coverage_score_viewer.views.search', name='search'),

    url(r'^map/$', 'map.views.map', name='map'),
)
