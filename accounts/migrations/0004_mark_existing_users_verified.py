from django.db import migrations


def mark_existing_verified(apps, schema_editor):
    """Accounts created before email verification existed keep working as before."""
    Profile = apps.get_model('accounts', 'Profile')
    Profile.objects.filter(email_verified=False).update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_email_verification_otp'),
    ]

    operations = [
        migrations.RunPython(mark_existing_verified, migrations.RunPython.noop),
    ]
