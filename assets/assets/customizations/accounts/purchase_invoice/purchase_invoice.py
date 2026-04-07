from erpnext.erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
    PurchaseInvoice,
)
from assets.assets.customizations.accounts.purchase_invoice.override import (
    set_expense_account,
    check_asset_cwip_enabled,
    make_item_gl_entries,
    update_gross_purchase_amount_for_linked_assets,
)


class AssetsPurchaseInvoice(PurchaseInvoice):
    def set_expense_account(self, for_validate=False):
        set_expense_account(self, for_validate)

    def check_asset_cwip_enabled(self):
        check_asset_cwip_enabled(self)

    def make_item_gl_entries(self, gl_entries):
        make_item_gl_entries(self, gl_entries)

    def update_gross_purchase_amount_for_linked_assets(self, item):
        update_gross_purchase_amount_for_linked_assets(self, item)
