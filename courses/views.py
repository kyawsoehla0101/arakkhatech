from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Course, Lesson, Enrollment, Notification, CommunityVoice, NewsletterSubscriber
from .forms import CourseForm, LessonForm, StudentCreationForm, ManualEnrollmentForm, CommunityVoiceForm, ProfileForm, UserUpdateForm
from .helpers import is_admin, is_instructor, can_manage_course, can_manage_book
from django.db.models import Q, Count

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep the user logged in
            messages.success(request, "စကားဝှက်ကို အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ")
            return redirect('student_dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'courses/password_form.html', {'form': form, 'title': 'စကားဝှက်ပြောင်းရန်'})

def preview_404(request, exception=None):
    return render(request, '404.html', status=404)

def about_us(request):
    return render(request, 'courses/about_us.html')

def contact_us(request):
    if request.method == 'POST':
        # Here you could handle contact form submission if needed
        messages.success(request, "သင်၏ မက်ဆေ့ဂျ်ကို လက်ခံရရှိပါပြီ။ မကြာမီ ပြန်လည်ဆက်သွယ်ပေးပါမည်။")
        return redirect('contact')
    return render(request, 'courses/contact.html')

def privacy_policy(request):
    return render(request, 'courses/privacy_policy.html')

def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            if NewsletterSubscriber.objects.filter(email=email).exists():
                messages.info(request, "ဤ Email သည် စာရင်းသွင်းပြီးသား ဖြစ်နေပါသည်။")
            else:
                NewsletterSubscriber.objects.create(email=email)
                messages.success(request, "သတင်းလွှာအတွက် စာရင်းသွင်းမှု အောင်မြင်ပါသည်။ ကျေးဇူးတင်ပါသည်။")
        else:
            messages.error(request, "Email လိပ်စာ ထည့်သွင်းပေးရန် လိုအပ်ပါသည်။")
    
    # Redirect back to the page the user was on
    return redirect(request.META.get('HTTP_REFERER', 'course_list'))

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "ပရိုဖိုင်နှင့် အချက်အလက်များကို ပြင်ဆင်ပြီးပါပြီ")
            return redirect('student_dashboard')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile)
        
    return render(request, 'courses/profile_form.html', {
        'u_form': u_form,
        'p_form': p_form,
        'title': 'ပရိုဖိုင်ပြင်ဆင်ရန်'
    })

@login_required
def submit_community_voice(request):
    if request.method == 'POST':
        form = CommunityVoiceForm(request.POST)
        if form.is_valid():
            voice = form.save(commit=False)
            voice.user = request.user
            voice.save()
            
            # Notify Admin
            admin_users = User.objects.filter(is_superuser=True)
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    title="New Community Voice",
                    message=f"Student {request.user.username} has submitted a new community voice for approval.",
                    is_admin_notification=True
                )
            
            messages.success(request, "ကျေးဇူးတင်ပါတယ်! သင့်ရဲ့ ထင်မြင်ယူဆချက်ကို ပေးပို့ပြီးပါပြီ။ Admin က စစ်ဆေးပြီးရင် ပြသပေးသွားမှာပါ။")
            return redirect('student_dashboard')
    return redirect('student_dashboard')

@login_required
@user_passes_test(is_admin)
def manage_voices(request):
    voices = CommunityVoice.objects.all().select_related('user').order_by('-created_at')
    return render(request, 'courses/management/manage_voices.html', {'voices': voices, 'title': 'Manage Community Voices'})

@login_required
@user_passes_test(is_admin)
def approve_voice(request, pk):
    voice = get_object_or_404(CommunityVoice, pk=pk)
    voice.is_approved = True
    voice.save()
    
    # Notify User
    Notification.objects.create(
        user=voice.user,
        title="Voice Approved! ✨",
        message="Your community voice has been approved and is now visible on the landing page.",
        is_admin_notification=False
    )
    
    messages.success(request, "Community Voice ကို အတည်ပြုလိုက်ပါပြီ")
    return redirect('manage_voices')

@login_required
@user_passes_test(is_admin)
def delete_voice(request, pk):
    voice = get_object_or_404(CommunityVoice, pk=pk)
    voice.delete()
    messages.success(request, "Community Voice ကို ပယ်ဖျက်လိုက်ပါပြီ")
    return redirect('manage_voices')

