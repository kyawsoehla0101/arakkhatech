from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = 'courses'
    
    def ready(self):
        import os
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        from decouple import config
        
        render_domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
        if render_domain:
            domain = render_domain
        else:
            domain = config('SITE_DOMAIN', default='localhost:8000')
        
        site_name = config('SITE_NAME', default='Arakkha Tech')
        
        try:
            site, created = Site.objects.get_or_create(
                id=1,
                defaults={'domain': domain, 'name': site_name}
            )
            if not created and (site.domain != domain or site.name != site_name):
                site.domain = domain
                site.name = site_name
                site.save()
        except Exception:
            site = None
        
        client_id = config('GOOGLE_CLIENT_ID', default=None)
        secret_key = config('GOOGLE_CLIENT_SECRET', default=None)
        
        if client_id and secret_key:
            try:
                try:
                    social_app = SocialApp.objects.get(provider='google')
                    social_app.name = 'Arakkha Tech Google Login'
                    social_app.client_id = client_id
                    social_app.secret = secret_key
                    social_app.save()
                except SocialApp.DoesNotExist:
                    social_app = SocialApp.objects.create(
                        provider='google',
                        name='Arakkha Tech Google Login',
                        client_id=client_id,
                        secret=secret_key,
                    )
                    if site:
                        social_app.sites.add(site)
                else:
                    if site and not social_app.sites.filter(id=site.id).exists():
                        social_app.sites.add(site)
            except Exception:
                pass


