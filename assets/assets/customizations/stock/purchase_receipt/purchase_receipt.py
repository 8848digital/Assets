from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from assets.assets.customizations.stock.purchase_receipt.override import make_item_gl_entries, update_assets
from assets.assets.customizations.stock.purchase_receipt.doc_events import validate_cwip_accounts


class AssetsPurchaseReceipt(PurchaseReceipt):
	def make_item_gl_entries(self, gl_entries, warehouse_account=None):
		make_item_gl_entries(self, gl_entries, warehouse_account)

	def update_assets(self, item, valuation_rate):
		update_assets(self, item, valuation_rate)

def validate(doc, method = None):
    validate_cwip_accounts(doc)
