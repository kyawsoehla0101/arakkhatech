import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


User = get_user_model()


class Command(BaseCommand):
    help = (
        'Ensure a Django superuser exists. '
        'Credentials are read from environment variables: '
        'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD. '
        'If the user already exists, the command is a no-op and will NOT overwrite the password.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            dest='username',
            default=None,
            help='Superuser username (overrides DJANGO_SUPERUSER_USERNAME)',
        )
        parser.add_argument(
            '--email',
            dest='email',
            default=None,
            help='Superuser email (overrides DJANGO_SUPERUSER_EMAIL)',
        )
        parser.add_argument(
            '--password',
            dest='password',
            default=None,
            help='Superuser password (overrides DJANGO_SUPERUSER_PASSWORD)',
        )

    def handle(self, *args, **options):
        username = options.get('username') or os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = options.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = options.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                '[ensure_superuser] Skipped: DJANGO_SUPERUSER_USERNAME and '
                'DJANGO_SUPERUSER_PASSWORD environment variables were not provided. '
                'Set these in Render > Environment to enable auto superuser creation.'
            ))
            return

        if not email:
            # Use a sensible default if email is missing, but keep it valid
            email = f'{username}@localhost'

        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_superuser': True,
                    'is_staff': True,
                    'is_active': True,
                },
            )

            if created:
                user.set_password(password)
                user.save(update_fields=['password'])
                self.stdout.write(self.style.SUCCESS(
                    f'[ensure_superuser] Created superuser: username={username}, email={email}'
                ))
            else:
                # User already exists: ensure flags and optionally update email.
                # Do NOT overwrite password (never risk changing an existing admin's password silently).
                needs_save = False
                if not user.is_superuser:
                    user.is_superuser = True
                    needs_save = True
                if not user.is_staff:
                    user.is_staff = True
                    needs_save = True
                if not user.is_active:
                    user.is_active = True
                    needs_save = True
                if email and user.email != email:
                    user.email = email
                    needs_save = True
                if needs_save:
                    user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'[ensure_superuser] Superuser already exists: username={username} (no changes to password)'
                ))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(
                f'[ensure_superuser] Failed to ensure superuser: {type(exc).__name__}: {exc}'
            ))
