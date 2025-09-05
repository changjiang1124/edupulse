from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # Student URLs
    path('', views.StudentListView.as_view(), name='student_list'),
    path('add/', views.StudentCreateView.as_view(), name='student_add'),
    path('<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_edit'),
    
    # Search
    path('search/', views.StudentSearchView.as_view(), name='student_search'),
    
    # Bulk operations
    path('bulk-notification/', views.bulk_notification, name='bulk_notification'),
]