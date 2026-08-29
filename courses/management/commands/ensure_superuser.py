import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


User = get_user_model()


class Command(BaseCommand):
    help = (
        'Ensure a Django superuser exists. '
        'Reads DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD. '
        'Use DJANGO_SUPERUSER_FORCE=1 to reset the password every deploy. '
        'If no user matches USERNAME exactly, a case-insensitive username match or an EMAIL match '
        'will be tried before creating a brand new user (avoids duplicate admin accounts when '
        'the same person has previously signed up via Google / allauth).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', dest='username', default=None,
            help='Superuser username (overrides DJANGO_SUPERUSER_USERNAME)',
        )
        parser.add_argument(
            '--email', dest='email', default=None,
            help='Superuser email (overrides DJANGO_SUPERUSER_EMAIL)',
        )
        parser.add_argument(
            '--password', dest='password', default=None,
            help='Superuser password (overrides DJANGO_SUPERUSER_PASSWORD)',
        )
        parser.add_argument(
            '--force', action='store_true', dest='force',
            help='Force password + role update even if the user already exists.',
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _env_truthy(self, key: str) -> bool:
        v = str(os.environ.get(key, '')).strip().lower()
        return v in {'1', 'true', 'yes', 'y', 'on'}

    def _find_user(self, username: str, email: str):
        """
        Best-effort user lookup in this priority order:
          1. exact username match (case sensitive, Django default)
          2. case-insensitive username match
          3. exact email match
        Returns (User, matched_via_str) or (None, None).
        """
        try:
            return User.objects.get(username=username), 'exact username'
        except User.DoesNotExist:
            pass

        try:
            user = User.objects.get(username__iexact=username)
            return user, f'case-insensitive username match for "{username}"'
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            pass

        if email:
            try:
                user = User.objects.get(email__iexact=email)
                return user, f'email match for "{email}"'
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                pass

        return None, None

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
                    f'    -> Profile.role upgraded to "admin" (user={user.username})'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Profile.role already "admin" (user={user.username})'
                ))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(
                f'    -> Could not ensure Profile role: {type(exc).__name__}: {exc}'
            ))

    # ------------------------------------------------------------------
    # main handler
    # ------------------------------------------------------------------
    @transaction.atomic
    def handle(self, *args, **options):
        username = options.get('username') or os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = options.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = options.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        force = bool(options.get('force')) or self._env_truthy('DJANGO_SUPERUSER_FORCE')

        self.stdout.write(self.style.MIGRATE_HEADING(
            '[ensure_superuser] ================================================================'
        ))
        self.stdout.write('[ensure_superuser] Render deploy auto-superuser hook starting...')
        self.stdout.write(f'    DJANGO_SUPERUSER_USERNAME  = {username or "(NOT SET)"}')
        self.stdout.write(f'    DJANGO_SUPERUSER_EMAIL     = {email or "(NOT SET -> default: username@localhost)"}')
        self.stdout.write(f'    DJANGO_SUPERUSER_PASSWORD  = {"(SET)" if password else "(NOT SET)"}')
        self.stdout.write(f'    DJANGO_SUPERUSER_FORCE     = {"1 — password/role WILL be reset" if force else "0 — preserve existing password hash"}')
        self.stdout.write('')

        if not username or not password:
            self.stdout.write(self.style.ERROR(
                '[ensure_superuser] ❌ MISSING CREDENTIALS. Superuser creation skipped.'
            ))
            self.stdout.write(self.style.WARNING(
                '   -> Go to Render > Service > Environment and set these 3 variables, '
                'then re-deploy with DJANGO_SUPERUSER_FORCE=1:'
            ))
            self.stdout.write('      - DJANGO_SUPERUSER_USERNAME = your_admin_username')
            self.stdout.write('      - DJANGO_SUPERUSER_EMAIL    = your@email.com')
            self.stdout.write('      - DJANGO_SUPERUSER_PASSWORD = A_very_strong_password_123!')
            self.stdout.write('      - DJANGO_SUPERUSER_FORCE    = 1   (set on first deploy, or anytime you want to reset)')
            self.stdout.write(self.style.MIGRATE_HEADING(
                '[ensure_superuser] ================================================================'
            ))
            return

        if not email:
            email = f'{username}@localhost'

        try:
            user, match_reason = self._find_user(username, email)

            if user is None:
                # ----------------------------------------------------------
                # BRAND NEW USER
                # ----------------------------------------------------------
                user = User.objects.create(
                    username=username,
                    email=email,
                    is_superuser=True,
                    is_staff=True,
                    is_active=True,
                )
                user.set_password(password)
                user.save(update_fields=['password'])
                self.stdout.write(self.style.SUCCESS(
                    f'[ensure_superuser] ✅ New superuser CREATED: username="{username}", email="{email}"'
                ))
                self._ensure_profile_admin(user)
                self.stdout.write('')
                self.stdout.write(self.style.MIGRATE_HEADING(
                    '   >>> NOW LOG IN TO /admin USING THESE EXACT CREDENTIALS <<<'
                ))
                self.stdout.write(f'       LOGIN PAGE : /admin/login/')
                self.stdout.write(f'       Username   : {username}')
                self.stdout.write(f'       Password   : (the DJANGO_SUPERUSER_PASSWORD value you set in Render env)')
                self.stdout.write(self.style.WARNING(
                    '       NOTE: Do NOT use the "Google" button from the login form for admin access — '
                    'Google creates a regular student account first.'
                ))
                self.stdout.write(self.style.MIGRATE_HEADING(
                    '[ensure_superuser] ================================================================'
                ))
                return

            # --------------------------------------------------------------
            # EXISTING USER FOUND
            # --------------------------------------------------------------
            self.stdout.write(
                f'[ensure_superuser] Found existing user {user.username!r} via {match_reason}.'
            )

            # Username sync: if we matched by email (or case-insensitive username) but username
            # differs from desired value, update it so the canonical admin identity is stable.
            if user.username != username:
                old_uname = user.username
                user.username = username
                user.save(update_fields=['username'])
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Username updated from "{old_uname}" -> "{username}"'
                ))

            # Flags sync: ALWAYS ensure 3 critical admin flags.
            changed_flags = []
            if not user.is_superuser:
                user.is_superuser = True
                changed_flags.append('is_superuser')
            if not user.is_staff:
                user.is_staff = True
                changed_flags.append('is_staff')
            if not user.is_active:
                user.is_active = True
                changed_flags.append('is_active')

            # Email sync
            if email and user.email.lower() != email.lower():
                user.email = email
                changed_flags.append('email')

            # --------------------------------------------------------------
            # Password update decision
            # --------------------------------------------------------------
            needs_password = False
            if force:
                # Always respect the user's explicit reset request.
                if not user.check_password(password):
                    needs_password = True
                    pw_reason = (
                        'FORCE=1 set and stored hash does not match env password — updating hash.'
                    )
                else:
                    pw_reason = (
                        'FORCE=1 set but password already matches env value — no change needed.'
                    )
            else:
                # No force — only touch the password hash if it's genuinely broken,
                # never overwrite a valid/usable admin password silently.
                if not user.has_usable_password():
                    needs_password = True
                    pw_reason = 'Existing password hash is UNUSABLE — auto-repairing with env password.'
                else:
                    pw_reason = (
                        'Existing password hash is valid — PRESERVING it '
                        '(set DJANGO_SUPERUSER_FORCE=1 to force-reset).'
                    )

            self.stdout.write(f'    -> Password policy: {pw_reason}')

            # Apply any field updates
            if needs_password:
                user.set_password(password)
                if changed_flags:
                    # set_password already marks the field; update_fields plus any other changed.
                    user.save(update_fields=changed_flags + ['password'])
                else:
                    user.save()  # save password-only change
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Password UPDATED (hash refreshed for user={user.username})'
                ))
                if changed_flags:
                    self.stdout.write(self.style.SUCCESS(
                        f'    -> User flags updated too: {", ".join(changed_flags)}'
                    ))
            elif changed_flags:
                user.save(update_fields=changed_flags)
                self.stdout.write(self.style.SUCCESS(
                    f'    -> User fields updated: {", ".join(changed_flags)}'
                ))
            else:
                self.stdout.write(
                    f'    -> No changes to user fields (user={user.username}).'
                )

            # Profile.role always enforced to 'admin' (both normal and force runs).
            self._ensure_profile_admin(user)

            # Final summary — explicit login instructions.
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                f'[ensure_superuser] ✅ Superuser READY: user="{user.username}" '
                f'is_staff={user.is_staff}, is_superuser={user.is_superuser}, is_active={user.is_active}, '
                f'role={getattr(getattr(user, "profile", None), "role", "N/A")!r}'
            ))
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(
                '   >>> LOGIN TO ADMIN WITH THESE EXACT CREDENTIALS <<<'
            ))
            self.stdout.write(f'       URL        : /admin/login/')
            self.stdout.write(f'       Username   : {user.username}')
            self.stdout.write(f'       Password   : (use the value of DJANGO_SUPERUSER_PASSWORD from Render env)')
            self.stdout.write(self.style.WARNING(
                '       IMPORTANT: Use the regular Django username/password fields on the admin '
                'login form — NOT the Google / social-login button. Google login creates a '
                'regular (role=student) account and will NOT give you staff access.'
            ))
            if not force:
                self.stdout.write(self.style.WARNING(
                '       TROUBLESHOOT: If you still see "Please enter the correct username and '
                'password for a staff account", set DJANGO_SUPERUSER_FORCE=1 in Render > Environment, '
                'save, and re-deploy. That force-resets the hash.'
            ))
            self.stdout.write(self.style.MIGRATE_HEADING(
                '[ensure_superuser] ================================================================'
            ))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(
                f'[ensure_superuser] ❌ FAILED: {type(exc).__name__}: {exc}'
            ))
            self.stderr.write(
                '       Troubleshooting tips:'
                ' (a) Ensure DATABASE_URL env var is pointing to the correct Aiven MySQL.'
                ' (b) Ensure mysqlclient package installed (it is in requirements.txt).'
                ' (c) Ensure DB migrations ran: startCommand in render.yaml runs'
                ' "python manage.py migrate --noinput" BEFORE ensure_superuser.'
            )
