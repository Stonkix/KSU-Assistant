from django.contrib import admin
from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.index),
    path('view', views.viewPage),
    path('change', views.changePage),
    path('add', views.addPage),
    path('delete', views.deletePage),
    path('test', views.testPage),
]
