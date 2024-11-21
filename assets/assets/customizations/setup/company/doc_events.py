import frappe
from frappe import _

def set_default_accounts(doc):
    if not frappe.local.flags.ignore_chart_of_accounts:
        default_accounts = {
            "accumulated_depreciation_account": "Accumulated Depreciation",
            "depreciation_expense_account": "Depreciation",
            "capital_work_in_progress_account": "Capital Work in Progress",
            "asset_received_but_not_billed": "Asset Received But Not Billed",
            "expenses_included_in_asset_valuation": "Expenses Included In Asset Valuation"
        }


        if doc.update_default_account:
            for default_account in default_accounts:
                doc._set_default_account(default_account, default_accounts.get(default_account))

        if not doc.disposal_account:
            disposal_acct = frappe.db.get_value(
                "Account",
                {"account_name": _("Gain/Loss on Asset Disposal"), "company": doc.name, "is_group": 0},
            )

            doc.db_set("disposal_account", disposal_acct)

def create_default_cost_center(doc):
    if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": doc.name}):
	    doc.db_set("depreciation_cost_center", _("Main") + " - " + doc.abbr)