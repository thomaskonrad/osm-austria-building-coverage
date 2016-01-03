from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.http import Http404
from coverage_score_viewer.models import CoverageBoundary
from coverage_score_viewer.models import CoverageScore
import pygal
from pygal.style import LightStyle
from datetime import date
import json


def index(request):
    country = CoverageBoundary.objects.filter(admin_level=0)[0]
    states = CoverageBoundary.objects.filter(admin_level=1).order_by('rank')
    top_10_districts = CoverageBoundary.objects.filter(admin_level=2).order_by('rank')[:10]

    top_10_municipalities = CoverageBoundary.objects.filter(admin_level=3).order_by('rank')[:10]
    top_10_ascending_municipalities = CoverageBoundary.objects.filter(admin_level=3).order_by('-total_coverage_gain')[:10]

    least_covered_districts = CoverageBoundary.objects.filter(admin_level=2).order_by('-rank')[:20]
    least_covered_municipalities = CoverageBoundary.objects.filter(admin_level=3).order_by('-rank')[:20]

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
    boundary_id = request.GET.get('id')
    admin_level = request.GET.get('admin_level')

    chart = pygal.DateLine(
        x_label_rotation=90,
        range=(0, 100),
        fill=True,
        style=LightStyle
    )

    today = date.today()

    if boundary_id:
        coverage_boundary = get_object_or_404(CoverageBoundary, pk=boundary_id)
        coverage_scores = CoverageScore.objects.filter(coverage_boundary_id=boundary_id).order_by('date')

        values = []

        last = len(coverage_scores) - 1
        for i, coverage_score in enumerate(coverage_scores):
            values.append((coverage_score.date, round(coverage_score.coverage, 1)))

            if i == last and coverage_score.date != today:
                values.append((today, round(coverage_score.coverage, 1)))

        if coverage_boundary.abbreviation is not None:
            chart.add(coverage_boundary.abbreviation, values)
        else:
            chart.add(coverage_boundary.name, values)
    elif admin_level:
        coverage_boundaries = CoverageBoundary.objects.filter(admin_level=admin_level).order_by('rank')[:10]

        for coverage_boundary in coverage_boundaries:
            coverage_scores = CoverageScore.objects.filter(coverage_boundary_id=coverage_boundary.id)

            values = []

            last = len(coverage_scores) - 1
            for i, coverage_score in enumerate(coverage_scores):
                values.append((coverage_score.date, round(coverage_score.coverage, 1)))

                if i == last and coverage_score.date != today:
                    values.append((today, round(coverage_score.coverage, 1)))

            if coverage_boundary.abbreviation is not None:
                chart.add(coverage_boundary.abbreviation, values)
            else:
                chart.add(coverage_boundary.name, values)


    return HttpResponse(chart.render(), content_type="image/svg+xml")
