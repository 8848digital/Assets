import frappe
from frappe import _

from assets.assets.doctype.asset.depreciation import (
	get_disposal_account_and_cost_center
)

def validate_fixed_asset(doc):
    for d in doc.get("items"):
        if d.is_fixed_asset and d.meta.get_field("asset") and d.asset:
            asset = frappe.get_doc("Asset", d.asset)
            if doc.doctype == "Sales Invoice" and doc.docstatus == 1:
                if doc.update_stock:
                    frappe.throw(_("'Update Stock' cannot be checked for fixed asset sale"))

                elif asset.status in ("Scrapped", "Cancelled", "Capitalized", "Decapitalized") or (
                    asset.status == "Sold" and not doc.is_return
                ):
                    frappe.throw(
                        _("Row #{0}: Asset {1} cannot be submitted, it is already {2}").format(
                            d.idx, d.asset, asset.status
                        )
                    )

def set_income_account_for_fixed_assets(doc):
    disposal_account = depreciation_cost_center = None
    for d in doc.get("items"):
        if d.is_fixed_asset:
            if not disposal_account:
                disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(
                    doc.company
                )

            d.income_account = disposal_account
            if not d.cost_center:
                d.cost_center = depreciation_cost_center