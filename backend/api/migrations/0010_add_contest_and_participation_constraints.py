from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_consolidate_contests_and_add_constraints'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='contest',
            constraint=models.UniqueConstraint(
                fields=('platform', 'platform_id'),
                name='unique_contest_platform_and_id'
            ),
        ),
        migrations.AddConstraint(
            model_name='contestparticipation',
            constraint=models.UniqueConstraint(
                condition=models.Q(user__isnull=False),
                fields=('user', 'contest'),
                name='unique_user_contest_participation'
            ),
        ),
        migrations.AddConstraint(
            model_name='contestparticipation',
            constraint=models.UniqueConstraint(
                condition=models.Q(team__isnull=False),
                fields=('team', 'contest'),
                name='unique_team_contest_participation'
            ),
        ),
    ]
