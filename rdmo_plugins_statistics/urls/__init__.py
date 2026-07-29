from django.urls import path

from ..views import statistics

app_name = 'statistics'

urlpatterns = [
    path('', statistics, name='index'),
]