@login_required
@user_passes_test(is_admin)
def admin_search(request):
    query = request.GET.get('q')
    courses = []
    lessons = []
    students = []
    
    if query:
        courses = Course.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).annotate(student_count=Count('enrolled_students'))
        
        lessons = Lesson.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).select_related('course')
        
        students = User.objects.filter(is_superuser=False).filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        ).annotate(enrollment_count=Count('enrollments'))

    return render(request, 'courses/management/admin_search_results.html', {
        'query': query,
        'courses': courses,
        'lessons': lessons,
        'students': students,
        'title': f'Search Results for "{query}"'
    })

@login_required
def mark_notifications_read(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If user is admin and coming from admin panel (referrer check or just logic)
        # For simplicity, we'll mark the notifications based on user type
        if request.user.is_superuser:
            Notification.objects.filter(user=request.user, is_read=False, is_admin_notification=True).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False, is_admin_notification=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return redirect('all_notifications')

@login_required
def all_notifications(request):
    # Admins see admin notifications, Students see student notifications
    if request.user.is_superuser:
        notifications = Notification.objects.filter(user=request.user, is_admin_notification=True)
    else:
        notifications = Notification.objects.filter(user=request.user, is_admin_notification=False)
        
    # Mark filtered as read
    notifications.filter(is_read=False).update(is_read=True)
    
    return render(request, 'courses/all_notifications.html', {
        'notifications': notifications,
        'title': 'Notifications'
    })
from django.db.models.functions import TruncMonth
import json
from django.utils import timezone
from datetime import timedelta

# Course Management Views
@login_required
@user_passes_test(is_instructor)
def manage_courses(request):
    if is_admin(request.user):
        courses = Course.objects.annotate(student_count=Count('enrolled_students')).order_by('-created_at')
    else:
        courses = Course.objects.filter(instructor=request.user).annotate(student_count=Count('enrolled_students')).order_by('-created_at')
    return render(request, 'courses/management/manage_courses.html', {'courses': courses})

@login_required
@user_passes_test(is_instructor)
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                course = form.save(commit=False)
                if not is_admin(request.user):
                    course.instructor = request.user
                course.save()
                
                messages.success(request, "သင်တန်းအသစ်ကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ")
                return redirect('manage_courses')
            except Exception as e:
                messages.error(request, f"သင်တန်းသိမ်းဆည်းရာတွင် အမှားတစ်ခုဖြစ်ပွားခဲ့ပါသည် - {str(e)}")
        else:
            print(f"Form Errors: {form.errors}") # Debug print
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Default instructor to current user in initial data
        form = CourseForm(initial={'instructor': request.user})
    return render(request, 'courses/management/course_form.html', {'form': form, 'title': 'သင်တန်းအသစ်ဖွင့်ရန်'})

@login_required
@user_passes_test(is_instructor)
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not can_manage_course(request.user, course):
        messages.error(request, "ဤသင်တန်းကို ပြင်ဆင်ခွင့်မရှိပါ။")
        return redirect('manage_courses')
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            try:
                course = form.save(commit=False)
                if not is_admin(request.user):
                    course.instructor = request.user
                course.save()
                messages.success(request, "သင်တန်းအချက်အလက်များကို ပြင်ဆင်ပြီးပါပြီ")
                return redirect('manage_courses')
            except Exception as e:
                messages.error(request, f"ပြင်ဆင်မှုသိမ်းဆည်းရာတွင် အမှားတစ်ခုဖြစ်ပွားခဲ့ပါသည် - {str(e)}")
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/management/course_form.html', {'form': form, 'title': 'သင်တန်းပြင်ဆင်ရန်'})

@login_required
@user_passes_test(is_instructor)
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not can_manage_course(request.user, course):
        messages.error(request, "ဤသင်တန်းကို ဖျက်သိမ်းခွင့်မရှိပါ။")
        return redirect('manage_courses')
    if request.method == 'POST':
        course.delete()
        messages.success(request, "သင်တန်းကို ဖျက်သိမ်းပြီးပါပြီ")
        return redirect('manage_courses')
    return render(request, 'courses/confirm_delete.html', {'item': course, 'type': 'Course'})

# Lesson Management Views
@login_required
@user_passes_test(is_instructor)
def manage_all_lessons(request):
    if is_admin(request.user):
        lessons = Lesson.objects.all().select_related('course').order_by('course', 'order')
    else:
        lessons = Lesson.objects.filter(course__instructor=request.user).select_related('course').order_by('course', 'order')
    return render(request, 'courses/management/manage_all_lessons.html', {'lessons': lessons})

@login_required
@user_passes_test(is_instructor)
def add_lesson_general(request):
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                lesson = form.save(commit=False)
                course = lesson.course
                if not can_manage_course(request.user, course):
                    messages.error(request, "ဤသင်တန်းအတွက် သင်ခန်းစာထည့်ခွင့်မရှိပါ။")
                    return redirect('manage_all_lessons')
                lesson.save()
                messages.success(request, "သင်ခန်းစာအသစ် ထည့်သွင်းပြီးပါပြီ")
                return redirect('manage_all_lessons')
            except Exception as e:
                messages.error(request, f"သိမ်းဆည်းရာတွင် အမှားတစ်ခုဖြစ်ပွားခဲ့ပါသည် - {str(e)}")
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        if is_admin(request.user):
            form = LessonForm()
        else:
            # For instructors, only show their own courses in the form
            form = LessonForm()
            form.fields['course'].queryset = Course.objects.filter(instructor=request.user)
    return render(request, 'courses/management/lesson_form.html', {'form': form, 'title': 'သင်ခန်းစာအသစ်ထည့်ရန်'})

@login_required
@user_passes_test(is_instructor)
def manage_lessons(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not can_manage_course(request.user, course):
        messages.error(request, "ဤသင်တန်းကို ကြည့်ရှုခွင့်မရှိပါ။")
        return redirect('manage_courses')
    lessons = course.lessons.all().order_by('order')
    return render(request, 'courses/management/manage_lessons.html', {'course': course, 'lessons': lessons})

@login_required
@user_passes_test(is_instructor)
def add_lesson(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    if not can_manage_course(request.user, course):
        messages.error(request, "ဤသင်တန်းအတွက် သင်ခန်းစာထည့်ခွင့်မရှိပါ။")
        return redirect('manage_courses')
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                lesson = form.save(commit=False)
                lesson.course = course
                lesson.save()
                messages.success(request, "သင်ခန်းစာအသစ် ထည့်သွင်းပြီးပါပြီ")
                return redirect('manage_lessons', course_pk=lesson.course.pk)
            except Exception as e:
                messages.error(request, f"သိမ်းဆည်းရာတွင် အမှားတစ်ခုဖြစ်ပွားခဲ့ပါသည် - {str(e)}")
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LessonForm(initial={'course': course})
            
    return render(request, 'courses/management/lesson_form.html', {'form': form, 'course': course, 'title': 'သင်ခန်းစာအသစ်ထည့်ရန်'})

@login_required
@user_passes_test(is_instructor)
def edit_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    if not can_manage_course(request.user, lesson.course):
        messages.error(request, "ဤသင်ခန်းစာကို ပြင်ဆင်ခွင့်မရှိပါ။")
        return redirect('manage_courses')
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            try:
                lesson = form.save()
                messages.success(request, "သင်ခန်းစာကို ပြင်ဆင်ပြီးပါပြီ")
                return redirect('manage_lessons', course_pk=lesson.course.pk)
            except Exception as e:
                messages.error(request, f"ပြင်ဆင်မှုသိမ်းဆည်းရာတွင် အမှားတစ်ခုဖြစ်ပွားခဲ့ပါသည် - {str(e)}")
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LessonForm(instance=lesson)
            
    return render(request, 'courses/management/lesson_form.html', {'form': form, 'course': lesson.course, 'title': 'သင်ခန်းစာပြင်ဆင်ရန်'})

@login_required
@user_passes_test(is_instructor)
def delete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    if not can_manage_course(request.user, lesson.course):
        messages.error(request, "ဤသင်ခန်းစာကို ဖျက်သိမ်းခွင့်မရှိပါ။")
        return redirect('manage_courses')
    course_pk = lesson.course.pk
    if request.method == 'POST':
        lesson.delete()
        messages.success(request, "သင်ခန်းစာကို ဖျက်သိမ်းပြီးပါပြီ")
        return redirect('manage_lessons', course_pk=course_pk)
    return render(request, 'courses/confirm_delete.html', {'item': lesson, 'type': 'Lesson'})

# Student Management View
@login_required
@user_passes_test(is_admin)
def add_student(request):
    if request.method == 'POST':
        form = StudentCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Admin notification
            Notification.objects.create(
                user=request.user,
                title="New Student Created",
                message=f"New student account for {user.username} has been created successfully.",
                is_admin_notification=True
            )
            messages.success(request, "ကျောင်းသားအသစ်အတွက် အကောင့်ကို အောင်မြင်စွာ ဖွင့်ပေးပြီးပါပြီ")
            return redirect('manage_students')
    else:
        form = StudentCreationForm()
    return render(request, 'courses/management/student_form.html', {'form': form, 'title': 'ကျောင်းသားအသစ်အတွက် အကောင့်ဖွင့်ရန်'})

@login_required
@user_passes_test(is_admin)
def enroll_student(request, student_pk=None):
    if student_pk:
        student = get_object_or_404(User, pk=student_pk)
        initial_data = {'student': student}
    else:
        initial_data = {}

    if request.method == 'POST':
        form = ManualEnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save()
            # Create notification for admin (Management notification)
            Notification.objects.create(
                user=request.user, # The admin who enrolled
                title="New Enrollment",
                message=f"Student {enrollment.student.username} has been enrolled in {enrollment.course.title}.",
                is_admin_notification=True # Set to Admin Panel
            )
            # Create notification for student (Personal notification)
            Notification.objects.create(
                user=enrollment.student,
                title="New Course Access",
                message=f"You have been given access to the course: {enrollment.course.title}.",
                is_admin_notification=False # Set to Student/Public
            )
            messages.success(request, "သင်တန်းအတွက် Access ပေးခြင်း အောင်မြင်ပါသည်")
            return redirect('manage_students')
    else:
        form = ManualEnrollmentForm(initial=initial_data)
        
    return render(request, 'courses/management/enroll_student_form.html', {'form': form, 'title': 'သင်တန်း Access ပေးရန်'})

@login_required
@user_passes_test(is_admin)
def manage_students(request):
    students = User.objects.filter(is_superuser=False).annotate(enrollment_count=Count('enrollments')).prefetch_related('enrollments', 'enrollments__course', 'enrollments__completed_lessons', 'profile')
    
    # Add average progress to each student object
    for student in students:
        enrollments = student.enrollments.all()
        if enrollments:
            total_progress = sum(e.progress_percentage for e in enrollments)
            student.average_progress = int(total_progress / len(enrollments))
        else:
            student.average_progress = 0
            
    return render(request, 'courses/management/manage_students.html', {'students': students})

# User Management Views (All Users including Admins/Instructors)
@login_required
@user_passes_test(is_admin)
def manage_users(request):
    users = User.objects.all().annotate(enrollment_count=Count('enrollments')).prefetch_related('enrollments', 'profile').order_by('-date_joined')
    
    return render(request, 'courses/management/manage_users.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        user_form = StudentCreationForm(request.POST)
        
        if user_form.is_valid():
            user = user_form.save()
            # Now update the profile (which was created by the signal)
            profile_form = ProfileForm(request.POST, request.FILES, instance=user.profile)
            if profile_form.is_valid():
                profile_form.save()
                
                # Admin notification
                Notification.objects.create(
                    user=request.user,
                    title="New User Created",
                    message=f"New account for {user.username} (Role: {user.profile.role}) has been created successfully.",
                    is_admin_notification=True
                )
                
                messages.success(request, f"User {user.username} ကို အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ")
                return redirect('manage_users')
            else:
                # If profile form is invalid, delete the created user
                user.delete()
                messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
        else:
            profile_form = ProfileForm(request.POST, request.FILES)
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        user_form = StudentCreationForm()
        profile_form = ProfileForm()
    
    return render(request, 'courses/management/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'title': 'User အသစ်ဖန်တီးရန်'
    })

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_pk):
    user = get_object_or_404(User, pk=user_pk)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            messages.success(request, f"User {user.username} ကို အောင်မြင်စွာ ပြင်ဆင်ပြီးပါပြီ")
            return redirect('manage_users')
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=user.profile)
    
    return render(request, 'courses/management/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_obj': user,
        'title': 'User ပြင်ဆင်ရန်'
    })

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_pk):
    user = get_object_or_404(User, pk=user_pk)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"User {username} ကို ဖျက်သိမ်းပြီးပါပြီ")
        return redirect('manage_users')
    
    return render(request, 'courses/confirm_delete.html', {'item': user, 'type': 'User'})

