from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fk_auth_test_app", "0002_align_abstractuser_state")]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="email",
            field=models.EmailField(max_length=254, unique=True, verbose_name="email address"),
        )
    ]
