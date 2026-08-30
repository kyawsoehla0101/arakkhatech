from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True, db_index=True)
    description = models.TextField()
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses_taught')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-populate slug from title (with Burmese/Unicode support fallback via pk)
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or f"course"
            candidate = base
            # Uniqueness loop: if slug collides, append "-2", "-3", etc.
            i = 2
            qs = Course.objects.all()
            if self.pk is not None:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=candidate).exists():
                # If candidate gets too long with suffix, include pk
                if len(base) > 180:
                    base = base[:180]
                pk_hint = self.pk or ''
                candidate = f"{base}-{i}" if not pk_hint else f"{base}-{pk_hint}-{i}"
                i += 1
            self.slug = candidate
        super().save(*args, **kwargs)

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    video_url = models.URLField(blank=True, null=True, help_text="YouTube link (e.g. https://www.youtube.com/watch?v=...)")
    video_file = models.FileField(upload_to='courses/videos/', blank=True, null=True)
    video_poster = models.ImageField(upload_to='courses/posters/', blank=True, null=True, help_text="Video thumbnail image")
    duration = models.CharField(max_length=20, blank=True, null=True, help_text="e.g. 10:25")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def youtube_id(self):
        if self.video_url:
            import re
            pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
            match = re.search(pattern, self.video_url)
            if match:
                return match.group(1)
        return None

class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrolled_students')
    date_enrolled = models.DateTimeField(auto_now_add=True)
    completed_lessons = models.ManyToManyField(Lesson, blank=True, related_name='completed_by_students')

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

    @property
    def progress_percentage(self):
        total_lessons = self.course.lessons.count()
        if total_lessons == 0:
            return 0
        completed_count = self.completed_lessons.count()
        return int((completed_count / total_lessons) * 100)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_admin_notification = models.BooleanField(default=False) # True for Admin Panel, False for Student/Public
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

class CommunityVoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='voices')
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Voice by {self.user.username}"

class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signals to automatically create profile
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def save_or_create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={'role': 'student'})
    else:
        Profile.objects.get_or_create(user=instance, defaults={'role': 'student'})

# ============================================================
# allauth Social Login (Google) Signals
# ============================================================
try:
    from allauth.account.signals import user_signed_up as _allauth_signed_up
    from allauth.socialaccount.signals import pre_social_login as _pre_social_login
except Exception:
    _allauth_signed_up = None
    _pre_social_login = None

if _pre_social_login is not None:
    @receiver(_pre_social_login)
    def social_login_populate_user(request, sociallogin, **kwargs):
        try:
            account = getattr(sociallogin, 'account', None)
            user = getattr(sociallogin, 'user', None)
            if account and user:
                extra = account.extra_data or {}
                if not user.first_name:
                    user.first_name = extra.get('given_name') or extra.get('first_name') or ''
                if not user.last_name:
                    user.last_name = extra.get('family_name') or extra.get('last_name') or ''
                if not user.email and account.provider == 'google':
                    user.email = extra.get('email') or ''
                if not user.username and user.email:
                    try:
                        base = user.email.split('@')[0]
                        candidate = base
                        suffix = 1
                        from django.contrib.auth.models import User as U
                        while U.objects.filter(username=candidate).exists() and getattr(user, 'pk', None) is None:
                            candidate = f"{base}{suffix}"
                            suffix += 1
                        user.username = candidate
                    except Exception:
                        pass
        except Exception:
            pass

if _allauth_signed_up is not None:
    @receiver(_allauth_signed_up)
    def social_signup_ensure_profile(request, user, **kwargs):
        profile, created = Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
        if not created and not profile.role:
            profile.role = 'student'
            profile.save(update_fields=['role'])

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email