def course_list(request):
    query = request.GET.get('q')
    if query:
        courses = Course.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).distinct()
    else:
        courses = Course.objects.all()
    
    # Dynamic Community Voices
    community_voices = CommunityVoice.objects.filter(is_approved=True).select_related('user')[:6]
    
    # Static data for landing page sections
    features = [
        {'icon': 'fas fa-rocket', 'title': 'အယင်ဆုံး သင်ယူမှု', 'desc': 'စနစ်ကျသော roadmap များဖြင့် အချိန်တိုအတွင်း တတ်မြောက်စီရမည်။'},
        {'icon': 'fas fa-certificate', 'title': 'လက်မှတ်ရဟိခြင်း', 'desc': 'သင်တန်းပြီးဆုံးပါက အရည်အသွေးမီ လက်မှတ်များကို ထုတ်ပီးပါသည်။'},
        {'icon': 'fas fa-users', 'title': 'Community Support', 'desc': 'သင်တန်းသားအချင်းချင်း ဆွေးနွေးနိုင်မည့် community ဟိပါသည်။'},
    ]
    
    stats = [
        {'number': '500+', 'label': 'Active Students'},
        {'number': '20+', 'label': 'Total Courses'},
        {'number': '15+', 'label': 'Expert Instructors'},
        {'number': '98%', 'label': 'Satisfaction Rate'},
    ]
    
    testimonials = [
        {'name': 'Kyaw Zayar', 'role': 'Frontend Developer', 'text': 'အေ platform ကနိန်ပနာ လိလာရစွာ တကယ့်ကို ထိရောက်ပါတယ်။ ဗီဒီယိုတွေကလည်း ရှင်းလင်းပါတယ်။'},
        {'name': 'Hsu Myat', 'role': 'Student', 'text': 'Tailwind CSS သင်တန်းက အရမ်းကောင်းပါတယ်။ UI တွေကလည်း အရမ်းလှပါတယ်။'},
    ]
    
    faqs = [
        {'q': 'သင်တန်းတိကို ဇာပိုင်စတင်လိလာရဖို့လဲ?', 'a': 'အကောင့်အရင်ဖွင့်ပြီး သင်တန်းစာမျက်နှာမှာ Enroll နှိပ်လိုက်ကေရပါယာ။'},
        {'q': 'လက်မှတ် ရနိုင်ပါသလား?', 'a': 'ဟုတ်ပါရေ၊ သင်ခန်းစာအားလုံး ပြီးဆုံးပါက Certificate ထုတ်ပီးပါရေ။'},
    ]

    return render(request, 'courses/course_list.html', {
        'courses': courses,
        'community_voices': community_voices,
        'features': features,
        'stats': stats,
        'testimonials': testimonials,
        'faqs': faqs,
        'query': query
    })

