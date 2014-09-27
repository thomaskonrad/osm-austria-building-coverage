from django.db import models


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
            'singular_upper': 'Country',
            'plural_upper': 'Countries'
        },
        1: {
            'singular_lower': 'state',
            'singular_upper': 'State',
            'plural_upper': 'States'
        },
        2: {
            'singular_lower': 'district',
            'singular_upper': 'District',
            'plural_upper': 'Districts'
        },
        3: {
            'singular_lower': 'municipality',
            'singular_upper': 'Municipality',
            'plural_upper': 'Municipalities'
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

    def children_admin_level_string(self, format='plural_upper'):
        return CoverageBoundary.admin_levels[self.admin_level + 1][format]
