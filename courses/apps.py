from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = 'courses'
    
    def ready(self):
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        from decouple import config
        
        domain = config('SITE_DOMAIN', default='localhost:8000')
        site_name = config('SITE_NAME', default='Arakkha Tech')
        site, _ = Site.objects.get_or_create(domain=domain, name=site_name)
        
        client_id = config('GOOGLE_CLIENT_ID', default=None)
        secret_key = config('GOOGLE_CLIENT_SECRET', default=None)
        
        if client_id and secret_key:
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

