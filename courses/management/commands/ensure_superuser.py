import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


User = get_user_model()


class Command(BaseCommand):
    help = (
        'Ensure a Django superuser exists. '
        'Credentials are read from environment variables: '
        'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD. '
        'If DJANGO_SUPERUSER_FORCE=1 or --force is passed, the password AND profile.role '
        'are updated every run (useful when you cannot log in after initial deploy).'
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
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help='Force-update password and profile.role even if the user already exists.',
        )

    def _env_truthy(self, key: str) -> bool:
        v = str(os.environ.get(key, '')).strip().lower()
        return v in {'1', 'true', 'yes', 'y', 'on'}

    def _ensure_profile_admin(self, user):
        try:
            from courses.models import Profile
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={'role': 'admin'},
            )
            if profile.role != 'admin':
                profile.role = 'admin'
                profile.save(update_fields=['role'])
                self.stdout.write(self.style.SUCCESS(
                    f'  -> Profile.role upgraded to "admin" for user={user.username}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'  -> Profile.role already "admin" for user={user.username}'
                ))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f'  -> Could not ensure Profile role: {type(exc).__name__}: {exc}'
            ))

    @transaction.atomic
    def handle(self, *args, **options):
        username = options.get('username') or os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = options.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = options.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        force = bool(options.get('force')) or self._env_truthy('DJANGO_SUPERUSER_FORCE')

        self.stdout.write(self.style.MIGRATE_HEADING(
            '[ensure_superuser] Starting (Render deploy hook)...'
        ))
        self.stdout.write(
            f'  DJANGO_SUPERUSER_USERNAME = {username or "(NOT SET)"}'
        )
        self.stdout.write(
            f'  DJANGO_SUPERUSER_EMAIL    = {email or "(NOT SET / default username@localhost)"}'
        )
        self.stdout.write(
            f'  DJANGO_SUPERUSER_PASSWORD = {"(SET)" if password else "(NOT SET — SKIPPING)"}'
        )
        self.stdout.write(
            f'  DJANGO_SUPERUSER_FORCE    = {"YES (force update enabled)" if force else "no"}'
        )

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                '[ensure_superuser] SKIPPED. Set both DJANGO_SUPERUSER_USERNAME and '
                'DJANGO_SUPERUSER_PASSWORD in Render > Environment Variables, then re-deploy.'
            ))
            return

        if not email:
            email = f'{username}@localhost'

        try:
            user, created = User.objects.select_for_update().get_or_create(
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
                    f'[ensure_superuser] ✅ Created NEW superuser: username={username}, email={email}'
                ))
                self._ensure_profile_admin(user)
                return

            # ---------------------------------------------------------------
            # User already exists — ensure flags and optionally force update
            # ---------------------------------------------------------------
            changed_fields = []

            if not user.is_superuser:
                user.is_superuser = True
                changed_fields.append('is_superuser')
            if not user.is_staff:
                user.is_staff = True
                changed_fields.append('is_staff')
            if not user.is_active:
                user.is_active = True
                changed_fields.append('is_active')
            if email and user.email != email:
                user.email = email
                changed_fields.append('email')

            # Password update decision:
            # - If FORCE=1 => always update (user explicitly wants login reset)
            # - Else => only update if the current stored password hash is
            #           clearly unusable (empty password). We do NOT overwrite
            #           an existing valid hash silently unless FORCED.
            needs_password = False
            if force:
                if not user.check_password(password):
                    needs_password = True
                    reason = 'DJANGO_SUPERUSER_FORCE=1 and stored hash does not match new password'
                else:
                    reason = 'DJANGO_SUPERUSER_FORCE=1 but password already matches; skip rehash'
            else:
                unusable = not user.has_usable_password()
                if unusable:
                    needs_password = True
                    reason = 'existing password hash is unusable (auto-fix)'
                else:
                    reason = 'existing password hash is usable; preserve to avoid lock-out'

            self.stdout.write(
                f'  Password policy: {reason}'
            )

            if needs_password:
                user.set_password(password)
                # Do NOT add password to changed_fields here; set_password + save() handles the hash column.
                changed_fields = changed_fields or None  # if no other changes, save() will still be called below
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'  -> Password UPDATED for user={username}'
                ))
            elif changed_fields:
                user.save(update_fields=changed_fields)
                self.stdout.write(self.style.SUCCESS(
                    f'  -> User flags/email UPDATED ({", ".join(changed_fields)})'
                ))
            else:
                self.stdout.write(
                    f'  -> No changes required for user={username}'
                )

            # Ensure Profile.role == 'admin' every run (both normal and FORCE).
            # This prevents: user created via signup -> Profile.role='student'
            #                -> same username used as superuser -> /admin 403
            self._ensure_profile_admin(user)

            self.stdout.write(self.style.SUCCESS(
                f'[ensure_superuser] ✅ Superuser exists and is valid: username={username}, '
                f'is_staff={user.is_staff}, is_superuser={user.is_superuser}, is_active={user.is_active}'
            ))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(
                f'[ensure_superuser] ❌ FAILED: {type(exc).__name__}: {exc}'
            ))
