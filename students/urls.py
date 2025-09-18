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
    path('bulk-notification/start/', views.bulk_notification_start, name='bulk_notification_start'),
    path('bulk-notification/execute/<str:task_id>/', views.bulk_notification_execute, name='bulk_notification_execute'),
    path('bulk-notification/progress/<str:task_id>/', views.bulk_notification_progress, name='bulk_notification_progress'),
    path('bulk-tag-operation/', views.bulk_tag_operation, name='bulk_tag_operation'),

    # Tag management
    path('<int:student_id>/tag-management/', views.student_tag_management, name='student_tag_management'),
    path('available-tags/', views.get_available_tags, name='get_available_tags'),
    path('search-tags/', views.search_tags, name='search_tags'),
    path('suggest-tag-name/', views.suggest_tag_name, name='suggest_tag_name'),
]