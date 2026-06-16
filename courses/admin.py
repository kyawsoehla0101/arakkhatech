from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Course, Lesson, Enrollment, Profile, CommunityVoice, Notification, NewsletterSubscriber

# Inline admin for Profile
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('role', 'avatar', 'bio')

# Extend UserAdmin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('instructor',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    ordering = ('course', 'order')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'date_enrolled')
    list_filter = ('course', 'student')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'avatar')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')

@admin.register(CommunityVoice)
class CommunityVoiceAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('user__username', 'content')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'is_admin_notification', 'created_at')
    list_filter = ('is_read', 'is_admin_notification', 'created_at')
    search_fields = ('user__username', 'title', 'message')

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
