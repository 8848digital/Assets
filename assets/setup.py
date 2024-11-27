import os
import json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields as make_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
import frappe


def after_install():
	create_custom_fields()
	create_property_setter()

def after_migrate():
	create_custom_fields()
	create_property_setter()

def before_uninstall():
	delete_property_setters()
	delete_custom_fields()
	delete_auto_created_custom_fields()


def create_custom_fields():
	CUSTOM_FIELDS = {}
	print("Creating/Updating Custom Fields For Assets....")
	path = os.path.join(os.path.dirname(__file__), "assets/custom_fields")
	for file in os.listdir(path):
		with open(os.path.join(path, file), "r") as f:
			CUSTOM_FIELDS.update(json.load(f))
	make_custom_fields(CUSTOM_FIELDS)

def create_property_setter():
	PROPERTY_SETTERS = {}
	print("Creating/Updating Property Setter For Assets....")
	path = os.path.join(os.path.dirname(__file__), "assets/property_setters")
	for file in os.listdir(path):
		with open(os.path.join(path, file), "r") as f:
			PROPERTY_SETTERS.update(json.load(f))
	for dt, property_setter_list in PROPERTY_SETTERS.items():
		for property_setter in property_setter_list:
			doc = make_property_setter(
                dt,
                property_setter.get("fieldname"),
                property_setter.get("property"),
                property_setter.get("value"),
                property_setter.get("property_type"),
                property_setter.get("for_doctype"),
                property_setter.get("validate_fields_for_doctype"),
            )
			frappe.db.set_value(doc.doctype, doc.name, "module", "Assets")

def delete_property_setters():
	PROPERTY_SETTERS = {}
	print("Removing Property Setters For Assets....")
	path = os.path.join(os.path.dirname(__file__), "assets/property_setters")
	for file in os.listdir(path):
		with open(os.path.join(path, file), "r") as f:
			PROPERTY_SETTERS.update(json.load(f))
	for dt, property_setter_list in PROPERTY_SETTERS.items():
		for property_setter in property_setter_list:
			filters = {
                "doc_type": dt,
                "field_name": property_setter.get("fieldname"),
                "property": property_setter.get("property"),
                "value": property_setter.get("value"),
                "property_type": property_setter.get("property_type"),
                "module": "Assets",
            }
			frappe.db.delete("Property Setter", filters)



def delete_custom_fields():
	CUSTOM_FIELDS = {}
	print("Removing Custom Fields For Assets....")
	path = os.path.join(os.path.dirname(__file__), "assets/custom_fields")
	for file in os.listdir(path):
		with open(os.path.join(path, file), "r") as f:
			CUSTOM_FIELDS.update(json.load(f))
	for doctypes, fields in CUSTOM_FIELDS.items():
		if isinstance(fields, dict):
			# only one field
			fields = [fields]

		if isinstance(doctypes, str):
			# only one doctype
			doctypes = (doctypes,)

		for doctype in doctypes:
			frappe.db.delete(
				"Custom Field",
				{
					"fieldname": ("in", [field["fieldname"] for field in fields]),
					"dt": doctype,
				},
			)
			frappe.clear_cache(doctype=doctype)

def delete_auto_created_custom_fields():
	doctype_list = frappe.get_all("DocType", {"module": "Assets"}, pluck = "name")
	custom_field_list = frappe.get_all("Custom Field",  {"fieldtype": "Link", "options": ["In", doctype_list]}, pluck = "name")
	for custom_field in custom_field_list:
		frappe.db.delete("Custom Field", {"name": custom_field})