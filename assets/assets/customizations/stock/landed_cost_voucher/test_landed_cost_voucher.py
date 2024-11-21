import frappe
from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import TestLandedCostVoucher, make_landed_cost_voucher
from assets.assets.doctype.asset.test_asset import create_asset_category, create_fixed_asset_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	make_purchase_receipt,
)


class AssetsTestLandedCostVoucher(TestLandedCostVoucher):

    def test_asset_lcv(self):
            "Check if LCV for an Asset updates the Assets Gross Purchase Amount correctly."
            frappe.db.set_value(
                "Company", "_Test Company", "capital_work_in_progress_account", "CWIP Account - _TC"
            )

            if not frappe.db.exists("Asset Category", "Computers"):
                create_asset_category()

            if not frappe.db.exists("Item", "Macbook Pro"):
                create_fixed_asset_item()

            pr = make_purchase_receipt(item_code="Macbook Pro", qty=1, rate=50000)

            # check if draft asset was created
            assets = frappe.db.get_all("Asset", filters={"purchase_receipt": pr.name})
            self.assertEqual(len(assets), 1)

            lcv = make_landed_cost_voucher(
                company=pr.company,
                receipt_document_type="Purchase Receipt",
                receipt_document=pr.name,
                charges=80,
                expense_account="Expenses Included In Valuation - _TC",
            )

            lcv.save()
            lcv.submit()

            # lcv updates amount in draft asset
            self.assertEqual(frappe.db.get_value("Asset", assets[0].name, "gross_purchase_amount"), 50080)

            # tear down
            lcv.cancel()
            pr.cancel()