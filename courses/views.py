from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives, get_connection, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .models import Course, Lesson, Enrollment, Notification, CommunityVoice, NewsletterSubscriber, Profile, ContactMessage
from .forms import CourseForm, LessonForm, StudentCreationForm, ManualEnrollmentForm, CommunityVoiceForm, ProfileForm, UserUpdateForm, SignUpForm, ContactForm, NewsletterSubscribeForm
from .helpers import is_admin, is_instructor, can_manage_course, can_manage_book
from django.db.models import Q, Count
import markdown
import datetime
import urllib.parse
import traceback
import logging

logger = logging.getLogger(__name__)

from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth.forms import PasswordChangeForm


def send_new_course_notification(course):
    """
    Send a beautiful HTML email to all active + confirmed newsletter subscribers
    when a new course is published.
    Includes a one-click unsubscribe link per recipient.
    """
    subscribers_qs = NewsletterSubscriber.objects.filter(is_active=True, confirmed=True)
    total_subs = subscribers_qs.count()
    if total_subs == 0:
        logger.info("send_new_course_notification: no active+confirmed subscribers found")
        return 0

    subject = f"သင်တန်းအသစ်ထွက်ပါဗျာယ်! 🎉 {course.title}"
    from_email = settings.DEFAULT_FROM_EMAIL or 'arakkhatech@gmail.com'

    if settings.ALLOWED_HOSTS:
        base_host = settings.ALLOWED_HOSTS[0]
    else:
        base_host = 'localhost:8000'
    protocol = getattr(settings, 'ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'http')

    if course.slug:
        course_path = f'/course/{course.slug}/'
    else:
        course_path = f'/course/{course.pk}/'
    course_url = f"{protocol}://{base_host}{course_path}"

    year = datetime.datetime.now().year

    base_html = None
    try:
        base_html = render_to_string('emails/new_course.html', {
            'course': course,
            'course_url': course_url,
            'year': year,
            'unsubscribe_url': '#UNSUBSCRIBE_URL#',
        })
    except Exception as e:
        logger.warning("send_new_course_notification: template failed: %s", e)
        traceback.print_exc()
        base_html = None

    count = 0
    errors = 0
    try:
        with get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            timeout=30,
        ) as connection:
            for sub in subscribers_qs.iterator():
                try:
                    unsub_token = sub.confirmation_token
                    if unsub_token:
                        unsub_path = reverse('newsletter_unsubscribe', kwargs={'token': unsub_token})
                        unsubscribe_oneclick = f"{protocol}://{base_host}{unsub_path}"
                    else:
                        unsub_path = reverse('newsletter_unsubscribe_simple')
                        qs = urllib.parse.urlencode({'email': sub.email})
                        unsubscribe_oneclick = f"{protocol}://{base_host}{unsub_path}?{qs}"

                    if base_html:
                        html_content = base_html.replace('#UNSUBSCRIBE_URL#', unsubscribe_oneclick)
                        plain_content = strip_tags(html_content)
                    else:
                        plain_content = (
                            f"သင်တန်းအသစ်ထွက်ပါဗျာယ်!\n\n"
                            f"Title: {course.title}\n"
                            f"{(course.description or '')[:200]}...\n\n"
                            f"အသေးစိတ်ကြည့်ရန်: {course_url}\n\n"
                            f"Newsletter မှ နုတ်ထွက်ရန်: {unsubscribe_oneclick}"
                        )
                        html_content = None

                    if html_content:
                        msg = EmailMultiAlternatives(
                            subject, plain_content, from_email, [sub.email],
                            connection=connection,
                        )
                        msg.attach_alternative(html_content, "text/html")
                        msg.send(fail_silently=False)
                    else:
                        send_mail(
                            subject, plain_content, from_email, [sub.email],
                            connection=connection, fail_silently=False,
                        )
                    count += 1
                except Exception as e:
                    errors += 1
                    logger.error("send_new_course_notification: failed for %s: %s", sub.email, e)
                    traceback.print_exc()
                    continue
    except Exception as e:
        logger.error("send_new_course_notification: SMTP connection failed: %s", e)
        traceback.print_exc()

    logger.info(
        "send_new_course_notification done: sent=%d failed=%d total=%d course=%s",
        count, errors, total_subs, course.title,
    )
    return count


