from rdmo.core.settings import *  # noqa: F403

INSTALLED_APPS = [
    *INSTALLED_APPS,  # noqa: F405
    'rdmo_plugins_statistics',
]

ROOT_URLCONF = 'tests.urls'

SECRET_KEY = 'rdmo-plugins-statistics-tests'

ALLOWED_HOSTS = ['testserver']

STATIC_ROOT = '/tmp/rdmo-plugins-statistics-static'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}
