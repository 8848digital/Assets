import click

from assets.setup import after_install as setup
import frappe
import os

from frappe.installer import _delete_doctypes, _delete_modules


def after_install():
    try:
        print("Setting up Frappe Asset...")
        setup()

        click.secho("Thank you for installing Frappe Asset!", fg="green")

    except Exception as e:
        click.secho(
            "Installation for Frappe Asset app failed due to an error."
            " Please try re-installing the app.",
            fg="bright_red",
        )
        raise e


def before_install():
    app_name = "assets" 
    modules_txt_path = os.path.join(frappe.get_app_path(app_name), "modules.txt")
    if not os.path.exists(modules_txt_path):
        print(f"modules.txt not found in the app directory {app_name}.")
        return
    with open(modules_txt_path, "r") as f:
        modules = f.readlines()
    modules = [module.strip() for module in modules]

    if not modules:
        print(f"No modules listed in modules.txt for the app {app_name}.")
        return

    for module_name in modules:
        if frappe.db.exists("Module Def", module_name):
            print(f"Deleting module {module_name} ")
            delete_module(module_name)
def delete_module(module_name):
    try:
        frappe.delete_doc("Module Def", module_name, force=True, ignore_permissions=True)

        print(f"Successfully deleted the module {module_name}")
    except Exception as e:
        print(f"Error deleting module {module_name}: {str(e)}")