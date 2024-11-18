import click

from assets.setup import after_install as setup


def after_install():
	try:
		print("Setting up Frappe Asset...")
		setup()

		click.secho("Thank you for installing Frappe Fixed Asset!", fg="green")

	except Exception as e:
		click.secho(
			"Installation for Frappe Asset app failed due to an error."
			" Please try re-installing the app.",
			fg="bright_red",
		)
		raise e