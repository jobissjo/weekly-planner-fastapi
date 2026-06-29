import typer

from app.commands import create_superadmin, initial_data, initial_setup, runserver

app = typer.Typer()

app.command("createsuperuser")(create_superadmin.run)
app.command("runserver")(runserver.run)
app.command("initialdata")(initial_data.run)
app.command("initial-setup")(initial_setup.run)

if __name__ == "__main__":
    app()
