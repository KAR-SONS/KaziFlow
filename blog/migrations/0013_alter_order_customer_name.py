# Generated by Django 4.2.23 on 2025-07-03 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0012_orderitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='customer_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
