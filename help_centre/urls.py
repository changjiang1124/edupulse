from django.urls import path

from . import views

app_name = 'help_centre'

urlpatterns = [
    path('', views.HelpCentreIndexView.as_view(), name='index'),
    path('<slug:slug>/', views.HelpArticleView.as_view(), name='article'),
]
