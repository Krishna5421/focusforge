from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('study', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='studysession',
            name='resource_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
