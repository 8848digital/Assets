import frappe
import os

def execute():
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
            create_module(app_name, module_name)
        
def delete_module(module_name):
    try:
        frappe.delete_doc("Module Def", module_name, force=True, ignore_permissions=True)

        print(f"Successfully deleted the module {module_name}")
    except Exception as e:
        print(f"Error deleting module {module_name}: {str(e)}")

def create_module(app_name, module_name):
    try:
        module_doc = frappe.get_doc({
            "doctype": "Module Def",
            "module_name": module_name,
            "app_name": app_name
        })
        module_doc.insert(ignore_permissions=True)
        print(f"Successfully created the module: {module_name}")
    except Exception as e:
        frappe.log_error(f"Error creating module {module_name}: {str(e)}", "Module Recreate")
        print(f"Error creating module {module_name}: {str(e)}")
