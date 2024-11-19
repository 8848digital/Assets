import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice as make_pi_from_po
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.stock.doctype.item.test_item import create_item

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import TestPurchaseInvoice

class AssetsTestPurchaseInvoice(TestPurchaseInvoice):
	def test_make_pr_and_pi_from_po(self):
			from assets.assets.doctype.asset.test_asset import create_asset_category

			if not frappe.db.exists("Asset Category", "Computers"):
				create_asset_category()

			item = create_item(
				item_code="_Test_Item", is_stock_item=0, is_fixed_asset=1, asset_category="Computers"
			)
			po = create_purchase_order(item_code=item.item_code)
			pr = create_pr_against_po(po.name, 10)
			pi = make_pi_from_po(po.name)
			pi.insert()
			pi.submit()

			pr_gl_entries = frappe.db.sql(
				"""select account, debit, credit
				from `tabGL Entry` where voucher_type='Purchase Receipt' and voucher_no=%s
				order by account asc""",
				pr.name,
				as_dict=1,
			)

			pr_expected_values = [
				["Asset Received But Not Billed - _TC", 0, 5000],
				["CWIP Account - _TC", 5000, 0],
			]

			for i, gle in enumerate(pr_gl_entries):
				self.assertEqual(pr_expected_values[i][0], gle.account)
				self.assertEqual(pr_expected_values[i][1], gle.debit)
				self.assertEqual(pr_expected_values[i][2], gle.credit)

			pi_gl_entries = frappe.db.sql(
				"""select account, debit, credit
				from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
				order by account asc""",
				pi.name,
				as_dict=1,
			)
			pi_expected_values = [
				["Asset Received But Not Billed - _TC", 5000, 0],
				["Creditors - _TC", 0, 5000],
			]

			for i, gle in enumerate(pi_gl_entries):
				self.assertEqual(pi_expected_values[i][0], gle.account)
				self.assertEqual(pi_expected_values[i][1], gle.debit)
				self.assertEqual(pi_expected_values[i][2], gle.credit)