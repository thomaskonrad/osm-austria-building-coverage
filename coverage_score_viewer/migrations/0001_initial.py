# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CoverageBoundary',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True)),
                ('admin_level', models.IntegerField()),
                ('name', models.TextField()),
                ('rank', models.IntegerField()),
                ('latest_timestamp', models.DateTimeField()),
                ('oldest_timestamp', models.DateTimeField()),
                ('coverage', models.FloatField()),
                ('original_coverage', models.FloatField()),
                ('total_coverage_gain', models.FloatField()),
                ('polygon', models.TextField()),
                ('bbox', models.TextField()),
                ('parent', models.ForeignKey(to='coverage_score_viewer.CoverageBoundary')),
            ],
            options={
                'db_table': 'coverage_boundary',
            },
            bases=(models.Model,),
        ),
    ]
