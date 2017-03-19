from django.conf.urls import url
from coverage_score_viewer.views import index, states, districts, municipalities, details, search, coverage_chart
from map.views import map

urlpatterns = [
    url(r'^$', index, name='index'),

    url(r'^states/$', states, name='states'),
    url(r'^districts/$', districts, name='districts'),
    url(r'^municipalities/$', municipalities, name='municipalities'),

    url(r'^details/(?P<boundary_id>\d+)$', details, name='details'),
    url(r'^search$', search, name='search'),

    url(r'^coverage-chart.svg', coverage_chart, name='coverage_chart'),

    url(r'^map/$', map, name='map'),
]
