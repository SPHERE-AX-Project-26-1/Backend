from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('regions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='region',
            name='caution_threshold',
            field=models.IntegerField(default=5),
        ),
        migrations.AddField(
            model_name='region',
            name='danger_threshold',
            field=models.IntegerField(default=10),
        ),
    ]