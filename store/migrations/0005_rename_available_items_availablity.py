# Generated by Django 3.2.2 on 2021-06-22 14:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0004_alter_items_size'),
    ]

    operations = [
        migrations.RenameField(
            model_name='items',
            old_name='available',
            new_name='availablity',
        ),
    ]
