from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        # Student/Public Notifications
        unread_count = Notification.objects.filter(user=request.user, is_read=False, is_admin_notification=False).count()
        latest = Notification.objects.filter(user=request.user, is_admin_notification=False).order_by('-created_at')[:5]
        
        # Admin Notifications
        unread_admin_count = 0
        latest_admin = []
        if request.user.is_superuser:
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
