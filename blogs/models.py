from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True, db_index=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    thumbnail = models.ImageField(upload_to='blogs/thumbnails/', blank=True, null=True)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or "post"
            candidate = base
            i = 2
            qs = Post.objects.all()
            if self.pk is not None:
                qs = qs.exclude(pk=self.pk)
            while qs.filter(slug=candidate).exists():
                if len(base) > 180:
                    base = base[:180]
                candidate = f"{base}-{i}"
                i += 1
            self.slug = candidate
        super().save(*args, **kwargs)
