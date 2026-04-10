from django.urls import path
from . import views

app_name = 'academics'

urlpatterns = [
    # Course Group URLs
    path('course-groups/', views.CourseGroupListView.as_view(), name='course_group_list'),
    path('course-groups/add/', views.CourseGroupCreateView.as_view(), name='course_group_add'),
    path('course-groups/<int:pk>/', views.CourseGroupDetailView.as_view(), name='course_group_detail'),
    path('course-groups/<int:pk>/edit/', views.CourseGroupUpdateView.as_view(), name='course_group_edit'),
    path('course-groups/<int:pk>/delete/', views.CourseGroupDeleteView.as_view(), name='course_group_delete'),
    path('course-groups/<slug:slug>/public/', views.CourseGroupPublicDetailView.as_view(), name='course_group_public_detail'),

    # Course URLs
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_add'),
    path('course-groups/<int:group_pk>/courses/add/', views.CourseCreateView.as_view(), name='course_add_from_group'),
    path('courses/bulk-duplicate/', views.BulkCourseDuplicateView.as_view(), name='course_bulk_duplicate'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('courses/<int:pk>/regenerate-classes/', views.CourseRegenerateClassesView.as_view(), name='course_regenerate_classes'),
    path('courses/<int:pk>/duplicate/', views.CourseDuplicateView.as_view(), name='course_duplicate'),
    path('courses/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('courses/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('courses/<int:pk>/archive/', views.CourseArchiveView.as_view(), name='course_archive'),
    path('courses/<int:pk>/restore/', views.CourseRestoreView.as_view(), name='course_restore'),
    
    # Class URLs
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassCreateView.as_view(), name='class_add'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    path('classes/<int:pk>/edit/', views.ClassUpdateView.as_view(), name='class_edit'),
    path('classes/<int:pk>/delete/', views.ClassDeleteView.as_view(), name='class_delete'),
    path('classes/<int:pk>/add-students/', views.class_add_students, name='class_add_students'),
    path('classes/<int:pk>/makeup-candidates/', views.class_makeup_candidates, name='class_makeup_candidates'),
    path('classes/<int:pk>/schedule-makeup/', views.class_schedule_makeup, name='class_schedule_makeup'),
    path('classes/<int:pk>/makeup-status/', views.class_update_makeup_status, name='class_update_makeup_status'),
]
