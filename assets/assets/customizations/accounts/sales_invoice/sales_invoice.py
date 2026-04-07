from assets.assets.customizations.accounts.sales_invoice.doc_events import (
    check_n_update_asset_doc, set_income_account_for_fixed_assets, validate_fixed_asset)
from assets.assets.customizations.accounts.sales_invoice.override import make_item_gl_entries
from erpnext.erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class AssetsSalesInvoice(SalesInvoice):
    def make_item_gl_entries(self, gl_entries):
        make_item_gl_entries(self, gl_entries)

def validate(doc, method = None):
    validate_fixed_asset(doc)
    set_income_account_for_fixed_assets(doc)

def on_submit(doc, method =None):
    if method == "on_submit":
        check_n_update_asset_doc(doc)
