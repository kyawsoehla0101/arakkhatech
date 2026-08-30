"""
Data migration — populate Profile.slug for existing instructor accounts
so they have working public profile URLs on /instructor/<slug>/.

Also applies: if an InstructorProfile exists from the (now-removed) prior model
and the target instructor profile lacks public fields, copy them across.
"""
from django.db import migrations


def populate_profile_fields(apps, schema_editor):
    Profile = apps.get_model('courses', 'Profile')
    User = apps.get_model('auth', 'User')

    # Try to map legacy InstructorProfile -> Profile if it still exists in
    # historical models. (Migration 0014 deletes the model, but 0015 runs
    # AFTER 0014 so historical model IS gone -> skip copy gracefully.)
    try:
        InstructorProfile = apps.get_model('courses', 'InstructorProfile')
    except Exception:
        InstructorProfile = None

    if InstructorProfile is not None:
        for ip in InstructorProfile.objects.all().select_related('user'):
            user = ip.user
            profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'instructor'})
            # Don't overwrite user-authored data
            profile.role = 'instructor'
            if not profile.headline and ip.title:
                profile.headline = ip.title[:120]
            elif not profile.headline and ip.tagline:
                profile.headline = ip.tagline[:120]
            if not profile.bio and ip.bio:
                profile.bio = ip.bio[:500]
            if not profile.expertise and ip.expertise:
                # convert newlines to commas and keep 255 chars
                cleaned = ', '.join([x.strip() for x in ip.expertise.replace('\n', ',').split(',') if x.strip()])
                profile.expertise = cleaned[:255]
            if not profile.years_of_experience and ip.years_of_experience:
                profile.years_of_experience = int(ip.years_of_experience)
            if not profile.linkedin_url and ip.linkedin_url:
                profile.linkedin_url = ip.linkedin_url[:255]
            if not profile.github_url and ip.github_url:
                profile.github_url = ip.github_url[:255]
            if not profile.twitter_url and ip.twitter_url:
                profile.twitter_url = ip.twitter_url[:255]
            if not profile.website_url and ip.website_url:
                profile.website_url = ip.website_url[:255]
            if ip.is_featured:
                profile.is_featured = True
            profile.save()

    # Assign slugs to every instructor profile that lacks one
    from django.utils.text import slugify as _slugify

    taken = set()
    instructors = (
        Profile.objects.filter(role='instructor')
        .select_related('user')
        .order_by('pk')
    )
    for p in instructors:
        if p.slug:
            taken.add(p.slug)
            continue
        base = _slugify(p.user.username, allow_unicode=True)
        if not base:
            base = _slugify(p.user.get_full_name(), allow_unicode=True)
        if not base:
            base = 'instructor'
        candidate = base
        i = 2
        while candidate in taken:
            if len(base) > 180:
                base = base[:180]
            candidate = f"{base}-{i}"
            i += 1
        while Profile.objects.filter(slug=candidate).exists():
            if len(base) > 180:
                base = base[:180]
            candidate = f"{base}-{i}"
            i += 1
        p.slug = candidate
        taken.add(candidate)
        p.save(update_fields=['slug'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_extend_profile_instructor_public'),
    ]

    operations = [
        migrations.RunPython(populate_profile_fields, reverse_code=reverse_noop),
    ]
