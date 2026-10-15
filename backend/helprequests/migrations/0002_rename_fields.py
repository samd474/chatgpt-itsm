from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("helprequests", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(model_name="helprequestscomment", old_name="requester", new_name="author"),
        migrations.RenameField(model_name="attachment", old_name="HelpRequests", new_name="help_request"),
        migrations.RenameField(model_name="attachment", old_name="file_name", new_name="file"),
    ]
