from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class Book(models.Model):
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='books/thumbnails/', null=True, blank=True, help_text="Book cover image")
    order = models.PositiveIntegerField(default=0)
    is_free_book = models.BooleanField(default=True, help_text="If True, it will appear in the Free Books section")

    class Meta:
        verbose_name_plural = "Books"
        ordering = ['order', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            if not base_slug:
                import uuid
                base_slug = str(uuid.uuid4())[:8]
            
            slug = base_slug
            counter = 1
            while Book.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('book_overview', kwargs={'slug': self.slug})

class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField(help_text="Markdown content is supported.")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            if not base_slug:
                import uuid
                base_slug = str(uuid.uuid4())[:8]
            
            slug = base_slug
            counter = 1
            while Chapter.objects.filter(slug=slug, book=self.book).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.book.title} - {self.title}"

    def get_absolute_url(self):
        return reverse('chapter_detail', kwargs={'book_slug': self.book.slug, 'slug': self.slug})
