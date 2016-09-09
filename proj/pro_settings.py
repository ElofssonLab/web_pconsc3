"""
Django settings for proj project in production

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

try:
    from shared_settings import *
except ImportError:
    pass

with open('/etc/django_pro_secret_key.txt') as f:
    SECRET_KEY = f.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['localhost', 'pconsc3.bioinfo.se', 'c3.pcons.net', '*.pcons.net', 'dev.pconsc3.bioinfo.se']

computenodefile = "%s/pred/static/computenode.txt"%(BASE_DIR)
if os.path.exists(computenodefile):
    nodelist = []
    try:
        nodelist = open(computenodefile, "r").read().split()
    except:
        pass
    ALLOWED_HOSTS += nodelist


