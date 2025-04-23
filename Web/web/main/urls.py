from django.contrib import admin
from django.urls import include, path
from . import views
from . import lessons
from . import broadcast

urlpatterns = [
    path('', views.index),
    path('new_user', views.newUserPage),
    path('view', views.viewPage),
    path('change', views.changePage),
    path('add', views.addPage),
    path('delete', views.deletePage),
    path('test', views.testPage),
    path('lessons', lessons.lessonsPage),
    path('broadcast', broadcast.broadcastPage),
]
