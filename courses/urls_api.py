from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views_api import (
    CourseViewSet, LessonViewSet, EnrollmentViewSet,
    NotificationViewSet, CommunityVoiceViewSet,
    ProfileViewSet, UserViewSet, NewsletterSubscriberViewSet
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'community-voices', CommunityVoiceViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'users', UserViewSet)
router.register(r'newsletter', NewsletterSubscriberViewSet, basename='newsletter')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
