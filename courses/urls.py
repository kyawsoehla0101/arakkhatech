from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('register/', views.signup, name='signup'),
    path('signup/', views.signup, name='register'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Management URLs
    path('manage/courses/', views.manage_courses, name='manage_courses'),
    path('manage/courses/add/', views.add_course, name='add_course'),
    path('manage/courses/<int:pk>/edit/', views.edit_course, name='edit_course'),
    path('manage/courses/<int:pk>/delete/', views.delete_course, name='delete_course'),
    
    path('manage/lessons/', views.manage_all_lessons, name='manage_all_lessons'),
    path('manage/lessons/add/', views.add_lesson_general, name='add_lesson_general'),
    path('manage/courses/<int:course_pk>/lessons/', views.manage_lessons, name='manage_lessons'),
    path('manage/courses/<int:course_pk>/lessons/add/', views.add_lesson, name='add_lesson'),
    path('manage/lessons/<int:pk>/edit/', views.edit_lesson, name='edit_lesson'),
    path('manage/lessons/<int:pk>/delete/', views.delete_lesson, name='delete_lesson'),
    
    path('manage/students/', views.manage_students, name='manage_students'),
    path('manage/students/add/', views.add_student, name='add_student'),
    path('manage/students/<int:student_pk>/enroll/', views.enroll_student, name='enroll_student_manual'),
    path('manage/enroll/', views.enroll_student, name='enroll_student_general'),
    path('manage/enrollments/', views.manage_enrollments, name='manage_enrollments'),
    path('manage/enrollments/<int:enrollment_pk>/remove/', views.remove_enrollment, name='remove_enrollment'),
    
    path('manage/users/', views.manage_users, name='manage_users'),
    path('manage/users/add/', views.add_user, name='add_user'),
    path('manage/users/<int:user_pk>/edit/', views.edit_user, name='edit_user'),
    path('manage/users/<int:user_pk>/delete/', views.delete_user, name='delete_user'),
    
    path('admin-search/', views.admin_search, name='admin_search'),
    path('notifications/', views.all_notifications, name='all_notifications'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    
    # 404 Preview for testing
    path('404-preview/', views.preview_404, name='preview_404'),

    # Community Voice URLs
    path('community-voice/submit/', views.submit_community_voice, name='submit_community_voice'),
    path('manage/voices/', views.manage_voices, name='manage_voices'),
    path('manage/voice/<int:pk>/approve/', views.approve_voice, name='approve_voice'),
    path('manage/voice/<int:pk>/delete/', views.delete_voice, name='delete_voice'),

    path('course/<int:pk>/', views.course_detail, name='course_detail'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('course/<int:course_pk>/lesson/<int:lesson_pk>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_pk>/toggle-completion/', views.toggle_lesson_completion, name='toggle_lesson_completion'),
    path('course/<int:pk>/enroll/', views.enroll, name='enroll'),

    # Static Pages
    path('about/', views.about_us, name='about'),
    path('contact/', views.contact_us, name='contact'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]
