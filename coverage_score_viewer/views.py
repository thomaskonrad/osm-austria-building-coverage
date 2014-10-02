from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.http import Http404
from coverage_score_viewer.models import CoverageBoundary
import pygal
from datetime import datetime, timedelta

import json


def index(request):
    country = CoverageBoundary.objects.filter(admin_level=0)[0]
    states = CoverageBoundary.objects.filter(admin_level=1).order_by('rank')
    top_10_districts = CoverageBoundary.objects.filter(admin_level=2).order_by('rank')[:10]

    top_10_municipalities = CoverageBoundary.objects.filter(admin_level=3).order_by('rank')[:10]
    top_10_ascending_municipalities = CoverageBoundary.objects.filter(admin_level=3).order_by('-total_coverage_gain')[:10]

    least_covered_districts = CoverageBoundary.objects.filter(admin_level=2).order_by('-rank')[:50]
    least_covered_municipalities = CoverageBoundary.objects.filter(admin_level=3).order_by('-rank')[:50]

    context = {
        'country': country,
        'states': states,
        'top_10_districts': top_10_districts,

        'top_10_municipalities': top_10_municipalities,
        'top_10_ascending_municipalities': top_10_ascending_municipalities,

        'least_covered_districts': least_covered_districts,
        'least_covered_municipalities': least_covered_municipalities,
    }

    return render(request, 'index.html', context)


def list(request, admin_level):
    admin_level_dict = CoverageBoundary.admin_level_dict()

    if not admin_level in admin_level_dict:
        raise Http404

    boundaries = CoverageBoundary.objects.filter(admin_level=admin_level).order_by('rank')
    context = {
        'admin_level_heading': admin_level_dict[admin_level]['plural_upper'],
        'boundaries': boundaries,
    }

    return render(request, 'list.html', context)


def details(request, boundary_id):
    coverage_boundary = get_object_or_404(CoverageBoundary, pk=boundary_id)

    return render(request, 'details.html', {
        'coverage_boundary': coverage_boundary,
        'children': CoverageBoundary.objects.filter(parent=coverage_boundary).order_by('rank')
    })


def search(request):
    query = request.GET.get('q')

    if len(query) >= 3:
        coverage_boundaries = CoverageBoundary.objects.filter(name__icontains=query).order_by('admin_level')

        data = []

        for boundary in coverage_boundaries:
            data.append({
                'id': boundary.id,
                'name': boundary.name,
                'admin_level': boundary.admin_level,
                'admin_level_string': boundary.admin_level_string()
            })

        return HttpResponse(json.dumps(data), content_type="application/json")
    else:
        raise Http404


def states(request):
    return list(request, 1)


def districts(request):
    return list(request, 2)


def municipalities(request):
    return list(request, 3)


def coverage_chart(request):
    test_chart = pygal.DateY(x_label_rotation=20)
    test_chart.add("70409", [
        (datetime(2014, 10, 1), 76.56),
        (datetime(2014, 10, 2), 77.83),
        (datetime(2014, 10, 10), 79.34),
        (datetime(2014, 11, 2), 86.83),
    ])
    test_chart.render()

    return HttpResponse(test_chart.render(), content_type="image/svg+xml")