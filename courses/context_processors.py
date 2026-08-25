from .models import Notification
from .helpers import is_admin as _is_admin, is_instructor as _is_instructor

def notifications(request):
    if request.user.is_authenticated:
        # Student/Public Notifications
        unread_count = Notification.objects.filter(user=request.user, is_read=False, is_admin_notification=False).count()
        latest = Notification.objects.filter(user=request.user, is_admin_notification=False).order_by('-created_at')[:5]
        
        # Admin Notifications
        unread_admin_count = 0
        latest_admin = []
        if _is_admin(request.user):
            unread_admin_count = Notification.objects.filter(user=request.user, is_read=False, is_admin_notification=True).count()
            latest_admin = Notification.objects.filter(user=request.user, is_admin_notification=True).order_by('-created_at')[:5]
            
        return {
            'unread_notifications_count': unread_count,
            'latest_notifications': latest,
            'unread_admin_notifications_count': unread_admin_count,
            'latest_admin_notifications': latest_admin
        }
    return {
        'unread_notifications_count': 0,
        'latest_notifications': [],
        'unread_admin_notifications_count': 0,
        'latest_admin_notifications': []
    }

def user_roles(request):
    if request.user.is_authenticated:
        return {
            'is_admin_user': _is_admin(request.user),
            'is_instructor_user': _is_instructor(request.user),
            'user_role_label': (request.user.profile.role if hasattr(request.user, 'profile') else 'student')
        }
    return {
        'is_admin_user': False,
        'is_instructor_user': False,
        'user_role_label': 'guest'
    }
