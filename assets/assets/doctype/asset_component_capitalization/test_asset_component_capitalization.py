# Copyright (c) 2024, 8848 Digital LLP and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from assets.assets.doctype.asset.test_asset import create_asset_data
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	make_purchase_receipt,
)
from frappe.query_builder import DocType


class TestAssetComponentCapitalization(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value(
			"Company", "_Test Company", "capital_work_in_progress_account", "CWIP Account - _TC"
		)
		create_asset_data()
		make_location()

	def test_gl_entry(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)
		pr1 = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=200000.0, location="Test Location"
		)
		parent_asset = (
			frappe.get_doc(
				{
					"doctype": "Parent Asset",
					"item_code": "Macbook Pro",
					"company": "_Test Company",
				}
			)
			.save()
			.submit()
		)
		asset = create_asset(pr_name=pr.name, parent_asset=parent_asset.name)
		asset1 = create_asset(pr_name=pr1.name, parent_asset=parent_asset.name)
		asset_component_capitalization = create_asset_component_capitalization(
			parent_asset, asset, asset1
		)
		frappe.db.commit()

		gl_entry = DocType("GL Entry")

		gle = (
			frappe.qb.from_(gl_entry)
			.select(gl_entry.account, gl_entry.debit, gl_entry.credit)
			.where(
				(gl_entry.voucher_type == "Asset Component Capitalization")
				& (gl_entry.voucher_no == asset_component_capitalization.name)
			)
			.orderby(gl_entry.account)
		).run()

		expected_gle = (
			("CWIP Account - _TC", 0.0, 300000.0),
			("_Test Fixed Asset - _TC", 300000.0, 0.0),
		)

		self.assertSequenceEqual(gle, expected_gle)


def make_location():
	for location in ["Pune", "Mumbai", "Nagpur"]:
		if not frappe.db.exists("Location", location):
			frappe.get_doc({"doctype": "Location", "location_name": location}).insert(
				ignore_permissions=True
			)


def create_asset(**args):
	asset_name = frappe.db.get_value(
		"Asset", {"purchase_receipt": args.get("pr_name")}, "name"
	)
	asset = frappe.get_doc("Asset", asset_name)
	asset.calculate_depreciation = 1
	asset.available_for_use_date = "2020-06-06"
	asset.purchase_date = "2020-06-06"
	asset.parent_asset = args.get("parent_asset")
	asset.append(
		"finance_books",
		{
			"expected_value_after_useful_life": 10000,
			"next_depreciation_date": "2020-12-31",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 3,
			"frequency_of_depreciation": 10,
		},
	)

	if asset.docstatus == 0:
		asset.submit()
	return asset


def create_asset_component_capitalization(parent_asset, asset1, asset2):
	asset_component_capitalization = (
		frappe.get_doc(
			{
				"doctype": "Asset Component Capitalization",
				"item_code": "Macbook Pro",
				"company": "_Test Company",
				"parent_asset": parent_asset,
				"posting_date": "2022-12-23",
				"component_asset": [
					{
						"asset": asset1.name,
						"asset_name": "Macbook Pro",
						"gross_amount": asset1.get("gross_purchase_amount"),
					},
					{
						"asset": asset2.name,
						"asset_name": "Macbook Pro",
						"gross_amount": asset2.get("gross_purchase_amount"),
					},
				],
			}
		)
		.save()
		.submit()
	)

	return asset_component_capitalization
