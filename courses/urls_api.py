from django.urls import path, include
from docs.views_api import BookViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .views_api import (
    CourseViewSet, LessonViewSet, EnrollmentViewSet,
    NotificationViewSet, CommunityVoiceViewSet,
    ProfileViewSet, UserViewSet, NewsletterSubscriberViewSet
)
from .api_google_auth import GoogleAuthAPIView, CurrentUserAPIView


class APIRootView(APIView):
    """Arakkha Tech API Root - အသုံးပြုနိုင်သော API endpoints အားလုံးကို တစ်နေရာတည်းမှာ ပြသသည်"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, format=None):
        return Response({
            'name': 'Arakkha Tech Platform API',
            'version': 'v1',
            'authentication': {
                'jwt_token_obtain': {
                    'method': 'POST',
                    'url': reverse('token_obtain_pair', request=request, format=format),
                    'body': {'username': 'string', 'password': 'string'},
                    'description': 'Username/Password ဖြင့် JWT Access + Refresh Token ရယူရန်'
                },
                'jwt_token_refresh': {
                    'method': 'POST',
                    'url': reverse('token_refresh', request=request, format=format),
                    'body': {'refresh': 'string'},
                    'description': 'Access Token သက်တမ်းကုန်ချိန်တွင် Refresh Token ဖြင့် အသစ်ထုတ်ယူရန်'
                },
                'google_login': {
                    'method': 'POST',
                    'url': reverse('google_auth_api', request=request, format=format),
                    'body': {
                        'id_token': 'string (Firebase GoogleSignIn.idToken)',
                        'access_token': 'string (optional)'
                    },
                    'description': 'Flutter/Firebase GoogleSignIn မှ ရရှိသော ID Token ကို Verify လုပ်ပြီး JWT Access + Refresh Token ပြန်ပေးရန်'
                },
                'current_user': {
                    'method': 'GET',
                    'url': reverse('current_user_api', request=request, format=format),
                    'auth_required': True,
                    'description': 'Login ဝင်ထားသူ့ရဲ့ အချက်အလက် + Role ကို ပြန်ပေးရန်'
                }
            },
            'resources': {
                'users': {
                    'list': reverse('user-list', request=request, format=format),
                    'admin_actions': {
                        'register_user': 'POST /users/register/ (Public - Student အသစ်ဖွင့်)',
                        'change_password': 'POST /users/change_password/',
                        'me': 'GET /users/me/',
                        'change_role': 'POST /users/{id}/change_role/ (Admin)',
                        'deactivate': 'POST /users/{id}/deactivate/ (Admin)',
                        'activate': 'POST /users/{id}/activate/ (Admin)'
                    }
                },
                'courses': reverse('course-list', request=request, format=format),
                'lessons': reverse('lesson-list', request=request, format=format),
                'enrollments': {
                    'list': reverse('enrollment-list', request=request, format=format),
                    'instructor_actions': {
                        'enroll_student': 'POST /enrollments/enroll_user/ (Instructor/Admin: username_or_email + course_id ဖြင့် enroll)',
                        'manage_enrollments': 'GET /enrollments/manage/'
                    },
                    'student_actions': {
                        'complete_lesson': 'POST /enrollments/{id}/complete_lesson/'
                    }
                },
                'books': reverse('book-list', request=request, format=format),
                'notifications': reverse('notification-list', request=request, format=format),
                'community_voices': reverse('communityvoice-list', request=request, format=format),
                'profiles': reverse('profile-list', request=request, format=format),
                'newsletter_subscribers': reverse('newsletter-list', request=request, format=format)
            },
            'notes': [
                'Protected endpoints များအားလုံးတွင် Authorization Header တွင် Bearer <access_token> ထည့်ပို့ပါ။',
                'Token သက်တမ်းကုန်လျှင် auth/token/refresh/ endpoint သို့ refresh token ဖြင့် POST လုပ်ပါ။',
                'Google Login အတွက် Flutter မှ Firebase GoogleSignIn အရင်လုပ်ပြီး ရလာတဲ့ idToken ကို auth/google/ သို့ POST လုပ်ပါ။'
            ]
        })


router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'books', BookViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'community-voices', CommunityVoiceViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'users', UserViewSet)
router.register(r'newsletter', NewsletterSubscriberViewSet, basename='newsletter')

urlpatterns = [
    path('', APIRootView.as_view(), name='api_root'),
    path('', include(router.urls)),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/google/', GoogleAuthAPIView.as_view(), name='google_auth_api'),
    path('auth/me/', CurrentUserAPIView.as_view(), name='current_user_api'),
]
