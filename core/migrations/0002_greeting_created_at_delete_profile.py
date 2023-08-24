"""Drop the unused Profile model and timestamp greetings.

``Profile`` was never read or written by any view, serializer or service — it
was registered in the admin and nothing else — and its ``ImageField`` forced a
Pillow dependency that made ``manage.py check`` fail when Pillow was absent.

``Greeting.created_at`` gives the append-only table an ordering key and the
column a retention job would prune on.
"""

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="profile", name="user"),
        migrations.DeleteModel(name="Profile"),
        migrations.AddField(
            model_name="greeting",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="greeting",
            options={"ordering": ("-created_at", "-id")},
        ),
        migrations.AddIndex(
            model_name="greeting",
            index=models.Index(fields=["-created_at"], name="greeting_recent_idx"),
        ),
    ]
