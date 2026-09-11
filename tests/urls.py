from django.urls import include, path

from rdmo.core.views import home

urlpatterns = [
    path('', home, name='home'),
    path('', include('rdmo.core.urls')),
    path('api/v1/', include('rdmo_plugins_statistics.urls.v1')),
    path('statistics/', include('rdmo_plugins_statistics.urls')),
]
