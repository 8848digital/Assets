# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe import _
from erpnext.erpnext.stock.doctype.item.test_item import create_item
from erpnext.erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from frappe.utils import flt, nowdate, nowtime, today ,add_days,now_datetime,get_datetime, getdate,add_months,get_first_day
from erpnext.erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.erpnext.setup.doctype.company.test_company import create_child_company
from assets.assets.doctype.asset.asset import (
	get_asset_account,
	get_asset_value_after_depreciation,
	make_sales_invoice,
)
from assets.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	set_depreciation_settings_in_company,
)
from erpnext.erpnext.assets.doctype.asset_repair.asset_repair import get_repair_cost_for_purchase_invoice
from assets.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
)
from erpnext.erpnext.stock.doctype.item.test_item import make_item
from assets.assets.doctype.asset.test_asset import create_asset_category, create_asset_category_as_test_category

class TestAssetRepair(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		set_depreciation_settings_in_company()
		create_asset_data()
		create_item("_Test Stock Item")
		frappe.db.sql("delete from `tabTax Rule`")
		service_item_creation()
		create_locatin_test()

	def test_asset_status(self):
		date = nowdate()
		purchase_date = add_months(get_first_day(date), -2)

		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date=purchase_date,
			purchase_date=purchase_date,
			expected_value_after_useful_life=10000,
			total_number_of_depreciations=10,
			frequency_of_depreciation=1,
			submit=1,
		)

		si = make_sales_invoice(asset=asset.name, item_code="Macbook Pro", company="_Test Company")
		si.customer = "_Test Customer"
		si.due_date = date
		si.get("items")[0].rate = 25000
		si.insert()
		si.submit()

		asset.reload()
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")
		asset_repair = frappe.new_doc("Asset Repair")
		asset_repair.update({"company": "_Test Company", "asset": asset.name, "asset_name": asset.asset_name})
		self.assertRaises(frappe.ValidationError, asset_repair.save)

	# TC_FA_045
	def test_completed_asset_repair_submit_on_complete_status_TC_FA_045(self):
		if not frappe.db.exists("Asset Category", "Test_Category"):
			create_asset_category_as_test_category(name = "Test_Category")

		company = "_Test Company"
		item_code = "Test_asset_repair_item1"
		asset_name = "Test_asset_maintainance"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			item_data = frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,  # Marking as fixed asset
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}).insert()

		today = nowdate()
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": add_days(today, 1),  # Tomorrow
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": today,  # Today's date
			"calculate_depreciation": 0,
			"opening_accumulated_depreciation": 8000,
			"opening_number_of_booked_depreciations": 8,
			"is_fully_depreciated": 1,
			"maintenance_required": 1,
			"finance_books": [{
				"finance_book": "Test Finance Book 1",  # Dynamic financial year
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": add_days(today, 365),  # One year later
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()

		company = "_Test Company"
		supplier = "_Test Supplier"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = today

		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset,
			"company": company,
			"failure_date": now_datetime(),  # Current date & time
			"completion_date": add_days(now_datetime(), 1),  # Completion date as tomorrow
			"repair_status": "Completed",
		}).insert()
		asset_repair.submit()

	# TC_FA_044
	def test_pending_asset_repair_submit_on_pending_status_TC_FA_044(self):
		if not frappe.db.exists("Asset Category", "Test_Category"):
			create_asset_category_as_test_category(name = "Test_Category")

		company = "_Test Company"
		item_code = "Test_asset_repair_item1"
		asset_name = "Test_asset_maintainance"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,  # Marking as fixed asset
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists
			frappe.get_doc(item_data).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": nowdate(),  # Current date
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": add_days(nowdate(), -1),  # 1 day before current date
			"calculate_depreciation": 0,
			"opening_accumulated_depreciation": 8000,
			"opening_number_of_booked_depreciations": 8,
			"is_fully_depreciated": 1,
			"maintenance_required": 1,
			"finance_books": [{
				"finance_book": f"{getdate('2024-04-01').year}-{getdate('2025-03-31').year}",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": add_days(nowdate(), 60),  # 60 days ahead
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()

		self.assertEqual(target_asset.docstatus, 1)

		supplier = "_Test Supplier"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()

		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset.name,
			"company": company,
			"failure_date": now_datetime(),  # Current date & time
			"completion_date": add_days(now_datetime(), 1),  # 1 day ahead
			"repair_status": "Pending",
		}).insert()

		self.assertEqual(asset_repair.repair_status, "Pending")


	# TC_FA_046
	def test_pending_asset_repair_submit_on_complete_status_TC_FA_046(self):
		if not frappe.db.exists("Asset Category", "Test_Category"):
			create_asset_category_as_test_category(name = "Test_Category")


		company = "_Test Company"
		item_code = "Test_asset_repair_item1"
		asset_name = "Test_asset_maintainance"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,  # Marking as fixed asset
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"

			frappe.get_doc(item_data).insert()

		# Create asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": nowdate(),
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": add_days(nowdate(), -1),
			"calculate_depreciation": 0,
			"opening_accumulated_depreciation": 8000,
			"opening_number_of_booked_depreciations": 8,
			"is_fully_depreciated": 1,
			"maintenance_required": 1,
			"finance_books": [{
				"finance_book": f"{getdate('2024-04-01').year}-{getdate('2025-03-31').year}",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": add_days(nowdate(), 60),
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()

		# Fetch asset document before creating repair entry
		asset_doc = frappe.get_doc("Asset", target_asset.name)

		# Create asset repair entry
		failure_date = now_datetime()
		completion_date = add_days(failure_date, 1)

		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset.name,
			"company": company,
			"failure_date": failure_date,
			"completion_date": completion_date,
			"repair_status": "Pending",
		})

		# Assign asset_doc to asset_repair before insert
		asset_repair.asset_doc = asset_doc
		asset_repair.insert()

		# Assert values
		self.assertEqual(asset_repair.asset, target_asset.name)
		self.assertEqual(asset_repair.company, company)
		self.assertEqual(asset_repair.repair_status, "Pending")
		self.assertEqual(asset_repair.failure_date, failure_date)
		self.assertEqual(asset_repair.completion_date, completion_date)

	# TC_FA_137
	def test_pending_asset_repair_submit_on_complete_status_TC_FA_137(self):
		if not frappe.db.exists("Asset Category", "Test_Category"):
			create_asset_category_as_test_category(name = "Test_Category")

		company = "_Test Company"
		item_code = "Test_asset_repair_item1"
		asset_name = "Test_asset_maintainance"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,  # Marking as fixed asset
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"

			frappe.get_doc(item_data).insert()

		# Create asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": nowdate(),
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": add_days(nowdate(), -1),
			"calculate_depreciation": 0,
			"opening_accumulated_depreciation": 8000,
			"opening_number_of_booked_depreciations": 8,
			"is_fully_depreciated": 1,
			"maintenance_required": 1,
			"finance_books": [{
				"finance_book": f"{getdate('2024-04-01').year}-{getdate('2025-03-31').year}",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": add_days(nowdate(), 60),
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()

		# Fetch asset document before creating repair entry
		asset_doc = frappe.get_doc("Asset", target_asset.name)

		# Create asset repair entry
		failure_date = now_datetime()
		completion_date = add_days(failure_date, 1)

		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset.name,
			"company": company,
			"failure_date": failure_date,
			"completion_date": completion_date,
			"repair_status": "Pending",
		})

		# Assign asset_doc to asset_repair before insert
		asset_repair.asset_doc = asset_doc
		asset_repair.insert()

		# Assert values
		self.assertEqual(asset_repair.asset, target_asset.name)
		self.assertEqual(asset_repair.company, company)
		self.assertEqual(asset_repair.repair_status, "Pending")
		self.assertEqual(asset_repair.failure_date, failure_date)
		self.assertEqual(asset_repair.completion_date, completion_date)


	# TC_FA_138
	def test_completed_asset_repair_submit_on_complete_status_TC_FA_138(self):
		if not frappe.db.exists("Asset Category", "Test_Category"):
			create_asset_category_as_test_category(name = "Test_Category")

		company = "_Test Company"
		item_code = "Test_asset_repair_item1"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,  # Marking as fixed asset
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

			frappe.get_doc(item_data).insert()

		# Create Asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": nowdate(),  # Dynamic current date
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": nowdate(),
			"calculate_depreciation": 0,
			"opening_accumulated_depreciation": 8000,
			"opening_number_of_booked_depreciations": 8,
			"is_fully_depreciated": 1,
			"maintenance_required": 1,
			"finance_books": [{
				"finance_book": f"{getdate('2024-04-01').year}-{getdate('2025-03-31').year}",				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": add_days(now_datetime(), 365),  # One year later
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()

		# Fetch the asset document explicitly to avoid 'asset_doc' attribute error
		target_asset = frappe.get_doc("Asset", target_asset.name)

		# Define dynamic failure and completion dates
		failure_date = get_datetime(add_days(now_datetime(), 5))  # 5 days later
		completion_date = get_datetime(add_days(now_datetime(), 6))  # 6 days later

		# Create Asset Repair
		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset.name,
			"company": company,
			"failure_date": failure_date,
			"completion_date": completion_date,
			"repair_status": "Completed",
		})

		# Explicitly link the asset document before submission
		asset_repair.asset_doc = target_asset

		asset_repair.insert()
		asset_repair.submit()

		# Assertions to validate the values
		self.assertEqual(asset_repair.asset, target_asset.name)
		self.assertEqual(asset_repair.company, company)
		self.assertEqual(asset_repair.repair_status, "Completed")
		self.assertEqual(str(asset_repair.failure_date), str(failure_date))  # Ensure dates match
		self.assertEqual(str(asset_repair.completion_date), str(completion_date))

	# TC_FA_139
	def test_service_item_asset_repair_submit_on_complete_status_TC_FA_139(self):
		item_code = "Test_asset1"
		company = "_Test Company"
		location = "Test"
		supplier = "_Test Supplier"
		warehouse = "Cost of Goods Sold - _TC"

		# Ensure required Warehouse exists
		if not frappe.db.exists("Warehouse", {"warehouse_name": "Cost of Goods Sold - _TIRC", "company": "_Test Indian Registered Company"}):
			frappe.get_doc({
				"doctype": "Warehouse",
				"warehouse_name": "Cost of Goods Sold - _TIRC",
				"company": "_Test Indian Registered Company"
			}).insert()

		# Ensure required Company and Location exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Location", "Test Location"):
			frappe.get_doc({"doctype": "Location", "location_name": location}).insert()

		# Ensure the Item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_fixed_asset": 1,
				"is_stock_item": 0,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		# Create Purchase Invoice
		purchase_invoice = frappe.new_doc("Purchase Invoice")
		purchase_invoice.company = company
		purchase_invoice.supplier = supplier
		purchase_invoice.posting_date = nowdate()  # Dynamic date
		purchase_invoice.append("items", {
			"item_code": "Test Service Item",
			"qty": 1,
			"rate": 5000
		})
		purchase_invoice.submit()

		# Define dynamic dates
		purchase_date = add_days(nowdate(), -30)  # Purchase date 30 days before today
		depreciation_start_date = purchase_date  # Ensure it's not earlier than purchase_date

		# Create Asset
		grouped_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": location,
			"is_existing_asset": 1,
			"available_for_use_date": purchase_date,  # Same as purchase date
			"gross_purchase_amount": "12000",
			"asset_quantity": 5,
			"purchase_date": purchase_date,  # Dynamic date
			"calculate_depreciation": 1,
			"finance_books": [{
				"finance_book": "Test Finance Book 1",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"salvage_value_percentage": 10,
				"depreciation_start_date": depreciation_start_date  # Same as purchase_date
			}]
		}).insert()
		grouped_asset.submit()

		# Create Asset Repair
		repair_asset = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": grouped_asset.name,
			"company": company,
			"cost_center": "Main - _TC",
			"failure_date": nowdate(),  # Dynamic date
			"repair_status": "Completed",
			"capitalize_repair_cost": 1,
			"increase_in_asset_life": 12
		})

		# Assign asset_doc before submission to avoid AttributeError
		repair_asset.asset_doc = frappe.get_doc("Asset", repair_asset.asset)

		repair_asset.append("invoices", {
			"purchase_invoice": purchase_invoice.name,
			"expense_account": warehouse,
			"repair_cost": 5000
		})
		repair_asset.insert()
		repair_asset.submit()

	def test_capitalize_repair_cost_asset_repair_submit_on_complete_status_TC_FA_140(self):
		from assets.assets.doctype.asset.test_asset import create_fixed_asset_item , create_asset_category_as_test_category
		from erpnext.erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		create_asset_category_as_test_category("Computers")
		item_code = create_fixed_asset_item(item_code=None, auto_create_assets=1, is_grouped_asset=0)
		company = "_Test Company"
		location = "Test"
		supplier = "_Test Supplier"
		warehouse = "_Test Warehouse - _TC"

		# Ensure required Warehouse exists
		warehouse = create_warehouse(warehouse_name="_Test Warehouse - _TC", company="_Test Company")

		# Create Purchase Invoice
		purchase_invoice = frappe.new_doc("Purchase Invoice")
		purchase_invoice.company = company
		purchase_invoice.supplier = supplier
		purchase_invoice.update_stock = 1
		purchase_invoice.posting_date = nowdate()  # Dynamic date
		purchase_invoice.append("items", {
			"item_code": "Macbook Pro",
			"qty": 100,
			"rate": 5000,
			"asset_location": location,
			"expense_account":"CWIP Account - _TC"
		})
		purchase_invoice.submit()

		# Define dynamic dates
		purchase_date = add_days(nowdate(), -30)  # Purchase date 30 days before today
		depreciation_start_date = purchase_date  # Ensure it's not earlier than purchase_date

		asset_doc =  frappe.db.get_value('Asset', {'purchase_invoice': purchase_invoice.name}, ['name','company', 'item_code', 'asset_category'])
		asset_name = frappe.db.get_value('Asset', {'purchase_invoice': purchase_invoice.name}, 'name')

		if asset_name:
			# Load the Asset doc
			asset_doc = frappe.get_doc('Asset', asset_name)

			# Check if not already submitted
			if asset_doc.docstatus == 0:
				asset_doc.available_for_use_date = purchase_date
				asset_doc.submit()
				frappe.msgprint(_("Asset {0} has been submitted.").format(asset_doc.name))
			else:
				frappe.msgprint(_("Asset {0} is already submitted.").format(asset_doc.name))
		else:
			frappe.msgprint(_("No asset found for this purchase invoice."))


		# Assert Asset Creation
		self.assertEqual(asset_doc.company, '_Test Company')
		self.assertEqual(asset_doc.item_code, "Macbook Pro")
		self.assertEqual(asset_doc.asset_category, "Computers")

		# Create Asset Repair
		repair_asset = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": asset_name,
			"company": company,
			# "cost_center": "Main - _TC",
			"failure_date": nowdate(),  # Dynamic date
			"repair_status": "Completed",
			"capitalize_repair_cost": 1,
			"increase_in_asset_life": 12
		})

		# Assign asset_doc before submission to avoid AttributeError
		repair_asset.asset_doc = frappe.get_doc("Asset", repair_asset.asset)

		repair_asset.append("invoices", {
			"purchase_invoice": purchase_invoice.name,
			"expense_account": "CWIP Account - _TC",
			"repair_cost": 5000
		})
		repair_asset.insert()
		repair_asset.submit()

		# Assert Asset Repair Creation
		self.assertEqual(repair_asset.company, company)
		self.assertEqual(repair_asset.repair_status, "Completed")
		self.assertEqual(repair_asset.increase_in_asset_life, 12)

		# Assert Invoice Link
		self.assertEqual(repair_asset.invoices[0].purchase_invoice, purchase_invoice.name)
		self.assertEqual(repair_asset.invoices[0].repair_cost, 5000)

	def test_stock_acapitalize_repair_and_consumption_cost_asset_repair_TC_FA_142(self):
		from erpnext.erpnext.accounts.doctype.account.test_account import create_account

		if not frappe.db.exists("Asset Category", "Test_Category"):
			create_asset_category_as_test_category(name="Test_Category")

		company = "_Test Company"
		item_code = "Test_asset_nostock_repair_item1"
		asset_name = "Test_asset_maintainance"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the non-stock asset item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"is_purchase_item": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"
			frappe.get_doc(item_data).insert()

		self.assertTrue(frappe.db.exists("Item", item_code))

		# Ensure "Service - _TC" expense account exists
		expense_account = "Service - _TC"
		if not frappe.db.exists("Account", {"name": expense_account, "company": company}):
			create_account(
				account_name="Service",
				parent_account="Expenses - _TC",
				company=company,
				account_type="Expense Account"
			)

		# Dates
		today = nowdate()
		purchase_date = add_days(today, -5)
		available_for_use_date = add_days(today, -3)
		depreciation_start_date = add_days(today, 365)

		# Create Asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": available_for_use_date,
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": purchase_date,
			"calculate_depreciation": 0,
			"opening_accumulated_depreciation": 8000,
			"opening_number_of_booked_depreciations": 8,
			"is_fully_depreciated": 1,
			"maintenance_required": 1,
			"finance_books": [
				{
					"finance_book": "2024-2025",
					"frequency_of_depreciation": 1,
					"depreciation_method": "Straight Line",
					"depreciation_start_date": depreciation_start_date,
					"total_number_of_depreciations": 12,
					"total_number_of_booked_depreciations": 7,
					"value_after_depreciation": 5000,
				}
			]
		}).insert()
		target_asset.submit()

		self.assertEqual(target_asset.company, company)
		self.assertEqual(target_asset.item_code, item_code)
		self.assertEqual(target_asset.asset_quantity, 2)
		self.assertEqual(target_asset.total_asset, 8000)

		# Create Purchase Invoice
		supplier = "_Test Supplier"
		qty, rate = 1, 500
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": supplier,
			"update_stock": 0,
			"posting_date": nowdate(),
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"location": "Test Location",
					"asset_location": "Test Location",
					"expense_account": expense_account,
				}
			]
		})
		pi.insert()
		pi.submit()

		self.assertEqual(pi.items[0].item_code, item_code)
		self.assertEqual(pi.items[0].qty, qty)
		self.assertEqual(pi.items[0].rate, rate)

		# Create Asset Repair
		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset.name,
			"company": company,
			"failure_date": "17-01-2025 14:49:20",
			"completion_date": "17-01-2025 14:52:22",
			"repair_status": "Completed",
			"capitalize_repair_cost": 1,
			"stock_consumption": 1,
			"invoices": [
				{
					"purchase_invoice": pi.name,
					"expense_account": expense_account,
					"repair_cost": 10000,
				}
			]
		}).insert()
		asset_repair.submit()

		self.assertEqual(asset_repair.company, company)
		self.assertEqual(asset_repair.repair_status, "Completed")
		self.assertEqual(asset_repair.capitalize_repair_cost, 1)
		self.assertEqual(asset_repair.stock_consumption, 1)
		self.assertEqual(asset_repair.invoices[0].repair_cost, 10000)


	def test_update_status(self):
		asset = create_asset(submit=1)
		initial_status = asset.status
		asset_repair = create_asset_repair(asset=asset)

		if asset_repair.repair_status == "Pending":
			asset.reload()
			self.assertEqual(asset.status, "Out of Order")

		asset_repair.repair_status = "Completed"
		asset_repair.save()
		asset_status = frappe.db.get_value("Asset", asset_repair.asset, "status")
		self.assertEqual(asset_status, initial_status)

	def test_stock_item_total_value(self):
		asset_repair = create_asset_repair(stock_consumption=1)

		for item in asset_repair.stock_items:
			total_value = flt(item.valuation_rate) * flt(item.consumed_quantity)
			self.assertEqual(item.total_value, total_value)

	def test_total_repair_cost(self):
		asset_repair = create_asset_repair(stock_consumption=1)

		total_repair_cost = asset_repair.repair_cost
		self.assertEqual(total_repair_cost, asset_repair.repair_cost)
		for item in asset_repair.stock_items:
			total_repair_cost += item.total_value

		self.assertEqual(total_repair_cost, asset_repair.total_repair_cost)

	def test_repair_status_after_submit(self):
		asset_repair = create_asset_repair(submit=1)
		self.assertNotEqual(asset_repair.repair_status, "Pending")

	def test_stock_items(self):
		asset_repair = create_asset_repair(stock_consumption=1)
		self.assertTrue(asset_repair.stock_consumption)
		self.assertTrue(asset_repair.stock_items)

	def test_warehouse(self):
		asset_repair = create_asset_repair(stock_consumption=1)
		self.assertTrue(asset_repair.stock_consumption)
		self.assertTrue(asset_repair.stock_items[0].warehouse)

	def test_decrease_stock_quantity(self):
		asset_repair = create_asset_repair(stock_consumption=1, submit=1)
		stock_entry = frappe.get_last_doc("Stock Entry")

		self.assertEqual(stock_entry.stock_entry_type, "Material Issue")
		self.assertEqual(
			stock_entry.items[0].s_warehouse, asset_repair.stock_items[0].warehouse
		)
		self.assertEqual(
			stock_entry.items[0].item_code, asset_repair.stock_items[0].item_code
		)
		self.assertEqual(
			stock_entry.items[0].qty, asset_repair.stock_items[0].consumed_quantity
		)

	def test_serialized_item_consumption(self):
		from erpnext.erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		stock_entry = make_serialized_item()
		bundle_id = stock_entry.get("items")[0].serial_and_batch_bundle
		serial_nos = get_serial_nos_from_bundle(bundle_id)
		serial_no = serial_nos[0]

		# should not raise any error
		create_asset_repair(
			stock_consumption=1,
			item_code=stock_entry.get("items")[0].item_code,
			warehouse="_Test Warehouse - _TC",
			serial_no=[serial_no],
			submit=1,
		)

		# should raise error
		asset_repair = create_asset_repair(
			stock_consumption=1,
			warehouse="_Test Warehouse - _TC",
			item_code=stock_entry.get("items")[0].item_code,
		)

		asset_repair.repair_status = "Completed"
		self.assertRaises(frappe.ValidationError, asset_repair.submit)

	def test_no_increase_in_asset_value_when_not_capitalized(self):
		asset = create_asset(calculate_depreciation=1, submit=1)
		initial_asset_value = get_asset_value_after_depreciation(asset.name)
		create_asset_repair(asset=asset, stock_consumption=1, submit=1)
		asset.reload()

		increase_in_asset_value = (
			get_asset_value_after_depreciation(asset.name) - initial_asset_value
		)
		self.assertEqual(increase_in_asset_value, 0)

	def test_increase_in_asset_value_due_to_repair_cost_capitalisation(self):
		asset = create_asset(calculate_depreciation=1, submit=1)
		initial_asset_value = get_asset_value_after_depreciation(asset.name)
		asset_repair = create_asset_repair(
			asset=asset, capitalize_repair_cost=1, item="Macbook Pro", submit=1, pi_expense_account1 = "CWIP Account - _TC", pi_expense_account2 = "CWIP Account - _TC",
		)
		asset.reload()

		increase_in_asset_value = (
			get_asset_value_after_depreciation(asset.name) - initial_asset_value
		)
		self.assertEqual(asset_repair.repair_cost, increase_in_asset_value)

	def test_purchase_invoice(self):
		asset_repair = create_asset_repair(
			capitalize_repair_cost=1, item="Macbook Pro", submit=1, pi_expense_account1 = "CWIP Account - _TC", pi_expense_account2 = "CWIP Account - _TC",
		)
		self.assertTrue(asset_repair.invoices)

	def test_gl_entries_with_perpetual_inventory(self):
		set_depreciation_settings_in_company(company="_Test Company with perpetual inventory")

		asset_category = frappe.get_doc("Asset Category", "Computers")
		asset_category.append(
			"accounts",
			{
				"company_name": "_Test Company with perpetual inventory",
				"fixed_asset_account": "_Test Fixed Asset - TCP1",
				"accumulated_depreciation_account": "_Test Accumulated Depreciations - TCP1",
				"depreciation_expense_account": "_Test Depreciations - TCP1",
				"capital_work_in_progress_account": "CWIP Account - TCP1",
			},
		)
		asset_category.save()

		asset_repair = create_asset_repair(
			capitalize_repair_cost=1,
			stock_consumption=1,
			warehouse="Stores - TCP1",
			company="_Test Company with perpetual inventory",
			pi_expense_account1="Administrative Expenses - TCP1",
			pi_expense_account2="Legal Expenses - TCP1",
			item="_Test Non Stock Item",
			submit=1,
		)

		gl_entries = frappe.db.sql(
			"""
			select
				account,
				sum(debit) as debit,
				sum(credit) as credit
			from `tabGL Entry`
			where
				voucher_type='Asset Repair'
				and voucher_no=%s
			group by
				account
		""",
			asset_repair.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		fixed_asset_account = get_asset_account(
			"fixed_asset_account", asset=asset_repair.asset, company=asset_repair.company
		)
		pi_expense_accounts = [pi.expense_account for pi in asset_repair.invoices]
		pi_repair_costs = [pi.repair_cost for pi in asset_repair.invoices]
		stock_entry_expense_account = (
			frappe.get_doc("Stock Entry", {"asset_repair": asset_repair.name})
			.get("items")[0]
			.expense_account
		)

		expected_values = {
			fixed_asset_account: [asset_repair.total_repair_cost, 0],
			pi_expense_accounts[0]: [0, pi_repair_costs[0]],
			pi_expense_accounts[1]: [0, pi_repair_costs[1]],
			stock_entry_expense_account: [0, 100],
		}

		for d in gl_entries:
			self.assertEqual(expected_values[d.account][0], d.debit)
			self.assertEqual(expected_values[d.account][1], d.credit)

	def test_gl_entries_with_periodical_inventory(self):
		frappe.db.set_value(
			"Company", "_Test Company", "default_expense_account", "Cost of Goods Sold - _TC"
		)
		asset_repair = create_asset_repair(
			capitalize_repair_cost=1,
			stock_consumption=1,
			item="Macbook Pro",
			submit=1,
			pi_expense_account1 = "CWIP Account - _TC",
			pi_expense_account2 = "CWIP Account - _TC",
		)

		gl_entries = frappe.db.sql(
			"""
			select
				account,
				sum(debit) as debit,
				sum(credit) as credit
			from `tabGL Entry`
			where
				voucher_type='Asset Repair'
				and voucher_no=%s
			group by
				account
		""",
			asset_repair.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		fixed_asset_account = get_asset_account(
			"fixed_asset_account", asset=asset_repair.asset, company=asset_repair.company
		)
		default_expense_account = frappe.get_cached_value(
			"Company", asset_repair.company, "default_expense_account"
		)

		pi_expense_accounts = [pi.expense_account for pi in asset_repair.invoices]

		total_debit = sum(entry['debit'] for entry in gl_entries)
		total_credit = sum(entry['credit'] for entry in gl_entries)

		for d in gl_entries:
			self.assertEqual(total_debit, 650)
			self.assertEqual(total_credit, 650)

	def test_increase_in_asset_life(self):
		asset = create_asset(calculate_depreciation=1, submit=1)
		for row in asset.get("finance_books"):
			first_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active",row.finance_book)
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		initial_num_of_depreciations = num_of_depreciations(asset)
		create_asset_repair(
			asset=asset, capitalize_repair_cost=1, item= "Macbook Pro" , submit=1 , pi_expense_account1 = "CWIP Account - _TC",  pi_expense_account2 =  "CWIP Account - _TC"
		)

		asset.reload()
		first_asset_depr_schedule.load_from_db()

		for row in asset.get("finance_books"):
			second_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active",row.finance_book)
		self.assertEqual(second_asset_depr_schedule.status, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Cancelled")

		self.assertEqual((initial_num_of_depreciations + 1), num_of_depreciations(asset))
		self.assertEqual(
			second_asset_depr_schedule.get("depreciation_schedule")[
				-1
			].accumulated_depreciation_amount,
			asset.finance_books[0].value_after_depreciation,
		)

	def test_asset_repiar_link_in_stock_entry(self):
		asset = create_asset(calculate_depreciation=1, submit=1)
		asset_repair = create_asset_repair(asset=asset, stock_consumption=1, submit=1)
		stock_entry = frappe.get_last_doc("Stock Entry")
		self.assertEqual(stock_entry.asset_repair, asset_repair.name)


def service_item_creation():
	if not frappe.db.exists("Item", "Test Service Item"):
		service_item = make_item("Test Service Item", {
			"is_stock_item": 0,

		})
		service_item.save()

def create_locatin_test():
	if not frappe.db.exists("Location", "Test"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test"}).insert()

	def test_repair_cost_fetches_only_service_item_amount(self):
		"""Test that repair cost only includes service (non-stock) item amounts from purchase invoice."""

		company = "_Test Company with perpetual inventory"
		warehouse = "Stores - TCP1"

		service_item = create_item(
			"_Test Service Item for Repair",
			is_stock_item=0,
			warehouse=warehouse,	
			company=company,
		)

		stock_item = create_item(
			"_Test Stock Item for Repair",
			is_stock_item=1,
			warehouse=warehouse,
			company=company,
		)

		service_expense_account = "Miscellaneous Expenses - TCP1"
		cost_center = frappe.db.get_value("Company", company, "cost_center")

		pi = make_purchase_invoice(
			item_code=service_item.name,
			qty=1,
			rate=500,
			expense_account=service_expense_account,
			cost_center=cost_center,
			warehouse=warehouse,
			update_stock=0,
			do_not_submit=1,
			company=company,
		)

		pi.update_stock = 1
		pi.append(
			"items",
			{
				"item_code": stock_item.name,
				"qty": 2,
				"rate": 300,
				"warehouse": "Stores - TCP1",
				"cost_center": cost_center,
			},
		)
		pi.save()
		pi.submit()

		repair_cost = get_repair_cost_for_purchase_invoice(pi.name)

		self.assertEqual(repair_cost, 500)


def num_of_depreciations(asset):
	return asset.finance_books[0].total_number_of_depreciations


def create_asset_repair(**args):
	from erpnext.erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
		make_purchase_invoice,
	)
	from erpnext.erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

	args = frappe._dict(args)

	if args.asset:
		asset = args.asset
	else:
		asset = create_asset(is_existing_asset=1, submit=1, company=args.company)
	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update(
		{
			"asset": asset.name,
			"asset_name": asset.asset_name,
			"failure_date": nowdate(),
			"description": "Test Description",
			"company": asset.company,
		}
	)

	if args.stock_consumption:
		asset_repair.stock_consumption = 1
		warehouse = args.warehouse or create_warehouse(
			"Test Warehouse", company=asset.company
		)

		bundle = None
		if args.serial_no:
			bundle = make_serial_batch_bundle(
				frappe._dict(
					{
						"item_code": args.item_code,
						"warehouse": warehouse,
						"company": frappe.get_cached_value("Warehouse", warehouse, "company"),
						"qty": (flt(args.stock_qty) or 1) * -1,
						"voucher_type": "Asset Repair",
						"type_of_transaction": "Asset Repair",
						"serial_nos": args.serial_no,
						"posting_date": today(),
						"posting_time": nowtime(),
						"do_not_submit": 1,
					}
				)
			).name

		asset_repair.append(
			"stock_items",
			{
				"item_code": args.item_code or "_Test Stock Item",
				"warehouse": warehouse,
				"valuation_rate": args.rate if args.get("rate") is not None else 100,
				"consumed_quantity": args.qty or 1,
				"serial_and_batch_bundle": bundle,
			},
		)

	asset_repair.insert(ignore_if_duplicate=True)

	if args.submit:
		asset_repair.repair_status = "Completed"
		asset_repair.completion_date = add_days(args.failure_date, 1)
		asset_repair.cost_center = frappe.db.get_value(
			"Company", asset.company, "cost_center"
		)

		if args.stock_consumption:
			stock_entry = frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Receipt",
					"company": asset.company,
				}
			)
			stock_entry.append(
				"items",
				{
					"t_warehouse": asset_repair.stock_items[0].warehouse,
					"item_code": asset_repair.stock_items[0].item_code,
					"qty": asset_repair.stock_items[0].consumed_quantity,
					"basic_rate": args.rate if args.get("rate") is not None else 100,
					"cost_center": asset_repair.cost_center,
				},
			)
			stock_entry.submit()

		if args.capitalize_repair_cost:
			asset_repair.capitalize_repair_cost = 1
			if asset.calculate_depreciation:
				asset_repair.increase_in_asset_life = 12
			pi1 = make_purchase_invoice(
				item=args.item or "_Test Non Stock Item",
				company=asset.company,
				item=args.item or "_Test Item",
				expense_account=args.pi_expense_account1 or "Administrative Expenses - _TC",
				cost_center=asset_repair.cost_center,
				warehouse=args.warehouse
				or create_warehouse("Test Warehouse", company=asset.company),
				rate="50",
			)
			pi2 = make_purchase_invoice(
				company=asset.company,
				item=args.item or "_Test Item",
				expense_account=args.pi_expense_account2 or "Legal Expenses - _TC",
				cost_center=asset_repair.cost_center,
				warehouse=args.warehouse
				or create_warehouse("Test Warehouse", company=asset.company),
				rate="60",
			)
			invoices = [
				{
					"purchase_invoice": pi1.name,
					"expense_account": args.pi_expense_account1 or "Administrative Expenses - _TC",
					"repair_cost": args.pi_repair_cost1 or 250,
				},
				{
					"purchase_invoice": pi2.name,
					"expense_account": args.pi_expense_account2 or "Legal Expenses - _TC",
					"repair_cost": args.pi_repair_cost2 or 300,
				},
			]

			for invoice in invoices:
				asset_repair.append("invoices", invoice)

		asset_repair.submit()
	return asset_repair
