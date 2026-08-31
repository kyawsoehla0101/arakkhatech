from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0016_contactmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='newslettersubscriber',
            name='confirmed',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='confirmation_token',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='ip_address',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='source',
            field=models.CharField(choices=[('footer', 'Footer Form'), ('cta', 'CTA Section'), ('manual', 'Manual Entry'), ('other', 'Other')], default='footer', max_length=50),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='unsubscribed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='newslettersubscriber',
            name='user_agent',
            field=models.CharField(blank=True, default='', max_length=512),
        ),
        migrations.AlterField(
            model_name='newslettersubscriber',
            name='email',
            field=models.EmailField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='newslettersubscriber',
            name='is_active',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='newslettersubscriber',
            name='subscribed_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
