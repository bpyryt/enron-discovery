from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include


def healthcheck(_request):
    return HttpResponse('Enron Discovery OK')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('messages/', include('investigation.urls')),
    path('', healthcheck, name='healthcheck'),
]