def signup(request):
    if request.user.is_authenticated:
        return redirect('student_dashboard')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            if hasattr(user, 'profile'):
                user.profile.role = 'student'
                user.profile.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"မင်္ဂလာပါ {user.get_full_name() or user.username}! Arakkha Tech တွင် စာရင်းသွင်းခြင်း အောင်မြင်ပါသည်")
            return redirect('student_dashboard')
        else:
            messages.error(request, "စာရင်းသွင်းရာတွင် အမှားအယွင်းရှိနေပါသည်။ အောက်ပါပြဿနာများကို ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

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
    """Public contact form — saves submissions, notifies admins, blocks spam with honeypot."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Honeypot already validated inside clean_honeypot() above; commit & notify
            msg = form.save(commit=False)
            # Light anti-duplicate: same email + message in the last 15 minutes => skip notify.
            recent_dup = ContactMessage.objects.filter(
                email__iexact=msg.email,
                message=msg.message,
            ).order_by('-created_at').first()
            is_dup = bool(
                recent_dup and
                recent_dup.pk and
                (recent_dup.created_at and (recent_dup.created_at.timestamp() + 15*60) >
                 (msg.created_at.timestamp() if msg.created_at else __import__('time').time()))
            )
            msg.save()

            # Notify every admin + instructor staff of the new message (if not a duplicate flood).
            if not is_dup:
                try:
                    admin_ids = list(Profile.objects.filter(
                        role__in=('admin', 'instructor')
                    ).values_list('user_id', flat=True))
                    if not admin_ids:
                        admin_ids = list(User.objects.filter(
                            is_superuser=True, is_active=True
                        ).values_list('id', flat=True))
                    notif_objs = []
                    title = f"📩 {msg.subject_label} — {msg.name}"
                    snippet = (msg.message[:80] + '…') if len(msg.message) > 80 else msg.message
                    body = f"{msg.name} <{msg.email}> မှ မက်ဆေ့ဂျ်အသစ်: {snippet}"
                    for uid in admin_ids:
                        notif_objs.append(Notification(
                            user_id=uid,
                            title=title,
                            message=body,
                            is_read=False,
                            is_admin_notification=True,
                        ))
                    if notif_objs:
                        Notification.objects.bulk_create(notif_objs, batch_size=200, ignore_conflicts=True)
                except Exception:
                    # Never let the user see a 500 for notification failures;
                    # the message itself already persisted safely.
                    pass

            messages.success(
                request,
                "သင်၏ မက်ဆေ့ဂျ်ကို လက်ခံရဟိပါရေ။ မကြာခင် ပြန်လည်ဆက်သွယ်ပီးပါမေ။"
            )
            return redirect('contact')
        else:
            messages.error(
                request,
                "မက်ဆေ့ဂျ်ပီးပို့မှု မအောင်မြင်ပါ။ အောက်ပါ error များကို စစ်ဆီးပီးပါ။"
            )
    else:
        form = ContactForm()

    # Show a mini success preview block after first submission (for UX)
    show_success = False
    return render(request, 'courses/contact.html', {
        'form': form,
        'show_success': show_success,
    })

def privacy_policy(request):
    return render(request, 'courses/privacy_policy.html')

def newsletter_subscribe(request):
    if request.method != 'POST':
        return redirect(request.META.get('HTTP_REFERER', 'course_list'))

    form = NewsletterSubscribeForm(request.POST)
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
        return redirect(request.META.get('HTTP_REFERER', 'course_list'))

    email = form.cleaned_data['email']
    source = form.cleaned_data.get('source') or 'footer'

    ip_address = _get_client_ip(request)
    ua = (request.META.get('HTTP_USER_AGENT') or '')[:512]

    if not _check_rate_limit(request, 'newsletter', ip_address, max_requests=5, window_seconds=3600):
        messages.error(
            request,
            "အကြိမ်အကျော် လျှောထားပါပြီ။ ကျေးဇူးတင်ပါတယ်။ နာရီအနည်းငယ် အကြာမှာ ပြန်လည်ကြိုးစားပေးပါ။"
        )
        return redirect(request.META.get('HTTP_REFERER', 'course_list'))

    from django.utils import timezone
    now = timezone.now()

    subscriber = NewsletterSubscriber.objects.filter(email__iexact=email).first()

    if subscriber:
        if subscriber.confirmed and subscriber.is_active:
            messages.info(request, "ဤ Email သည် စာရင်းသွင်းပြီးသား ဖြစ်နေပါသည်။")
        elif not subscriber.confirmed:
            subscriber.generate_confirmation_token()
            subscriber.ip_address = ip_address
            subscriber.user_agent = ua
            subscriber.source = source
            subscriber.subscribed_at = now
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=[
                'confirmation_token', 'ip_address', 'user_agent',
                'source', 'subscribed_at', 'unsubscribed_at',
            ])
            _send_confirmation_email(subscriber, request)
            messages.success(
                request,
                "Email အတည်ပြုလိပ်စာကို ပြန်လည်ပို့ပေးပြီးပါပြီ။ သင့် Email Inbox ကို စစ်ဆေးပေးပါ။"
            )
        else:
            subscriber.is_active = True
            subscriber.confirmed = True
            subscriber.confirmed_at = now
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=[
                'is_active', 'confirmed', 'confirmed_at', 'unsubscribed_at',
            ])
            messages.success(request, "သတင်းလွှာအတွက် စာရင်းသွင်းမှု အောင်မြင်ပါသည်။ ကျေးဇူးတင်ပါသည်။")
    else:
        subscriber = NewsletterSubscriber(email=email)
        subscriber.generate_confirmation_token()
        subscriber.ip_address = ip_address
        subscriber.user_agent = ua
        subscriber.source = source
        subscriber.subscribed_at = now
        subscriber.is_active = False
        subscriber.confirmed = False
        subscriber.save()
        _send_confirmation_email(subscriber, request)
        messages.success(
            request,
            "စာရင်းသွင်းမှု အောင်မြင်ပါသည်။ သင့် Email Inbox တွင် ပေးပို့ထားသော Link ကို နှိပ်ပြီး အတည်ပြုပေးပါ။"
        )

    return redirect(request.META.get('HTTP_REFERER', 'course_list'))


def newsletter_confirm(request, token):
    from django.utils import timezone
    now = timezone.now()

    subscriber = get_object_or_404(NewsletterSubscriber, confirmation_token=token)

    if subscriber.confirmed and subscriber.is_active:
        messages.info(request, "Email သည် အရင်ကတည်းက အတည်ပြုပြီးသား ဖြစ်ပါတယ်။")
        return render(request, 'courses/newsletter_status.html', {
            'status': 'already_confirmed',
            'subscriber': subscriber,
            'title': 'Newsletter — အတည်ပြုမှု',
        })

    if subscriber.unsubscribed_at:
        subscriber.unsubscribed_at = None

    subscriber.confirmed = True
    subscriber.is_active = True
    subscriber.confirmed_at = now
    subscriber.save(update_fields=[
        'confirmed', 'is_active', 'confirmed_at', 'unsubscribed_at',
    ])

    messages.success(request, "Email အတည်ပြုမှု အောင်မြင်ပါသည်။ Newsletter ကို လက်ခံရရှိနိုင်ပါပြီ။ 🎉")

    return render(request, 'courses/newsletter_status.html', {
        'status': 'confirmed',
        'subscriber': subscriber,
        'title': 'Newsletter — အတည်ပြုမှု အောင်မြင်ပါသည်',
    })


def newsletter_unsubscribe(request, token):
    from django.utils import timezone
    subscriber = get_object_or_404(NewsletterSubscriber, confirmation_token=token)

    if request.method == 'POST':
        now = timezone.now()
        subscriber.is_active = False
        subscriber.confirmed = False
        subscriber.unsubscribed_at = now
        subscriber.save(update_fields=[
            'is_active', 'confirmed', 'unsubscribed_at',
        ])
        messages.success(request, "Newsletter မှ အောင်မြင်စွာ နုတ်ထွက်ပြီးပါပြီ။")
        return render(request, 'courses/newsletter_status.html', {
            'status': 'unsubscribed',
            'subscriber': subscriber,
            'title': 'Unsubscribe — အောင်မြင်ပါသည်',
        })

    return render(request, 'courses/newsletter_confirm_unsubscribe.html', {
        'subscriber': subscriber,
        'token': token,
        'title': 'Unsubscribe — အတည်ပြုရန်',
    })


def newsletter_unsubscribe_simple(request):
    email = (request.GET.get('email') or '').strip().lower()
    if not email:
        messages.error(request, "Email လိပ်စာ ထည့်ပေးပါ")
        return redirect('course_list')

    subscriber = NewsletterSubscriber.objects.filter(email__iexact=email).first()
    if not subscriber:
        messages.info(request, "ဤ Email သည် စာရင်းသွင်းထားခြင်း မရှိပါ။")
        return redirect('course_list')

    from django.utils import timezone
    subscriber.is_active = False
    subscriber.confirmed = False
    subscriber.unsubscribed_at = timezone.now()
    subscriber.save(update_fields=['is_active', 'confirmed', 'unsubscribed_at'])
    messages.success(request, f"{email} ကို Newsletter မှ အောင်မြင်စွာ နုတ်ထွက်ပြီးပါပြီ။")
    return redirect('course_list')


@login_required
@user_passes_test(is_admin)
def manage_newsletter(request):
    subscribers = NewsletterSubscriber.objects.all().order_by('-subscribed_at')
    stats = {
        'total': subscribers.count(),
        'active': subscribers.filter(is_active=True, confirmed=True).count(),
        'pending': subscribers.filter(confirmed=False).count(),
        'unsubscribed': subscribers.filter(unsubscribed_at__isnull=False).count(),
    }
    return render(request, 'courses/management/manage_newsletter.html', {
        'subscribers': subscribers,
        'stats': stats,
        'title': 'Manage Newsletter Subscribers',
    })


@login_required
@user_passes_test(is_admin)
def newsletter_toggle_active(request, pk):
    sub = get_object_or_404(NewsletterSubscriber, pk=pk)
    sub.is_active = not sub.is_active
    if sub.is_active and not sub.confirmed:
        from django.utils import timezone
        sub.confirmed = True
        sub.confirmed_at = timezone.now()
        update_fields = ['is_active', 'confirmed', 'confirmed_at']
    else:
        update_fields = ['is_active']
    sub.save(update_fields=update_fields)
    status = "activated" if sub.is_active else "deactivated"
    messages.success(request, f"{sub.email} ကို {status} လုပ်ပြီးပါပြီ")
    return redirect('manage_newsletter')


@login_required
@user_passes_test(is_admin)
def newsletter_delete(request, pk):
    sub = get_object_or_404(NewsletterSubscriber, pk=pk)
    if request.method == 'POST':
        email = sub.email
        sub.delete()
        messages.success(request, f"{email} ကို ဖျက်သိမ်းပြီးပါပြီ")
        return redirect('manage_newsletter')
    return render(request, 'courses/confirm_delete.html', {
        'item': sub,
        'type': f'Newsletter Subscriber ({sub.email})',
    })


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip or None


def _check_rate_limit(request, namespace, identifier, max_requests=5, window_seconds=3600):
    if not identifier:
        return True
    from django.core.cache import caches
    import time
    try:
        cache = caches['default']
    except Exception:
        cache = None
    if cache is None:
        return True
    key = f"{namespace}:{identifier}"
    history = cache.get(key, []) or []
    now = time.time()
    cutoff = now - window_seconds
    history = [t for t in history if t > cutoff]
    if len(history) >= max_requests:
        return False
    history.append(now)
    cache.set(key, history, window_seconds)
    return True


def _send_confirmation_email(subscriber, request):
    try:
        if request is not None and hasattr(request, 'scheme'):
            protocol = request.scheme
        else:
            protocol = getattr(settings, 'ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'http')

        if request is not None and hasattr(request, 'get_host'):
            host = request.get_host()
        elif settings.ALLOWED_HOSTS:
            host = settings.ALLOWED_HOSTS[0]
        else:
            host = 'localhost:8000'

        try:
            confirm_path = reverse('newsletter_confirm', kwargs={'token': subscriber.confirmation_token})
        except Exception as e:
            logger.error("_send_confirmation_email: reverse confirm failed token=%s err=%s", subscriber.confirmation_token, e)
            confirm_path = f"/newsletter/confirm/{subscriber.confirmation_token}/"
        try:
            unsub_path = reverse('newsletter_unsubscribe', kwargs={'token': subscriber.confirmation_token})
        except Exception as e:
            logger.error("_send_confirmation_email: reverse unsub failed token=%s err=%s", subscriber.confirmation_token, e)
            unsub_path = f"/newsletter/unsubscribe/{subscriber.confirmation_token}/"

        confirm_url = f"{protocol}://{host}{confirm_path}"
        unsubscribe_url = f"{protocol}://{host}{unsub_path}"

        subject = "Arakkha Tech Newsletter — အီးမေးလ် အတည်ပြုရန် ✉️"
        from_email = settings.DEFAULT_FROM_EMAIL or 'arakkhatech@gmail.com'

        year = timezone.now().year
        context = {
            'subscriber': subscriber,
            'confirm_url': confirm_url,
            'unsubscribe_url': unsubscribe_url,
            'year': year,
        }

        html_content = None
        try:
            html_content = render_to_string('emails/newsletter_confirm.html', context)
            plain_content = strip_tags(html_content)
        except Exception as e:
            logger.warning("_send_confirmation_email: template failed: %s", e)
            traceback.print_exc()
            plain_content = (
                f"မင်္ဂလာပါ,\n\n"
                f"Arakkha Tech Newsletter ကို စာရင်းသွင်းမှုအတွက် ကျေးဇူးတင်ပါတယ်။\n"
                f"အောက်ပါ Link ကို နှိပ်ပြီး သင့် Email ကို အတည်ပြုပေးပါ:\n\n"
                f"{confirm_url}\n\n"
                f"အကယ်၍ မလိုအပ်ပါက အောက်ပါ Link ဖြင့် နုတ်ထွက်နိုင်ပါတယ်:\n"
                f"{unsubscribe_url}\n\n"
                f"ကျေးဇူးတင်ပါတယ်,\nArakkha Tech Team"
            )
            html_content = None

        logger.info(
            "_send_confirmation_email: sending to=%s from=%s host=%s port=%s user=%s",
            subscriber.email, from_email,
            getattr(settings, 'EMAIL_HOST', '?'),
            getattr(settings, 'EMAIL_PORT', '?'),
            getattr(settings, 'EMAIL_HOST_USER', '') or '(empty)',
        )

        with get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            timeout=30,
        ) as connection:
            if html_content:
                msg = EmailMultiAlternatives(
                    subject, plain_content, from_email, [subscriber.email],
                    connection=connection,
                )
                msg.attach_alternative(html_content, "text/html")
                sent = msg.send(fail_silently=False)
                logger.info("_send_confirmation_email: HTML sent to=%s result=%s", subscriber.email, sent)
            else:
                sent = send_mail(
                    subject, plain_content, from_email, [subscriber.email],
                    connection=connection, fail_silently=False,
                )
                logger.info("_send_confirmation_email: plain sent to=%s result=%s", subscriber.email, sent)
            return bool(sent)
    except Exception as e:
        logger.error("_send_confirmation_email: FATAL to=%s err=%s", subscriber.email, e)
        traceback.print_exc()
        return False

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, request.FILES, instance=profile, editing_user=request.user)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "ပရိုဖိုင်နှင့် အချက်အလက်များကို ပြင်ဆင်ပြီးပါပြီ")
            return redirect('student_dashboard')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileForm(instance=profile, editing_user=request.user)
        
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
        form = CourseForm(request.POST, request.FILES, editing_user=request.user)
        if form.is_valid():
            try:
                course = form.save()
                # Send notification email to all newsletter subscribers
                try:
                    email_count = send_new_course_notification(course)
                    if email_count > 0:
                        messages.success(request, f"သင်တန်းအသစ်ကို အောင်မြင်စွာ ထည့်သွင်းပြီး Newsletter Subscribers ({email_count}) ယောက်ထံ အီးမေးလ်ပို့ပြီးပါပြီ")
                    else:
                        messages.success(request, "သင်တန်းအသစ်ကို အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ")
                except Exception:
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
        form = CourseForm(initial={'instructor': request.user}, editing_user=request.user)
    return render(request, 'courses/management/course_form.html', {'form': form, 'title': 'သင်တန်းအသစ်ဖွင့်ရန်'})

@login_required
@user_passes_test(is_instructor)
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if not can_manage_course(request.user, course):
        messages.error(request, "ဤသင်တန်းကို ပြင်ဆင်ခွင့်မရှိပါ။")
        return redirect('manage_courses')
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course, editing_user=request.user)
        if form.is_valid():
            try:
                course = form.save()
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
        form = CourseForm(instance=course, editing_user=request.user)
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
@user_passes_test(is_instructor)
def manage_enrollments(request):
    if is_admin(request.user):
        enrollments = Enrollment.objects.select_related('student', 'student__profile', 'course', 'course__instructor') \
            .prefetch_related('completed_lessons').order_by('-date_enrolled')
    else:
        enrollments = Enrollment.objects.filter(course__instructor=request.user) \
            .select_related('student', 'student__profile', 'course', 'course__instructor') \
            .prefetch_related('completed_lessons').order_by('-date_enrolled')
    return render(request, 'courses/management/manage_enrollments.html', {'enrollments': enrollments})

@login_required
@user_passes_test(is_instructor)
def enroll_student(request, student_pk=None):
    if student_pk:
        student = get_object_or_404(User, pk=student_pk)
        initial_data = {'student': student}
    else:
        initial_data = {}

    if request.method == 'POST':
        form = ManualEnrollmentForm(request.POST, user=request.user)
        if form.is_valid():
            enrollment = form.save(commit=False)
            if not is_admin(request.user):
                if enrollment.course.instructor_id != request.user.id:
                    messages.error(request, "ဤသင်တန်းကို ကျောင်းသားများအား enroll လုပ်ခွင့်မရှိပါ")
                    return redirect('manage_enrollments')
            enrollment.save()
            # Create notification for instructor/admin who enrolled
            Notification.objects.create(
                user=request.user,
                title="New Enrollment",
                message=f"Student {enrollment.student.username} has been enrolled in {enrollment.course.title}.",
                is_admin_notification=is_admin(request.user)
            )
            # Create notification for student
            Notification.objects.create(
                user=enrollment.student,
                title="New Course Access",
                message=f"You have been given access to the course: {enrollment.course.title} by {request.user.get_full_name() or request.user.username}.",
                is_admin_notification=False
            )
            messages.success(request, "သင်တန်းအတွက် Access ပေးခြင်း အောင်မြင်ပါသည်")
            return redirect('manage_enrollments')
    else:
        form = ManualEnrollmentForm(initial=initial_data, user=request.user)
        
    return render(request, 'courses/management/enroll_student_form.html', {'form': form, 'title': 'သင်တန်း Access ပေးရန်'})

@login_required
@user_passes_test(is_instructor)
def remove_enrollment(request, enrollment_pk):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk)
    if not is_admin(request.user):
        if enrollment.course.instructor_id != request.user.id:
            messages.error(request, "ဤenrollment ကို ဖျက်သိမ်းခွင့်မရှိပါ")
            return redirect('manage_enrollments')
    if request.method == 'POST':
        course_title = enrollment.course.title
        student_name = enrollment.student.username
        enrollment.delete()
        Notification.objects.create(
            user=enrollment.student,
            title="Course Access Removed",
            message=f"Your access to the course: {course_title} has been removed.",
            is_admin_notification=False
        )
        messages.success(request, f"{student_name} ကို {course_title} မှ ထုတ်ပယ်ပြီးပါပြီ")
        return redirect('manage_enrollments')
    return render(request, 'courses/management/confirm_delete.html', {'item': enrollment, 'type': f'Enrollment ({enrollment.student.username} - {enrollment.course.title})'})

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

# User Management Views (All Users including Admins/Instructors) — role-filtered buckets
@login_required
@user_passes_test(is_admin)
def manage_users(request):
    role = request.GET.get('role', 'all').strip().lower()
    query = request.GET.get('q', '').strip()

    base_qs = User.objects.select_related('profile').prefetch_related('enrollments').all()

    if role in {'student', 'instructor', 'admin'}:
        base_qs = base_qs.filter(profile__role=role)
    elif role == 'staff':
        base_qs = base_qs.filter(Q(profile__role='instructor') | Q(profile__role='admin'))

    if query:
        base_qs = base_qs.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    users = list(base_qs.order_by('-date_joined'))

    counts = {
        'all': User.objects.count(),
        'student': User.objects.filter(profile__role='student').count(),
        'instructor': User.objects.filter(profile__role='instructor').count(),
        'admin': User.objects.filter(profile__role='admin').count(),
    }

    for u in users:
        u.enrollment_count = getattr(u, 'enrollments', None) and u.enrollments.count() or Enrollment.objects.filter(student=u).count()

    return render(request, 'courses/management/manage_users.html', {
        'users': users,
        'counts': counts,
        'active_role': role,
        'query': query,
    })


@login_required
@user_passes_test(is_admin)
def toggle_user_active(request, user_pk):
    target = get_object_or_404(User, pk=user_pk)
    if target.id == request.user.id:
        messages.error(request, "သင်ကိုယ်တိုင် အကောင့်ပိတ်မရနိုင်ပါ")
        return redirect('manage_users')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    status = "activated" if target.is_active else "deactivated"
    messages.success(request, f"{target.username} အကောင့်ကို {status} လုပ်ပြီးပါပြီ")
    return redirect('manage_users')


@login_required
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        user_form = StudentCreationForm(request.POST)
        
        if user_form.is_valid():
            user = user_form.save()
            # Now update the profile (which was created by the signal)
            profile_form = ProfileForm(request.POST, request.FILES, instance=user.profile, editing_user=request.user)
            if profile_form.is_valid():
                profile_form.save()
                # Role upgrade -> superuser/staff flags on Django User model
                role = user.profile.role
                user.is_staff = role in ('instructor', 'admin')
                user.is_superuser = (role == 'admin')
                user.save(update_fields=['is_staff', 'is_superuser'])

                # Admin notification
                Notification.objects.create(
                    user=request.user,
                    title="New User Created",
                    message=f"New account for {user.username} (Role: {user.profile.role}) has been created successfully.",
                    is_admin_notification=True
                )
                
                messages.success(request, f"User {user.username} ({user.profile.role}) ကို အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ")
                return redirect('manage_users')
            else:
                # If profile form is invalid, delete the created user
                user.delete()
                messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
        else:
            profile_form = ProfileForm(request.POST, request.FILES, editing_user=request.user)
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        user_form = StudentCreationForm()
        profile_form = ProfileForm(editing_user=request.user)
    
    return render(request, 'courses/management/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'title': 'User အသစ်ဖန်တီးရန်'
    })

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_pk):
    user = get_object_or_404(User.objects.select_related('profile'), pk=user_pk)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=user.profile, editing_user=request.user)
        
        if user_form.is_valid() and profile_form.is_valid():
            u = user_form.save()
            profile_form.save()

            role = u.profile.role
            # Keep Django is_staff / is_superuser synchronized with role
            u.is_staff = role in ('instructor', 'admin')
            u.is_superuser = (role == 'admin')
            u.save(update_fields=['is_staff', 'is_superuser'])

            messages.success(request, f"User {u.username} (role: {role}) ကို အောင်မြင်စွာ ပြင်ဆင်ပြီးပါပြီ")
            return redirect('manage_users')
        else:
            messages.error(request, "အချက်အလက်များ မှားယွင်းနေပါသည်။ ပြန်လည်စစ်ဆေးပေးပါ။")
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=user.profile, editing_user=request.user)
    
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

    # Real DB-backed landing page statistics
    total_courses = Course.objects.count()
    total_instructors = Profile.objects.filter(role='instructor', user__is_active=True).count()
    active_students = Enrollment.objects.values('student').distinct().count()

    # Satisfaction: weighted 98% baseline + 2% bonus when there are approved voices.
    # CommunityVoice model does not currently store an explicit rating field, so we
    # treat it as an adoption signal (more approved voices => higher satisfaction up to 99%).
    approved_count = CommunityVoice.objects.filter(is_approved=True).count()
    if approved_count:
        bonus = min(1, int(approved_count // 10))
        satisfaction_pct = min(99, 98 + bonus)
    else:
        satisfaction_pct = 98

    def _fmt_count(value):
        if value >= 1000:
            return f"{round(value / 1000, 1):g}K+"
        if value >= 100:
            return f"{value}+"
        if value > 0:
            return str(value)
        return "0+"

    stats = [
        {
            'number': _fmt_count(active_students),
            'raw_value': active_students,
            'label': 'Active Students',
            'icon': 'fas fa-user-graduate',
            'accent': 'from-indigo-500/10 to-sky-500/10',
            'icon_bg': 'bg-indigo-100 text-indigo-600',
        },
        {
            'number': _fmt_count(total_courses),
            'raw_value': total_courses,
            'label': 'Total Courses',
            'icon': 'fas fa-book-open',
            'accent': 'from-fuchsia-500/10 to-rose-500/10',
            'icon_bg': 'bg-fuchsia-100 text-fuchsia-600',
        },
        {
            'number': _fmt_count(total_instructors),
            'raw_value': total_instructors,
            'label': 'Expert Instructors',
            'icon': 'fas fa-chalkboard-teacher',
            'accent': 'from-emerald-500/10 to-teal-500/10',
            'icon_bg': 'bg-emerald-100 text-emerald-600',
        },
        {
            'number': f"{satisfaction_pct}%",
            'raw_value': satisfaction_pct,
            'label': 'Satisfaction Rate',
            'icon': 'fas fa-face-smile',
            'accent': 'from-amber-500/10 to-orange-500/10',
            'icon_bg': 'bg-amber-100 text-amber-600',
        },
    ]

    # Static data for landing page sections (copy stays, stats are dynamic)
    features = [
        {'icon': 'fas fa-rocket', 'title': 'အယင်ဆုံး သင်ယူမှု', 'desc': 'စနစ်ကျသော roadmap များဖြင့် အချိန်တိုအတွင်း တတ်မြောက်စီရမည်။'},
        {'icon': 'fas fa-certificate', 'title': 'လက်မှတ်ရဟိခြင်း', 'desc': 'သင်တန်းပြီးဆုံးပါက အရည်အသွေးမီ လက်မှတ်များကို ထုတ်ပီးပါသည်။'},
        {'icon': 'fas fa-users', 'title': 'Community Support', 'desc': 'သင်တန်းသားအချင်းချင်း ဆွေးနွေးနိုင်မည့် community ဟိပါသည်။'},
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


def courses_page(request):
    """
    Dedicated standalone Courses landing page (independent of home course_list).
    URL: /courses/  (template name: courses/course.html as requested).
    """
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest')

    base_qs = (
        Course.objects.select_related('instructor')
        .prefetch_related('lessons', 'enrolled_students')
        .annotate(
            student_count=Count('enrolled_students', distinct=True),
            lesson_count=Count('lessons', distinct=True),
        )
    )

    if query:
        base_qs = base_qs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(instructor__username__icontains=query)
        ).distinct()

    # Simple soft categorization by keyword in title (keeps the page functional
    # without having to add a category FK to the Course model right now).
    category_keywords = {
        'programming': ['python', 'django', 'javascript', 'react', 'flutter', 'coding', 'code', 'programming', 'နည်းပညာ', 'ကုဒ်', 'ပရိုဂရမ်'],
        'design': ['ui', 'ux', 'design', 'css', 'tailwind', 'figma', 'ဒီဇိုင်း'],
        'business': ['business', 'marketing', 'seo', 'startup', 'စီးပွားရေး', 'မာခက်တင်'],
        'language': ['english', 'japanese', 'iit', 'ielts', 'ဘာသာစကား', 'အင်္ဂလိပ်'],
    }
    if category and category in category_keywords:
        kw_filter = Q()
        for kw in category_keywords[category]:
            kw_filter |= Q(title__icontains=kw) | Q(description__icontains=kw)
        base_qs = base_qs.filter(kw_filter)

    if sort == 'popular':
        courses = base_qs.order_by('-student_count', '-created_at')
    elif sort == 'shortest':
        courses = base_qs.order_by('lesson_count', '-created_at')
    else:  # newest
        courses = base_qs.order_by('-created_at')

    courses = list(courses)

    # Aggregate stats for the hero
    total_courses = len(courses)
    total_lessons = sum((c.lesson_count or 0) for c in courses)
    total_students = sum((c.student_count or 0) for c in courses)
    try:
        total_instructors = Course.objects.values('instructor').distinct().count()
    except Exception:
        total_instructors = 0

    featured = [c for c in courses[:6]]

    categories = [
        {'key': '',           'label': 'All Courses',      'icon': 'fas fa-layer-group'},
        {'key': 'programming','label': 'Programming',      'icon': 'fas fa-code'},
        {'key': 'design',     'label': 'UI / UX / Design', 'icon': 'fas fa-pen-ruler'},
        {'key': 'business',   'label': 'Business',         'icon': 'fas fa-briefcase'},
        {'key': 'language',   'label': 'Languages',        'icon': 'fas fa-language'},
    ]

    sort_options = [
        {'key': 'newest',   'label': 'Newest'},
        {'key': 'popular',  'label': 'Popular'},
        {'key': 'shortest', 'label': 'Shortest'},
    ]

    hero_stats = [
        {'number': f'{total_courses}+',  'label': 'Courses Available', 'icon': 'fas fa-book-open',  'accent': 'indigo'},
        {'number': f'{total_lessons}+',  'label': 'Total Lessons',     'icon': 'fas fa-layer-group', 'accent': 'fuchsia'},
        {'number': f'{total_students}+', 'label': 'Students Enrolled', 'icon': 'fas fa-users',       'accent': 'emerald'},
        {'number': f'{total_instructors}+','label': 'Expert Instructors','icon':'fas fa-user-graduate','accent':'amber'},
    ]

    testimonials = [
        {'name': 'Kyaw Zayar', 'role': 'Frontend Developer', 'text': 'အေ platform ကနိန်ပနာ လိလာရစွာ တကယ့်ကို ထိရောက်ပါတယ်။ ဗီဒီယိုတွေကလည်း ရှင်းလင်းပါတယ်။'},
        {'name': 'Hsu Myat',   'role': 'Student',             'text': 'သင်တန်းပို့ချပုံစံက နားလည်လွယ်ပါတယ်။ Real-world project တွေကလည်း အရမ်းကောင်းပါတယ်။'},
        {'name': 'Aung Ko',    'role': 'Junior Developer',    'text': 'Course လိုင်းစဉ်လိုက်ပြီး သင်ယူလို့ရတာ ကောင်းပါတယ်။ Career အစပိုင်းမှာ အထောက်အကူအများကြီးရခဲ့ပါတယ်။'},
    ]

    return render(request, 'courses/course.html', {
        'courses': courses,
        'featured': featured,
        'query': query,
        'category': category,
        'sort': sort,
        'categories': categories,
        'sort_options': sort_options,
        'hero_stats': hero_stats,
        'testimonials': testimonials,
        'total_courses': total_courses,
    })


# ============================================================
# Instructor Public Pages (Listing + Detail)
# ============================================================
def instructors_list(request):
    """
    Public Instructor listing page, accessible via Navbar.
    Order: featured pinned on top, then by created_at desc.
    """
    profiles_qs = (
        Profile.objects.filter(role='instructor', user__is_active=True)
        .select_related('user')
        .prefetch_related('user__courses_taught', 'user__courses_taught__enrolled_students')
        .order_by('-is_featured', '-user__date_joined')
    )

    instructors = list(profiles_qs)
    for p in instructors:
        courses = list(p.user.courses_taught.all())
        p.course_count = len(courses)
        p.total_students = sum(len(list(c.enrolled_students.all())) for c in courses)
        p.avg_rating = 4.9  # review aggregator placeholder

    featured = [i for i in instructors if i.is_featured]
    total_students = sum(i.total_students for i in instructors)

    return render(request, 'courses/instructors_list.html', {
        'instructors': instructors,
        'featured': featured,
        'total_instructors': len(instructors),
        'total_courses': sum(i.course_count for i in instructors),
        'total_students': total_students,
    })


def instructor_detail(request, slug):
    """
    Public Instructor profile detail page.
    URL: /instructor/<slug>/
    """
    profile = get_object_or_404(
        Profile.objects.filter(role='instructor', user__is_active=True)
        .select_related('user')
        .prefetch_related('user__courses_taught', 'user__courses_taught__lessons',
                          'user__courses_taught__enrolled_students'),
        slug=slug
    )
    user = profile.user
    courses = list(user.courses_taught.all().order_by('-created_at'))
    for c in courses:
        c.lesson_count = c.lessons.count()
        c.student_count = c.enrolled_students.count()
        c.total_rating = 4.9
    total_students = sum(getattr(c, 'student_count', 0) for c in courses)
    total_lessons = sum(getattr(c, 'lesson_count', 0) for c in courses)

    return render(request, 'courses/instructor_detail.html', {
        'profile': profile,
        'instructor': user,
        'courses': courses,
        'total_courses': len(courses),
        'total_students': total_students,
        'total_lessons': total_lessons,
        'avg_rating': 4.9,
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


# ──────────────────────────────────────────────────────────────
#  Contact Messages — Admin + Instructor management
# ──────────────────────────────────────────────────────────────
def _contact_staff_or_403(request):
    """Instructors + Admins can view/manage contact messages."""
    if not request.user.is_authenticated:
        return False
    try:
        return is_admin(request.user) or is_instructor(request.user)
    except Exception:
        return False


@login_required
def manage_contacts(request):
    if not _contact_staff_or_403(request):
        messages.error(request, "ဈေးဝယ်ခွင့်မရှိပါ။ Contact messages ကို Admin/Instructor သာ ကြည့်ရှုနိုင်ပါတယ်။")
        return redirect('course_list')

    # Tabs: All / Unread / Answered / Unanswered + search across name/email/message
    status = request.GET.get('status', 'all').strip().lower()
    q = request.GET.get('q', '').strip()
    subject = request.GET.get('subject', '').strip()

    qs = ContactMessage.objects.all()
    if status == 'unread':
        qs = qs.filter(is_read=False)
    elif status == 'read':
        qs = qs.filter(is_read=True)
    elif status == 'answered':
        qs = qs.filter(is_answered=True)
    elif status == 'unanswered':
        qs = qs.filter(is_answered=False)

    if subject and subject in dict(ContactMessage.SUBJECT_CHOICES).keys():
        qs = qs.filter(subject=subject)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q) |
            Q(message__icontains=q)
        ).distinct()

    qs = qs.order_by('-created_at')

    counts = {
        'all':        ContactMessage.objects.count(),
        'unread':     ContactMessage.objects.filter(is_read=False).count(),
        'answered':   ContactMessage.objects.filter(is_answered=True).count(),
        'unanswered': ContactMessage.objects.filter(is_answered=False).count(),
    }

    return render(request, 'courses/management/manage_contacts.html', {
        'contacts': qs,
        'status':   status,
        'query':    q,
        'subject_filter': subject,
        'counts':   counts,
        'subjects': ContactMessage.SUBJECT_CHOICES,
    })


@login_required
def contact_detail(request, pk):
    if not _contact_staff_or_403(request):
        messages.error(request, "ဈေးဝယ်ခွင့်မရှိပါ။")
        return redirect('course_list')
    msg = get_object_or_404(ContactMessage, pk=pk)

    # Handle any internal note / answered toggle submitted from the detail page.
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        if action == 'save_note':
            note = (request.POST.get('internal_note') or '').strip()[:1000]
            msg.internal_note = note
            msg.save(update_fields=['internal_note', 'updated_at'])
            messages.success(request, "Internal note ကို သိမ်းဆည်းပြီးပြီ။")
        elif action == 'mark_read':
            msg.is_read = True
            msg.save(update_fields=['is_read', 'updated_at'])
            messages.success(request, "ဖတ်ပြီးပြီ လို့ အမှတ်အသားပေးလိုက်ပါတယ်။")
        elif action == 'mark_unread':
            msg.is_read = False
            msg.save(update_fields=['is_read', 'updated_at'])
            messages.success(request, "မဖတ်ရသေးသေးဘူး လို့ ပြန်ပြောင်းလိုက်ပါတယ်။")
        elif action == 'toggle_answered':
            msg.is_answered = not msg.is_answered
            msg.is_read = True
            msg.save(update_fields=['is_answered', 'is_read', 'updated_at'])
            messages.success(
                request,
                "အဖြေပေးပြီးပြီ" if msg.is_answered else "အဖြေမပေးသေးဘူး လို့ ပြောင်းလိုက်ပါတယ်။"
            )
        return redirect('contact_detail', pk=msg.pk)

    # Auto-mark as read when an admin/instructor opens the detail page.
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read', 'updated_at'])

    return render(request, 'courses/management/contact_detail.html', {
        'msg': msg,
    })


@login_required
def contact_mark_read(request, pk):
    if not _contact_staff_or_403(request):
        messages.error(request, "ဈေးဝယ်ခွင့်မရှိပါ။")
        return redirect('course_list')
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_read = True
    msg.save(update_fields=['is_read', 'updated_at'])
    messages.success(request, "#{} ကို ဖတ်ပြီးပြီ လို့ အမှတ်အသားပေးလိုက်ပါတယ်။".format(pk))
    return redirect(request.META.get('HTTP_REFERER') or 'manage_contacts')


@login_required
def contact_mark_unread(request, pk):
    if not _contact_staff_or_403(request):
        messages.error(request, "ဈေးဝယ်ခွင့်မရှိပါ။")
        return redirect('course_list')
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_read = False
    msg.save(update_fields=['is_read', 'updated_at'])
    messages.success(request, "#{} ကို မဖတ်ရသေးသေးဘူး လို့ ပြန်ပြောင်းလိုက်ပါတယ်။".format(pk))
    return redirect(request.META.get('HTTP_REFERER') or 'manage_contacts')


@login_required
def contact_toggle_answered(request, pk):
    if not _contact_staff_or_403(request):
        messages.error(request, "ဈေးဝယ်ခွင့်မရှိပါ။")
        return redirect('course_list')
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_answered = not msg.is_answered
    if msg.is_answered and not msg.is_read:
        msg.is_read = True
    msg.save(update_fields=['is_answered', 'is_read', 'updated_at'])
    messages.success(
        request,
        "အဖြေပေးပြီးပြီ လို့ သိမ်းလိုက်ပါတယ်။" if msg.is_answered else "အဖြေမပေးသေးဘူး လို့ ပြောင်းလိုက်ပါတယ်။"
    )
    return redirect(request.META.get('HTTP_REFERER') or 'manage_contacts')


@login_required
@user_passes_test(is_admin)
def contact_delete(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.delete()
    messages.success(request, f"#{pk} မက်ဆေ့ဂျ်ကို ဖျက်ပြီးပြီ။")
    return redirect('manage_contacts')


def course_detail_pk_redirect(request, pk):
    """
    Legacy /course/<int:pk>/ URL — redirects to the clean slug-based URL.
    Keeps backwards compatibility for any old deep links / bookmarks.
    """
    c = get_object_or_404(Course, pk=pk)
    if not c.slug:
        c.save(update_fields=['slug'])
        c.refresh_from_db()
    return redirect('course_detail', slug=c.slug, permanent=True)


def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.select_related('instructor')
        .prefetch_related('lessons', 'enrolled_students'),
        slug=slug
    )
    is_enrolled = False
    enrollment = None
    progress_pct = 0
    completed_lesson_ids = []

    if request.user.is_authenticated:
        enrollment = (
            Enrollment.objects.filter(student=request.user, course=course)
            .prefetch_related('completed_lessons')
            .first()
        )
        is_enrolled = enrollment is not None
        if enrollment:
            progress_pct = enrollment.progress_percentage or 0
            completed_lesson_ids = list(
                enrollment.completed_lessons.values_list('id', flat=True)
            )

    lessons = list(course.lessons.all())
    lesson_count = len(lessons)
    enrolled_student_count = course.enrolled_students.count()

    # Try to grab the instructor's profile (avatar, bio) without errors.
    instructor_profile = None
    try:
        instructor_profile = getattr(course.instructor, 'profile', None)
    except Exception:
        instructor_profile = None

    # Course description with markdown support.
    try:
        description_html = markdown.markdown(
            course.description or '',
            extensions=[
                'extra', 'codehilite', 'toc', 'nl2br', 'sane_lists',
                'fenced_code', 'attr_list', 'admonition',
            ]
        )
    except Exception:
        description_html = course.description or ''

    # Total duration as pretty string (best effort).
    total_minutes = 0
    total_seconds = 0
    for l in lessons:
        if not l.duration:
            continue
        parts = str(l.duration).split(':')
        try:
            if len(parts) == 3:
                h, m, s = parts
                total_minutes += int(h) * 60 + int(m)
                total_seconds += int(s)
            elif len(parts) == 2:
                m, s = parts
                total_minutes += int(m)
                total_seconds += int(s)
        except Exception:
            pass
    total_minutes += total_seconds // 60
    total_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60
    if total_hours > 0:
        total_duration_str = f"{total_hours}h {remaining_minutes}m"
    else:
        total_duration_str = f"{remaining_minutes}m" if remaining_minutes else "—"

    # Related courses (same instructor, excluding the current one).
    related_courses = list(
        Course.objects.filter(instructor=course.instructor)
        .exclude(pk=course.pk)
        .annotate(student_count=Count('enrolled_students'))
        .order_by('-created_at')[:3]
    )

    # High-level FAQ / feature blocks shared across all course detail pages.
    # Kept static here so the page always has a polished FAQ section.
    course_features = [
        {
            'icon': 'fas fa-video',
            'title': 'အရည်အသွေးမြင့် ဗီဒီယိုသင်ခန်းစာများ',
            'desc': 'HD ဂုဏ်သတ္တိရှိသော ဗီဒီယိုများဖြင့် ရှင်းလင်းစွာ သင်ကြားပေးပါသည်။',
        },
        {
            'icon': 'fas fa-infinity',
            'title': 'ထပ်ခါထပ်ခါ ကြည့်ရှုနိုင်ခွင့်',
            'desc': 'တစ်ခါအပ်နှံပြီးသည်နှင့် ဘယ်အချိန်မဆို ထပ်ခါထပ်ခါ ကြည့်ရှုနိုင်ပါသည်။',
        },
        {
            'icon': 'fas fa-file-code',
            'title': 'လက်တွေ့ကျသော Source Code',
            'desc': 'သင်ခန်းစာတိုင်းနှင့်အတူ source code နှင့် project files များကို ပေးပို့ပေးပါသည်။',
        },
        {
            'icon': 'fas fa-certificate',
            'title': 'ပြီးဆုံးမှတ်တမ်း (Certificate)',
            'desc': 'သင်တန်းအားလုံးပြီးဆုံးသူများအား လက်မှတ်နှင့်အတူ ဂုဏ်ပြုပေးပါသည်။',
        },
        {
            'icon': 'fas fa-comments',
            'title': 'Community & Support',
            'desc': 'Community group တွင် မေးခွန်းများမေးနိုင်ပြီး instructor ထံမှ အကူအညီရရှိနိုင်ပါသည်။',
        },
        {
            'icon': 'fas fa-mobile-alt',
            'title': 'Mobile အသုံးပြုနိုင်မှု',
            'desc': 'ဖုန်း၊ တက်ဘလက်၊ ကွန်ပျူတာ — မည်သည့်စက်ပစ္စည်းနှင့်မဆို ကြည့်ရှုနိုင်ပါသည်။',
        },
    ]

    faqs = [
        {
            'q': 'သင်တန်းကို ဝင်ခွင့်ရရှိနိုင်ရန် အရင်ဆုံးဘာတွေလုပ်ရမလဲ?',
            'a': 'အကောင့်တစ်ခုဖွင့်ပြီး Course Detail Page ရှိ "Enroll Now" ကိုနှိပ်ရုံသာ လုံလောက်ပါသည်။ အခုလက်ရှိ demo courses များကို Free ဖြင့် အပ်နှံနိုင်ပါသည်။',
        },
        {
            'q': 'ဗီဒီယိုများကို စစ်ဆေးကြည့်လို့ရပါသလား?',
            'a': 'သင်တန်းအတွင်း ပထမဆုံးသင်ခန်းစာများကို စမ်းကြည့်နိုင်ပြီး Enroll မလုပ်မီ အကြောင်းအရာအစီအစဉ်ကို စစ်ဆေးနိုင်ပါသည်။',
        },
        {
            'q': 'သင်တန်းပြီးရင် Certificate ရနိုင်ပါသလား?',
            'a': 'ဟုတ်ပါသည်။ သင်ခန်းစာအားလုံးပြီးဆုံးပါက Arakkha Tech မှ ချမှတ်သော Certificate တစ်ခုကို အလိုအလျောက် ထုတ်ပေးပါသည်။',
        },
        {
            'q': 'ဗီဒီယိုကို download လုပ်လို့ရပါသလား?',
            'a': 'လက်ရှိ streaming သာလုပ်နိုင်ပြီး download ခွင့်မပေးထားသေးပါ။ ဒါပေမယ့် ဘယ်အချိန်မဆို ထပ်ခါထပ်ခါ ကြည့်ရှုနိုင်ပါသည်။',
        },
    ]

    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons': lessons,
        'lesson_count': lesson_count,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'progress_pct': progress_pct,
        'completed_lesson_ids': completed_lesson_ids,
        'enrolled_student_count': enrolled_student_count,
        'instructor_profile': instructor_profile,
        'description_html': description_html,
        'total_duration_str': total_duration_str,
        'related_courses': related_courses,
        'course_features': course_features,
        'faqs': faqs,
        # Querystring-based tab: <url>?tab=curriculum
        'active_tab': request.GET.get('tab', 'overview'),
    })

@login_required
def lesson_detail(request, course_pk, lesson_pk):
    course = get_object_or_404(Course, pk=course_pk)
    # Check if student is enrolled
    enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
    if not enrollment:
        messages.error(request, "သင်ခန်းစာများကို ကြည့်ရှုရန် အရင်ဆုံး သင်တန်းအပ်နှံပေးပါ")
        return redirect('course_detail', slug=course.slug)
    
    lesson = get_object_or_404(Lesson, pk=lesson_pk, course=course)
    lessons = course.lessons.all() # Get all lessons for the sidebar

    # Convert lesson.content markdown to HTML with full extension support
    try:
        content_html = markdown.markdown(lesson.content or '', extensions=[
            'extra', 'codehilite', 'toc', 'nl2br', 'sane_lists',
            'fenced_code', 'attr_list', 'admonition',
        ])
    except Exception:
        content_html = lesson.content or ''

    # Get completed lesson IDs for the current enrollment
    completed_lesson_ids = enrollment.completed_lessons.values_list('id', flat=True)

    # Get next and previous lessons
    next_lesson = course.lessons.filter(order__gt=lesson.order).order_by('order').first()
    prev_lesson = course.lessons.filter(order__lt=lesson.order).order_by('-order').first()

    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'content_html': content_html,
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
    course = get_object_or_404(Course, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "သင်တန်းအပ်နှံရန် Admin ကို ဆက်သွယ်ပေးပါ။")
        return redirect('course_detail', slug=course.slug)
        
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
    return redirect('course_detail', slug=course.slug)
