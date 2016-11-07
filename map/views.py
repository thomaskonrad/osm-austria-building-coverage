from django.shortcuts import render
from coverage_score_viewer.models import CoverageBoundary
import json

def map(request):
    polygon = None
    bbox = None
    boundary_id = request.GET.get('boundary_id', None)

    if boundary_id:
        boundary = CoverageBoundary.objects.get(pk=boundary_id)
        polygon = boundary.polygon
        bbox_json = json.loads(boundary.bbox)
        bbox = "[[%f,%f],[%f,%f]]" % (
            bbox_json['coordinates'][0][2][1],
            bbox_json['coordinates'][0][0][0],

            bbox_json['coordinates'][0][0][1],
            bbox_json['coordinates'][0][2][0],
        )
        a = 1

    root_boundary = CoverageBoundary.objects.get(pk=0)

    context = {
        'coverage_boundary': boundary,
        'disable_scroll_whell_zoom': request.GET.get('disable_scroll_whell_zoom', False),
        'polygon': polygon,
        'bbox': bbox,
        'oldest_timestamp': root_boundary.oldest_timestamp
    }

    return render(request, 'map.html', context)