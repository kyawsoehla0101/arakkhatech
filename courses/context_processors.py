from .models import Notification, ContactMessage, Course
from .helpers import is_admin as _is_admin, is_instructor as _is_instructor

def notifications(request):
    try:
        if request.user.is_authenticated:
            unread_count = Notification.objects.filter(user=request.user, is_read=False, is_admin_notification=False).count()
            latest = Notification.objects.filter(user=request.user, is_admin_notification=False).order_by('-created_at')[:5]

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
    except Exception:
        pass
    return {
        'unread_notifications_count': 0,
        'latest_notifications': [],
        'unread_admin_notifications_count': 0,
        'latest_admin_notifications': []
    }

def user_roles(request):
    try:
        if request.user.is_authenticated:
            is_admin = _is_admin(request.user)
            is_instructor = _is_instructor(request.user)
            unread_contacts = 0
            if is_admin or is_instructor:
                try:
                    unread_contacts = ContactMessage.objects.filter(is_read=False).count()
                except Exception:
                    unread_contacts = 0
            return {
                'is_admin_user': is_admin,
                'is_instructor_user': is_instructor,
                'user_role_label': (request.user.profile.role if hasattr(request.user, 'profile') else 'student'),
                'unread_contact_messages_count': unread_contacts,
            }
    except Exception:
        pass
    return {
        'is_admin_user': False,
        'is_instructor_user': False,
        'user_role_label': 'guest',
        'unread_contact_messages_count': 0,
    }

def navbar_active(request):
    try:
        nav = 'home'
        sub = ''
        drop = ''

        try:
            url_name = request.resolver_match.url_name
        except Exception:
            url_name = ''

        path = request.path or ''

        if url_name in {'courses_page', 'course_detail', 'course_detail_pk_redirect'}:
            nav = 'courses'
        elif url_name == 'course_list':
            nav = 'home'
        elif url_name in {'instructors_list', 'instructor_detail'}:
            nav = 'instructors'
        elif url_name in {'docs_list', 'book_detail', 'chapter_detail', 'lesson_detail'}:
            nav = 'docs'
        elif url_name in {'student_dashboard', 'my_courses', 'enrollment_detail', 'course_progress'}:
            nav = 'dashboard'
            drop = 'dashboard' if url_name == 'student_dashboard' else 'mycourses'
        elif url_name in {
            'admin_dashboard', 'manage_courses', 'manage_lessons', 'manage_books',
            'manage_chapters', 'manage_enrollments', 'enroll_student',
            'manage_users', 'add_user', 'edit_user', 'delete_user', 'toggle_user_active',
            'manage_notifications', 'send_announcement', 'community_voices',
        }:
            nav = 'admin'
            if url_name in {'manage_courses', 'manage_lessons'}:
                sub = 'courses'
                drop = 'manage_courses'
            elif url_name in {'manage_books', 'manage_chapters'}:
                sub = 'books'
                drop = 'manage_books'
            elif url_name in {'manage_enrollments', 'enroll_student'}:
                sub = 'enrollments'
                drop = 'manage_enrollments'
            elif url_name in {'manage_users', 'add_user', 'edit_user', 'delete_user', 'toggle_user_active'}:
                sub = 'users'
        elif url_name in {'edit_profile'}:
            nav = 'profile'
            drop = 'profile'
        elif url_name in {'change_password'}:
            nav = 'profile'
            drop = 'password'
        elif url_name in {'all_notifications'}:
            nav = 'profile'
            drop = 'notifications'

        if nav == 'home':
            if path.startswith('/course'):
                nav = 'courses'
            elif path.startswith('/instructor'):
                nav = 'instructors'
            elif path.startswith('/docs') or path.startswith('/book') or path.startswith('/chapter'):
                nav = 'docs'
            elif path.startswith('/dashboard') or path.startswith('/my-'):
                nav = 'dashboard'
                drop = drop or 'dashboard'
            elif path.startswith('/manage') or path.startswith('/admin'):
                nav = 'admin'
            elif path.startswith('/accounts') and path != '/accounts/logout/':
                nav = 'profile'

        return {
            'active_nav': nav,
            'active_sub': sub,
            'active_drop': drop,
        }
    except Exception:
        return {
            'active_nav': 'home',
            'active_sub': '',
            'active_drop': '',
        }

def footer_latest_courses(request):
    try:
        courses = list(Course.objects.order_by('-created_at')[:4])
        return {'footer_latest_courses': courses}
    except Exception:
        return {'footer_latest_courses': []}
