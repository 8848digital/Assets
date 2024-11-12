from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
import frappe

ASSETS_CUSTOM_FIELDS = {
    "Purchase Receipt Item": [
        {
            "default": "0",
            "fieldname": "is_fixed_asset",
            "fieldtype": "Check",
            "hidden": 1,
            "label": "Is Fixed Asset",
            "no_copy": 1,
            "print_hide": 1,
            "read_only": 1,
            "insert_after": "column_break_40",
        },
        {
            "depends_on": "is_fixed_asset",
            "fieldname": "asset_location",
            "fieldtype": "Link",
            "label": "Asset Location",
            "options": "Location",
            "insert_after": "manufacturer_part_no",
        },
        {
            "depends_on": "is_fixed_asset",
            "fetch_from": "item_code.asset_category",
            "fieldname": "asset_category",
            "fieldtype": "Link",
            "label": "Asset Category",
            "options": "Asset Category",
            "read_only": 1,
            "insert_after": "asset_location",
        },
        {
            "fieldname": "wip_composite_asset",
            "fieldtype": "Link",
            "label": "WIP Composite Asset",
            "options": "Asset",
            "insert_after": "add_serial_batch_bundle",
        },
    ],
    "Purchase Invoice Item": [
        {
            "fieldname": "wip_composite_asset",
            "fieldtype": "Link",
            "label": "WIP Composite Asset",
            "options": "Asset",
            "insert_after": "expense_account",
        },
        {
            "default": "0",
            "fetch_from": "item_code.is_fixed_asset",
            "fieldname": "is_fixed_asset",
            "fieldtype": "Check",
            "hidden": 1,
            "label": "Is Fixed Asset",
            "no_copy": 1,
            "print_hide": 1,
            "read_only": 1,
            "insert_after": "col_break5",
        },
        {
            "depends_on": "is_fixed_asset",
            "fieldname": "asset_location",
            "fieldtype": "Link",
            "label": "Asset Location",
            "options": "Location",
            "insert_after": "is_fixed_asset",
        },
        {
            "depends_on": "is_fixed_asset",
            "fetch_from": "item_code.asset_category",
            "fieldname": "asset_category",
            "fieldtype": "Link",
            "label": "Asset Category",
            "options": "Asset Category",
            "read_only": 1,
            "insert_after": "asset_location",
        },
    ],
    "Purchase Order Item": [
        {
            "fieldname": "wip_composite_asset",
            "fieldtype": "Link",
            "label": "WIP Composite Asset",
            "options": "Asset",
            "insert_after": "column_break_fyqr",
        },
        {
            "default": "0",
            "depends_on": "is_fixed_asset",
            "fetch_from": "item_code.is_fixed_asset",
            "fieldname": "is_fixed_asset",
            "fieldtype": "Check",
            "label": "Is Fixed Asset",
            "read_only": 1,
            "insert_after": "more_info_section_break",
        },
    ],
    "Material Request Item": [
        {
            "fieldname": "wip_composite_asset",
            "fieldtype": "Link",
            "label": "WIP Composite Asset",
            "options": "Asset",
            "insert_after": "column_break_glru",
        },
    ]
}

ASSETS_PROPERTY_SETTERS = {
    "Purchase Invoice Item": [
        {
            "fieldname": "cost_center",
            "property": "depends_on",
            "value": "eval:!doc.is_fixed_asset",
            "property_type": "Text",
			"for_doctype": False,
            "validate_fields_for_doctype": False,
        },
		{
            "fieldname": "batch_no",
            "property": "depends_on",
            "value": "eval:!doc.is_fixed_asset && doc.use_serial_batch_fields === 1 && parent.update_stock === 1",
            "property_type": "Text",
			"for_doctype": False,
            "validate_fields_for_doctype": False,
        },
		{
            "fieldname": "serial_no",
            "property": "depends_on",
            "value": "eval:!doc.is_fixed_asset && doc.use_serial_batch_fields === 1 && parent.update_stock === 1",
            "property_type": "Text",
			"for_doctype": False,
            "validate_fields_for_doctype": False,
        },
		{
            "fieldname": "rejected_serial_no",
            "property": "depends_on",
            "value": "eval:!doc.is_fixed_asset && doc.use_serial_batch_fields === 1 && parent.update_stock === 1",
            "property_type": "Text",
			"for_doctype": False,
            "validate_fields_for_doctype": False,
        },
		{
            "fieldname": "section_break_rqbe",
            "property": "depends_on",
            "value": "eval:!doc.is_fixed_asset && doc.use_serial_batch_fields === 1 && parent.update_stock === 1",
            "property_type": "Text",
			"for_doctype": False,
            "validate_fields_for_doctype": False,
        },
    ],
}

def create_custom_fields_for_assets():
	create_custom_fields(ASSETS_CUSTOM_FIELDS, ignore_validate=True)

def create_property_setter():
	for dt, property_setter_list in ASSETS_PROPERTY_SETTERS.items():
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
	for dt, property_setter_list in ASSETS_PROPERTY_SETTERS.items():
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
	"""
	:param custom_fields: a dict like `{'Customer': [{fieldname: 'test', ...}]}`
	"""

	for doctypes, fields in ASSETS_CUSTOM_FIELDS.items():
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