from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from decouple import config


class Command(BaseCommand):
    help = "Set up Google SocialApp using environment variables"

    def handle(self, *args, **options):
        domain = config('SITE_DOMAIN', default='localhost:8000')
        site_name = config('SITE_NAME', default='Arakkha Tech')
        
        # Get or create the Site
        site, created = Site.objects.get_or_create(domain=domain, name=site_name)
        
        # Get Google credentials from environment variables
        client_id = config('GOOGLE_CLIENT_ID', default=None)
        secret_key = config('GOOGLE_CLIENT_SECRET', default=None)
        
        if not client_id or not secret_key:
            self.stdout.write(self.style.WARNING(
                'Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment variables.'
            ))
            return

        # Get or create the SocialApp
        social_app, created = SocialApp.objects.get_or_create(
            provider='google',
            name='Arakkha Tech Google Login',
            defaults={
                'client_id': client_id,
                'secret': secret_key,
            }
        )
        
        if not social_app.sites.filter(id=site.id).exists():
            social_app.sites.add(site)
        
        if created:
            self.stdout.write(self.style.SUCCESS(
                'Successfully created Google SocialApp!'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Google SocialApp already exists! Updated it!'
            ))
