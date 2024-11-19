from assets.assets.customizations.accounts.sales_invoice.doc_events import validate_fixed_asset, set_income_account_for_fixed_assets
from assets.assets.customizations.accounts.sales_invoice.override import make_item_gl_entries
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

class AssetsSalesInvoice(SalesInvoice):
    def make_item_gl_entries(self, gl_entries):
        make_item_gl_entries(self, gl_entries)

def validate(doc, method = None):
    validate_fixed_asset(doc)
    set_income_account_for_fixed_assets(doc)
