import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

doctype_series_map = {
	"Asset Movement": "ACC-ASM-.YYYY.-.#####",
}


def execute():
	series_to_set = get_series()
	for doctype, opts in series_to_set.items():
		set_series(doctype, opts["value"])


def set_series(doctype, value):
	doc = frappe.db.exists(
		"Property Setter", {"doc_type": doctype, "property": "autoname"}
	)
	if doc:
		frappe.db.set_value("Property Setter", doc, "value", value)
	else:
		make_property_setter(doctype, "", "autoname", value, "", for_doctype=True)


def get_series():
	series_to_set = {}

	for doctype in doctype_series_map:
		if not frappe.db.exists("DocType", doctype):
			continue

		if not frappe.db.a_row_exists(doctype):
			continue

		series_to_preserve = get_series_to_preserve(doctype)
		if not series_to_preserve:
			continue

		# set autoname property setter
		if series_to_preserve:
			series_to_set[doctype] = {"value": series_to_preserve}

	return series_to_set


def get_series_to_preserve(doctype):
	series_to_preserve = frappe.db.get_value("DocType", doctype, "autoname")
	return series_to_preserve
