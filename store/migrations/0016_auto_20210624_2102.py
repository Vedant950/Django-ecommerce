# Generated by Django 3.2.2 on 2021-06-24 15:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0015_alter_items_date_added'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cart',
            options={'verbose_name_plural': 'Order'},
        ),
        migrations.AlterModelOptions(
            name='orderitem',
            options={'verbose_name_plural': 'Cart Items'},
        ),
    ]