from docs.models import Book

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    courses_count = Course.objects.count()
    students_count = User.objects.filter(is_superuser=False).count()
    enrollments_count = Enrollment.objects.count()
    books_count = Book.objects.count() # Updated model name
    
    courses = Course.objects.annotate(student_count=Count('enrolled_students')).order_by('-created_at')[:5]
    recent_enrollments = Enrollment.objects.select_related('student', 'course').prefetch_related('completed_lessons').order_by('-date_enrolled')[:5]
    
    # Chart Data: Enrollments per month for the last 6 months
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_stats = Enrollment.objects.filter(date_enrolled__gte=six_months_ago) \
        .annotate(month=TruncMonth('date_enrolled')) \
        .values('month') \
        .annotate(count=Count('id')) \
        .order_by('month')
    
    chart_labels = [stat['month'].strftime('%b') for stat in monthly_stats]
    chart_data = [stat['count'] for stat in monthly_stats]
    
    # If no data, provide defaults
    if not chart_labels:
        chart_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        chart_data = [0, 0, 0, 0, 0, 0]

    return render(request, 'courses/management/admin_dashboard.html', {
        'courses_count': courses_count,
        'students_count': students_count,
        'enrollments_count': enrollments_count,
        'books_count': books_count, # Pass to template
        'courses': courses,
        'recent_enrollments': recent_enrollments,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    })

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    is_enrolled = False
    enrollment = None
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        is_enrolled = enrollment is not None
    
    lessons = course.lessons.all()
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons': lessons,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment
    })

