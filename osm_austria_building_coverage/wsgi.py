"""
WSGI config for osm_austria_building_coverage project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/
"""

import os
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osm_austria_building_coverage.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
