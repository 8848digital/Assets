import frappe
from frappe import _

def validate_main_item(doc):
    """Validates, main Item is not a stock item"""
    if frappe.db.get_value("Item", doc.new_item_code, "is_fixed_asset"):
        frappe.throw(_("Parent Item {0} must not be a Fixed Asset").format(doc.new_item_code))