from django.apps import AppConfig


class CoursesConfig(AppConfig):
    name = 'courses'
    
    def ready(self):
        import os
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        from decouple import config
        
        # Use Render's RENDER_EXTERNAL_HOSTNAME if available, otherwise SITE_DOMAIN
        render_domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
        if render_domain:
            domain = render_domain
        else:
            domain = config('SITE_DOMAIN', default='localhost:8000')
        
        site_name = config('SITE_NAME', default='Arakkha Tech')
        
        # Get or create site with the correct domain
        site, created = Site.objects.get_or_create(
            id=1,  # Force id 1 to match SITE_ID
            defaults={'domain': domain, 'name': site_name}
        )
        
        # Update the site's domain and name in case they changed
        if not created and (site.domain != domain or site.name != site_name):
            site.domain = domain
            site.name = site_name
            site.save()
        
        # Set up social app
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
            
            # Update credentials if needed
            if social_app.client_id != client_id or social_app.secret != secret_key:
                social_app.client_id = client_id
                social_app.secret = secret_key
                social_app.save()
            
            # Ensure the site is linked
            if not social_app.sites.filter(id=site.id).exists():
                social_app.sites.add(site)


