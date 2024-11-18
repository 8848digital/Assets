from assets.assets.customizations.stock.item.doc_events import validate_fixed_asset, validate_item_type
import frappe

def onload(doc, method = None):
    doc.set_onload("asset_naming_series", get_asset_naming_series())

def validate(doc, method = None):
    validate_item_type(doc)
    validate_fixed_asset(doc)

@frappe.whitelist()
def get_asset_naming_series():
	from assets.assets.doctype.asset.asset import get_asset_naming_series

	return get_asset_naming_series()