@login_required
def lesson_detail(request, course_pk, lesson_pk):
    course = get_object_or_404(Course, pk=course_pk)
    # Check if student is enrolled
    enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
    if not enrollment:
        messages.error(request, "သင်ခန်းစာများကို ကြည့်ရှုရန် အရင်ဆုံး သင်တန်းအပ်နှံပေးပါ")
        return redirect('course_detail', pk=course_pk)
    
    lesson = get_object_or_404(Lesson, pk=lesson_pk, course=course)
    lessons = course.lessons.all() # Get all lessons for the sidebar
    
    # Get completed lesson IDs for the current enrollment
    completed_lesson_ids = enrollment.completed_lessons.values_list('id', flat=True)
    
    # Get next and previous lessons
    next_lesson = course.lessons.filter(order__gt=lesson.order).order_by('order').first()
    prev_lesson = course.lessons.filter(order__lt=lesson.order).order_by('-order').first()
    
    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'lessons': lessons,
        'next_lesson': next_lesson,
        'prev_lesson': prev_lesson,
        'enrollment': enrollment,
        'completed_lesson_ids': completed_lesson_ids,
        'is_completed': lesson.id in completed_lesson_ids
    })

from django.http import JsonResponse

@login_required
def toggle_lesson_completion(request, lesson_pk):
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, pk=lesson_pk)
        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)
        
        if lesson in enrollment.completed_lessons.all():
            enrollment.completed_lessons.remove(lesson)
            completed = False
        else:
            enrollment.completed_lessons.add(lesson)
            completed = True
            # Check if course completed
            if enrollment.progress_percentage == 100:
                # Student notification
                Notification.objects.get_or_create(
                    user=request.user,
                    title="Course Completed! 🎉",
                    message=f"Congratulations! You have completed all lessons in {enrollment.course.title}.",
                    is_admin_notification=False
                )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'completed': completed, 'progress': enrollment.progress_percentage})
            
        return redirect('lesson_detail', course_pk=lesson.course.pk, lesson_pk=lesson.pk)
    return redirect('course_list')

