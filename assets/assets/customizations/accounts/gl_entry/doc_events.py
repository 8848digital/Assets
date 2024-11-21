import frappe
from frappe import _
from frappe.utils import cint


def validate_cwip_accounts(doc):
    if not doc.flags.from_repost:
        """Validate that CWIP account are not used in Journal Entry"""
        if doc.voucher_type != "Journal Entry":
            return

        cwip_enabled = any(
            cint(ac.enable_cwip_accounting)
            for ac in frappe.db.get_all("Asset Category", "enable_cwip_accounting")
        )
        if cwip_enabled:
            cwip_accounts = [
                d[0]
                for d in frappe.db.sql(
                    """select name from tabAccount
                where account_type = 'Capital Work in Progress' and is_group=0"""
                )
            ]

            if doc.account in cwip_accounts:
                frappe.throw(
                    _(
                        "Account: <b>{0}</b> is capital Work in progress and can not be updated by Journal Entry"
                    ).format(doc.account)
                )