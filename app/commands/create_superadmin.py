import asyncio

import typer

from app.core.db_config import init_db
from app.core.security import hash_password
from app.models import User
from app.models.enums import UserRole


def run(
    email: str = typer.Option(..., prompt="Enter email"),
    password: str = typer.Option(..., prompt=True, hide_input=True),
    first_name: str = typer.Option("Admin", prompt="Enter first name"),
    last_name: str = typer.Option(..., prompt="Enter last name"),
):
    async def create_user():
        # Important: initialise MongoDB + Beanie for CLI
        await init_db()

        existing_user = await User.find_one(User.email == email)

        if existing_user:
            typer.echo(f"User with email {email} already exists.")
            return

        user = User(
            email=email,
            password=await hash_password(password),  # replace with hashed password
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=True,
            role=UserRole.USER,
        )

        await user.insert()
        typer.echo("Super Admin created successfully 🔥")

    asyncio.run(create_user())