@login_required
def student_dashboard(request):
    # Only show courses the student is enrolled in with optimized queries
    enrollments = Enrollment.objects.filter(student=request.user) \
        .select_related('course') \
        .prefetch_related('course__lessons', 'completed_lessons')
    
    # Statistics for the student
    total_courses = enrollments.count()
    
    return render(request, 'courses/student_dashboard.html', {
        'enrollments': enrollments,
        'total_courses': total_courses,
        'voice_form': CommunityVoiceForm()
    })

@login_required
def enroll(request, pk):
    # Only admin can use this view to enroll students (or if we want to keep it simple, 
    # just disable self-enrollment by checking if user is admin)
    if not request.user.is_superuser:
        messages.error(request, "သင်တန်းအပ်နှံရန် Admin ကို ဆက်သွယ်ပေးပါ။")
        return redirect('course_detail', pk=pk)
        
    course = get_object_or_404(Course, pk=pk)
    # For admin, we might want to enroll a specific student, but this view is simple.
    # Let's keep it as is but restricted, or better yet, the user wants admin-only enrollment.
    enrollment, created = Enrollment.objects.get_or_create(student=request.user, course=course)
    if created:
        # Student notification
        Notification.objects.create(
            user=request.user,
            title="Course Enrolled",
            message=f"You have successfully enrolled in {course.title}.",
            is_admin_notification=False
        )
        messages.success(request, f"{course.title} သင်တန်းကို အောင်မြင်စွာ အပ်နှံပြီးပါပြီ")
    else:
        messages.info(request, "သင်သည် ဤသင်တန်းကို အပ်နှံပြီးသားဖြစ်သည်")
    return redirect('course_detail', pk=pk)
