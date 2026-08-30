"""
Data migration: populate Course.slug for all existing courses.
Runs after 0011_add_slug_to_course.py (which adds the nullable slug field).
Iterates every course and calls model.save() so that the auto-slug logic
in Course.save() populates slug from title with uniqueness protection.
"""
from django.db import migrations


def populate_course_slugs(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    # We must re-run our slug logic manually here because the historical
    # model in migrations does not include custom save() methods.
    from django.utils.text import slugify as _slugify

    taken = set()
    for course in Course.objects.all().order_by('pk'):
        base = _slugify(course.title, allow_unicode=True) or f"course"
        candidate = base
        i = 2
        while candidate in taken:
            if len(base) > 180:
                base = base[:180]
            candidate = f"{base}-{i}"
            i += 1
        # DB-level safety net: if it somehow already exists, keep looping
        while Course.objects.filter(slug=candidate).exists():
            if len(base) > 180:
                base = base[:180]
            candidate = f"{base}-{i}"
            i += 1
        course.slug = candidate
        taken.add(candidate)
        course.save(update_fields=['slug'])


def reverse_noop(apps, schema_editor):
    # Reverse is no-op since we're just filling a field; no destructive action.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0011_add_slug_to_course'),
    ]

    operations = [
        migrations.RunPython(populate_course_slugs, reverse_code=reverse_noop),
    ]
