import click

from assets.setup import before_uninstall as remove_customizations


def before_uninstall():
	try:
		print("Removing customizations created by the Frappe Assets app...")
		remove_customizations()

	except Exception as e:
		click.secho(
			"Removing Customizations for Frappe Asset failed due to an error." " Please try again.",
			fg="bright_red",
		)
		raise e

	click.secho("Frappe Asset app customizations have been removed successfully...", fg="green")