# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.assets.doctype.asset.test_asset import create_asset, set_depreciation_settings_in_company
from erpnext.assets.report.fixed_asset_register.fixed_asset_register import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestFixedAssetRegister(ERPNextTestSuite):
	def setUp(self):
		set_depreciation_settings_in_company()

	def run_report(self, **extra):
		filters = frappe._dict(company="_Test Company", **extra)
		return execute(filters)[1]

	def test_asset_appears_with_purchase_value(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		row = next(row for row in self.run_report() if row["asset_id"] == asset.name)
		self.assertEqual(row["net_purchase_amount"], 100000)
		self.assertEqual(row["asset_value"], 100000)  # no depreciation yet
		self.assertEqual(row["asset_category"], "Computers")

	def test_asset_value_reduced_by_opening_depreciation(self):
		asset = create_asset(
			item_code="Macbook Pro",
			net_purchase_amount=100000,
			purchase_amount=100000,
			opening_accumulated_depreciation=20000,
			opening_number_of_booked_depreciations=2,
			submit=True,
		)

		row = next(row for row in self.run_report() if row["asset_id"] == asset.name)
		self.assertEqual(row["opening_accumulated_depreciation"], 20000)
		self.assertEqual(row["asset_value"], 80000)  # 100000 - 20000

	def test_status_in_location_filter_shows_active_asset(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		ids = {row["asset_id"] for row in self.run_report(status="In Location")}
		self.assertIn(asset.name, ids)

	def test_asset_category_filter(self):
		asset = create_asset(
			item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True
		)

		ids = {row["asset_id"] for row in self.run_report(asset_category="Computers")}
		self.assertIn(asset.name, ids)

	def test_group_by_asset_category_sums_values(self):
		create_asset(item_code="Macbook Pro", net_purchase_amount=100000, purchase_amount=100000, submit=True)
		create_asset(
			item_code="Macbook Pro",
			asset_name="Macbook Pro 2",
			net_purchase_amount=50000,
			purchase_amount=50000,
			submit=True,
		)

		rows = self.run_report(group_by="Asset Category")
		computers = next(row for row in rows if row["asset_category"] == "Computers")
		self.assertEqual(computers["net_purchase_amount"], 150000)
		self.assertEqual(computers["asset_value"], 150000)