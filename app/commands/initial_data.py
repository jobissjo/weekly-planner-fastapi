import asyncio

import typer

from app.core.db_config import init_db
from app.core.settings import setting
from app.models import EmailSetting, User
from app.models.enums import EmailType


def run():
    async def create_initial_data():
        await init_db()

        if not all(
            [
                setting.EMAIL_TYPE,
                setting.EMAIL_HOST_NAME,
                setting.EMAIL_HOST_PORT,
                setting.EMAIL_HOST_USERNAME,
                setting.EMAIL_HOST_PASSWORD,
            ]
        ):
            typer.echo("Email settings are not configured properly")
            return

        superuser = await User.find_one(User.is_superuser == True)
        if not superuser:
            typer.echo("Superuser not found, first create a superuser")
            return

        # Check if email setting already exists
        existing_email_setting = await EmailSetting.find_one(
            EmailSetting.email == setting.EMAIL_HOST_USERNAME
        )
        if existing_email_setting:
            typer.echo("Email setting data already exists for the superuser")
            return

        try:
            email_type = EmailType(setting.EMAIL_TYPE)
        except ValueError:
            email_type = EmailType.SMTP

        email_setting = EmailSetting(
            email=setting.EMAIL_HOST_USERNAME,
            email_type=email_type,
            host=setting.EMAIL_HOST_NAME,
            port=setting.EMAIL_HOST_PORT,
            password=setting.EMAIL_HOST_PASSWORD,
            is_admin_mail=True,
            is_active=True,
            user=superuser,
        )
        await email_setting.insert()
        typer.echo(
            f"Email setting data created successfully for {superuser.email} ({superuser.first_name})"
        )

    asyncio.run(create_initial_data())
