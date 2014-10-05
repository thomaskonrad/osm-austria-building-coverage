from django.db import models
from django.utils.translation import ugettext as _


class CoverageBoundary(models.Model):
    id = models.IntegerField(primary_key=True)
    admin_level = models.IntegerField()
    name = models.TextField()
    rank = models.IntegerField()
    parent = models.ForeignKey("CoverageBoundary")
    latest_timestamp = models.DateTimeField()
    oldest_timestamp = models.DateTimeField()
    coverage = models.FloatField()
    original_coverage = models.FloatField()
    total_coverage_gain = models.FloatField()
    polygon = models.TextField()
    bbox = models.TextField()

    admin_levels = {
        0: {
            'singular_lower': 'country',
            'singular_upper': _('Country'),
            'plural_upper': _('Countries')
        },
        1: {
            'singular_lower': 'state',
            'singular_upper': _('State'),
            'plural_upper': _('States')
        },
        2: {
            'singular_lower': 'district',
            'singular_upper': _('District'),
            'plural_upper': _('Districts')
        },
        3: {
            'singular_lower': 'municipality',
            'singular_upper': _('Municipality'),
            'plural_upper': _('Municipalities')
        },
    }

    class Meta:
       db_table = 'coverage_boundary'

    def __str__(self):
        return self.name

    @staticmethod
    def admin_level_dict():
        return CoverageBoundary.admin_levels

    def admin_level_string(self, format='singular_upper'):
        return CoverageBoundary.admin_levels[self.admin_level][format]

    def admin_level_string_plural(self):
        return CoverageBoundary.admin_levels[self.admin_level]['plural_upper']

    def children_admin_level_string(self, format='plural_upper'):
        return CoverageBoundary.admin_levels[self.admin_level + 1][format]


class CoverageScore(models.Model):
    id = models.IntegerField(primary_key=True)
    coverage_boundary = models.ForeignKey("CoverageBoundary")
    date = models.DateField()
    coverage = models.FloatField()
