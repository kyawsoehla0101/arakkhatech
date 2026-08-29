import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model, authenticate
from django.db import transaction


User = get_user_model()


class Command(BaseCommand):
    help = (
        'Ensure a Django superuser exists with BOTH is_staff=True AND is_superuser=True '
        'AND Profile.role="admin". Reads credentials from the environment variables: '
        'DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD. '
        'Use DJANGO_SUPERUSER_FORCE=1 to reset the password every deploy. '
        'Designed for Render free tier where shell access is not available: this command '
        'runs automatically on every deploy via render.yaml startCommand.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--username', dest='username', default=None)
        parser.add_argument('--email', dest='email', default=None)
        parser.add_argument('--password', dest='password', default=None)
        parser.add_argument('--force', action='store_true', dest='force',
                            help='Force password + role update every run.')

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _env_truthy(self, key: str) -> bool:
        v = str(os.environ.get(key, '')).strip().lower()
        return v in {'1', 'true', 'yes', 'y', 'on'}

    def _banner(self, text: str):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'[ensure_superuser] {text}'
        ))

    def _db_snapshot(self):
        total = User.objects.count()
        staff = User.objects.filter(is_staff=True).count()
        superusers = User.objects.filter(is_superuser=True).count()
        try:
            from courses.models import Profile
            admin_role = Profile.objects.filter(role='admin').count()
        except Exception:
            admin_role = '?'
        self.stdout.write(
            f'    DB snapshot: users_total={total}, '
            f'is_staff={staff}, is_superuser={superusers}, '
            f'Profile.role=admin={admin_role}'
        )

    def _find_user(self, username: str, email: str):
        """
        Lookup priority (highest first):
          1. exact username match (Django case-sensitive default)
          2. case-insensitive username match
          3. exact email match (env email matches Google signup email)
        Returns (User, reason_str) or (None, None).

        Extra safety: since Django's default User model only enforces
        username uniqueness (NOT email uniqueness), when we find a user
        by email but env username is ALREADY taken by a DIFFERENT user,
        we bail out to avoid a duplicate-key IntegrityError on rename —
        caller will create a fresh user instead.
        """
        # 1) exact username
        try:
            return User.objects.get(username=username), f'exact username="{username}"'
        except User.DoesNotExist:
            pass

        # 2) case-insensitive username
        try:
            u = User.objects.get(username__iexact=username)
            return u, f'case-insensitive username match (env="{username}", db="{u.username}")'
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            pass

        # 3) email (strongest match when user signed up via Google first)
        if email:
            try:
                u = User.objects.get(email__iexact=email)
                # Sanity check: before claiming this user as our target,
                # make sure the env username isn't held by a DIFFERENT user.
                conflict = User.objects.exclude(pk=u.pk).filter(username=username).first()
                if conflict is not None:
                    self.stdout.write(self.style.WARNING(
                        f'    -> Conflict: email matched user "{u.username}" but env username '
                        f'"{username}" is already used by another user (pk={conflict.pk}). '
                        f'Will create a NEW user instead of merging.'
                    ))
                    return None, None
                return u, f'email match (env email="{email}", db username="{u.username}")'
            except User.DoesNotExist:
                pass
            except User.MultipleObjectsReturned:
                self.stdout.write(self.style.WARNING(
                    f'    -> WARNING: Multiple users share email "{email}". '
                    f'Creating a new superuser with username="{username}" instead of merging.'
                ))

        return None, None

    def _ensure_profile_admin(self, user) -> str:
        try:
            from courses.models import Profile
            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={'role': 'admin'},
            )
            if profile.role != 'admin':
                profile.role = 'admin'
                profile.save(update_fields=['role'])
                return 'changed from %r -> "admin"' % (profile.role,)
            return 'already "admin"'
        except Exception as exc:
            return f'error: {type(exc).__name__}: {exc}'

    # ------------------------------------------------------------------
    # main handler
    # ------------------------------------------------------------------
    @transaction.atomic
    def handle(self, *args, **options):
        username = options.get('username') or os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = options.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = options.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        force = bool(options.get('force')) or self._env_truthy('DJANGO_SUPERUSER_FORCE')

        self._banner('=' * 68)
        self.stdout.write('[ensure_superuser] AUTO SUPERUSER ENSURE (Render deploy hook)')
        self.stdout.write(f'    ENV USERNAME : {username or "(NOT SET)"}')
        self.stdout.write(f'    ENV EMAIL    : {email or "(NOT SET -> default username@localhost)"}')
        self.stdout.write(f'    ENV PASSWORD : {"(SET)" if password else "(NOT SET — SKIP)"}')
        self.stdout.write(f'    FORCE RESET  : {"ENABLED (DJANGO_SUPERUSER_FORCE=1)" if force else "disabled"}')
        self._db_snapshot()

        if not username or not password:
            self._banner('MISSING CREDENTIALS — SKIPPED')
            self.stdout.write(self.style.ERROR(
                '   Both DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD must be set '
                'in Render > Service > Environment Variables.'
            ))
            self.stdout.write(
                '   Recommended minimal env vars (copy this block into Render Environment):'
            )
            self.stdout.write('     DJANGO_SUPERUSER_USERNAME = admin')
            self.stdout.write('     DJANGO_SUPERUSER_EMAIL    = your@email.com')
            self.stdout.write('     DJANGO_SUPERUSER_PASSWORD = AVeryStrongPassword_123!')
            self.stdout.write('     DJANGO_SUPERUSER_FORCE    = 1')
            self._banner('=' * 68)
            return

        if not email:
            email = f'{username}@localhost'

        try:
            user, match_reason = self._find_user(username, email)

            # ================================================================
            # BRAND NEW USER — create with FULL admin powers from day 1
            # ================================================================
            if user is None:
                user = User(
                    username=username,
                    email=email,
                    is_active=True,
                    is_staff=True,         # required to even see /admin/login form
                    is_superuser=True,     # required to have ALL permissions (not "staff only")
                )
                user.save()
                user.set_password(password)
                user.save(update_fields=['password'])
                self.stdout.write(self.style.SUCCESS(
                    f'[ensure_superuser] ✅ New user CREATED with full admin powers: '
                    f'username="{user.username}"'
                ))
                role_status = self._ensure_profile_admin(user)
                self.stdout.write(f'    Profile.role       : {role_status}')
                # Reload to guarantee user.profile.role reflects DB state (not cache)
                user.refresh_from_db()
                self._final_verification(user, password, created=True)
                return

            # ================================================================
            # EXISTING USER FOUND — hard upgrade to FULL admin
            # ================================================================
            self.stdout.write(
                f'[ensure_superuser] Found existing user {user.username!r} via {match_reason}.'
            )

            # Username sync: rename to env username so credentials stay consistent across deploys
            if user.username != username:
                old = user.username
                user.username = username
                user.save(update_fields=['username'])
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Username synced: "{old}" -> "{username}"'
                ))

            # Email sync
            if email and user.email.lower() != email.lower():
                user.email = email
                user.save(update_fields=['email'])
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Email synced to "{email}"'
                ))

            # --------------------------------------------------------------
            # CRITICAL: HARD-SET BOTH is_staff=True AND is_superuser=True
            # --------------------------------------------------------------
            # This is what prevents "staff only" empty admin pages.
            # "is_staff = True" alone allows login to /admin but with zero perms
            # unless is_superuser = True (or explicit per-object permissions granted).
            flags_were = (user.is_active, user.is_staff, user.is_superuser)
            user.is_active = True
            user.is_staff = True          # <-- required to access /admin
            user.is_superuser = True      # <-- required to NOT be "staff only"
            flags_now = (user.is_active, user.is_staff, user.is_superuser)
            flags_changed = [f for f, old_val, new_val in zip(
                ('is_active', 'is_staff', 'is_superuser'), flags_were, flags_now
            ) if old_val != new_val]

            # --------------------------------------------------------------
            # Password policy
            # --------------------------------------------------------------
            if force:
                pw_reason = 'FORCE=1 — always refresh password hash with env password.'
                needs_pw = not user.check_password(password)
            elif not user.has_usable_password():
                pw_reason = 'Current password hash is UNUSABLE — auto-repairing.'
                needs_pw = True
            else:
                pw_reason = 'Valid password hash detected (not FORCE mode) — preserving.'
                needs_pw = False

            self.stdout.write(f'    Password policy    : {pw_reason}')

            # Save fields
            save_fields = list(flags_changed)
            if needs_pw:
                user.set_password(password)
                # When password changes, persist it alongside any flag changes
                user.save(update_fields=(save_fields + ['password']) if save_fields else None)
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Password hash UPDATED (using env password).'
                ))
                if flags_changed:
                    self.stdout.write(self.style.SUCCESS(
                        f'    -> Admin flags UPDATED: {", ".join(flags_changed)}'
                    ))
            elif save_fields:
                user.save(update_fields=save_fields)
                self.stdout.write(self.style.SUCCESS(
                    f'    -> Admin flags UPDATED: {", ".join(flags_changed)}'
                ))
            else:
                # No field changes but we still want to guarantee no stale cached state
                user.save(update_fields=['last_login'])  # no-op-ish, refreshes cache
                self.stdout.write(
                    f'    -> No user fields needed changes (flags already correct).'
                )

            # Profile.role = admin — every run
            role_status = self._ensure_profile_admin(user)
            self.stdout.write(f'    Profile.role       : {role_status}')

            # Reload from DB to ensure we read the latest Profile.role
            # (in case get_or_create + save() have cached stale values on the relation)
            user.refresh_from_db()

            # Final summary + inline authenticate() verification
            self._final_verification(user, password, created=False)

        except Exception as exc:
            self._banner('FAILURE')
            self.stdout.write(self.style.ERROR(
                f'    {type(exc).__name__}: {exc}'
            ))
            self.stderr.write(
                '    Troubleshooting checklist:'
                ' (1) Verify DATABASE_URL in Render env points to correct MySQL DB.'
                ' (2) Verify migrations ran (render.yaml startCommand runs migrate before this command).'
                ' (3) Verify mysqlclient or appropriate DB driver is installed.'
            )
            self._banner('=' * 68)

    # ------------------------------------------------------------------
    # final verification block — also prints EXACT login instructions
    # ------------------------------------------------------------------
    def _final_verification(self, user, password, *, created: bool):
        self._banner('FINAL VERIFICATION')

        try:
            from courses.models import Profile
            role = user.profile.role
        except Exception:
            role = 'N/A'

        # Inline Django authenticate() using the env credentials.
        # This is the same call /admin/login/ uses — if it fails here,
        # the user WILL get "Please enter correct username and password..."
        auth_ok = None
        try:
            authed_user = authenticate(username=user.username, password=password)
            auth_ok = (authed_user is not None) and (authed_user.pk == user.pk)
        except Exception as exc:
            auth_ok = f'error: {type(exc).__name__}: {exc}'

        lines = [
            ('Username (EXACT to type)',   user.username),
            ('Email',                      user.email),
            ('is_active    (must be True)', str(user.is_active)),
            ('is_staff     (must be True — otherwise /admin blocked)',  str(user.is_staff)),
            ('is_superuser (must be True — otherwise "staff only" page)', str(user.is_superuser)),
            ('Profile.role (must be "admin" for custom /management views)', role),
        ]
        for label, val in lines:
            self.stdout.write(f'    {label:<55} : {val!r}')

        self.stdout.write('')
        if auth_ok is True:
            self.stdout.write(self.style.SUCCESS(
                '    authenticate() CHECK ✅ PASS — /admin/login/ will accept these credentials.'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'    authenticate() CHECK ❌ FAIL — you WILL NOT be able to log in: {auth_ok!r}'
            ))
            self.stdout.write(self.style.WARNING(
                '    REMEDY: Set DJANGO_SUPERUSER_FORCE=1 in Render Environment, Save changes,'
                ' and let it re-deploy. Then try logging in again.'
            ))

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            '    >>> EXACT LOGIN INSTRUCTIONS <<<'
        ))
        self.stdout.write(f'        Step 1 : Open /admin/login/ — https://your-render-domain.onrender.com/admin/login/')
        self.stdout.write(f'        Step 2 : Do NOT click "Google" / social buttons.')
        self.stdout.write(f'        Step 3 : Username field -> type this EXACTLY: {user.username!r}')
        self.stdout.write( '        Step 4 : Password field -> use the value of env DJANGO_SUPERUSER_PASSWORD.')
        self.stdout.write(f'        Step 5 : If it still says "Please enter correct username and password'
                          f' for a staff account", re-deploy with DJANGO_SUPERUSER_FORCE=1.')
        self._banner('=' * 68)
