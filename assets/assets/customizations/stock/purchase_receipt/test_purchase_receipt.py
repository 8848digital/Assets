import frappe
from erpnext.erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
    TestPurchaseReceipt,
    make_purchase_receipt,
)

from erpnext.erpnext.stock.doctype.item.test_item import make_item


class AssetsTestPurchaseReceipt(TestPurchaseReceipt):
    def test_auto_asset_creation(self):
        asset_item = "Test Asset Item"

        if not frappe.db.exists("Item", asset_item):
            asset_category = frappe.get_all("Asset Category")

            if asset_category:
                asset_category = asset_category[0].name

            if not asset_category:
                doc = frappe.get_doc(
                    {
                        "doctype": "Asset Category",
                        "asset_category_name": "Test Asset Category",
                        "depreciation_method": "Straight Line",
                        "total_number_of_depreciations": 12,
                        "frequency_of_depreciation": 1,
                        "accounts": [
                            {
                                "company_name": "_Test Company",
                                "fixed_asset_account": "_Test Fixed Asset - _TC",
                                "accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
                                "depreciation_expense_account": "_Test Depreciations - _TC",
                            }
                        ],
                    }
                ).insert()

                asset_category = doc.name

            item_data = make_item(
                asset_item,
                {
                    "is_stock_item": 0,
                    "stock_uom": "Box",
                    "is_fixed_asset": 1,
                    "auto_create_assets": 1,
                    "asset_category": asset_category,
                    "asset_naming_series": "ABC.###",
                },
            )
            asset_item = item_data.item_code

        pr = make_purchase_receipt(item_code=asset_item, qty=3)
        assets = frappe.db.get_all("Asset", filters={"purchase_receipt": pr.name})

        self.assertEqual(len(assets), 3)

        location = frappe.db.get_value("Asset", assets[0].name, "location")
        self.assertEqual(location, "Test Location")

        pr.cancel()

    def test_purchase_return_with_submitted_asset(self):
        from erpnext.erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
            make_purchase_return,
        )

        pr = make_purchase_receipt(item_code="Test Asset Item", qty=1)

        asset = frappe.get_doc("Asset", {"purchase_receipt": pr.name})
        asset.available_for_use_date = frappe.utils.nowdate()
        asset.gross_purchase_amount = 50.0
        asset.append(
            "finance_books",
            {
                "expected_value_after_useful_life": 10,
                "depreciation_method": "Straight Line",
                "total_number_of_depreciations": 3,
                "frequency_of_depreciation": 1,
            },
        )
        asset.submit()

        pr_return = make_purchase_return(pr.name)
        self.assertRaises(frappe.exceptions.ValidationError, pr_return.submit)

        asset.load_from_db()
        asset.cancel()

        pr_return.submit()

        pr_return.cancel()
        pr.cancel()
