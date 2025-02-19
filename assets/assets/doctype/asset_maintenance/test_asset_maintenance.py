# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	make_purchase_receipt,
)
from frappe.utils import add_days, get_last_day, nowdate
from erpnext.setup.doctype.company.test_company import create_child_company
from assets.assets.doctype.asset_maintenance.asset_maintenance import (
	calculate_next_due_date,
)


class TestAssetMaintenance(unittest.TestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		create_asset_data()
		create_maintenance_team()

	# TC_FA_038
	def test_asset_maintenance_creation_planned_TC_FA_038(self):
		company = "_Test Company"
		item_code = "Test_maintain_item"
		asset_name = "Test_asset_maintainance"
		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":0,
			"opening_accumulated_depreciation":8000,
			"opening_number_of_booked_depreciations":8,
			"is_fully_depreciated":1,
			"maintenance_required":1,
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":12,
				"total_number_of_booked_depreciations":7,
				"value_after_depreciation":5000
					}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()
	
		asset_maintenance = frappe.get_doc({
		"doctype": "Asset Maintenance",
		"asset_name":target_asset,
		"asset_category": "Test_Category",
		"company": "_Test Company",
		"item_code": "Test_item_receipt_01",
		"item_name": "Test_item_receipt_01",
		"maintenance_team": "Service team",
		"asset_maintenance_tasks": [{
			"maintenance_task": "Regular Task",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"start_date": "2025-01-15",
			"periodicity": "Weekly",
			"certificate_required": 0,
			"assign_to": "abc@gmail.com",
			"assign_to_name": "ABC",
			"next_due_date": "2025-01-22"
			}]
		})
		asset_maintenance.insert()
		frappe.db.commit()

	# TC_FA_039
	def test_asset_maintenance_creation_overdue_TC_FA_039(self):
		company = "_Test Company"
		item_code = "Test_maintain_item"
		asset_name = "Test_asset_maintainance"
		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":0,
			"opening_accumulated_depreciation":8000,
			"opening_number_of_booked_depreciations":8,
			"is_fully_depreciated":1,
			"maintenance_required":1,
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":12,
				"total_number_of_booked_depreciations":7,
				"value_after_depreciation":5000
					}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()
	
		asset_maintenance = frappe.get_doc({
		"doctype": "Asset Maintenance",
		"asset_name":target_asset,
		"asset_category": "Test_Category",
		"company": "_Test Company",
		"item_code": "Test_item_receipt_01",
		"item_name": "Test_item_receipt_01",
		"maintenance_team": "Service team",
		"asset_maintenance_tasks": [{
		"maintenance_task": "Regular Task",
		"maintenance_type": "Preventive Maintenance",
		"maintenance_status": "Overdue",
		"start_date": "2025-01-15",
		"periodicity": "Weekly",
		"certificate_required": 0,
		"assign_to": "abc@gmail.com",
		"assign_to_name": "ABC",
		"next_due_date": "2025-01-22"
		}]
		})
		asset_maintenance.insert()
		frappe.db.commit()
	
	# TC_FA_040
	def test_asset_maintenance_creation_cancel_TC_FA_040(self):
		company = "_Test Company"
		item_code = "Test_maintain_item"
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
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
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
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":0,
			"opening_accumulated_depreciation":8000,
			"opening_number_of_booked_depreciations":8,
			"is_fully_depreciated":1,
			"maintenance_required":1,
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":12,
				"total_number_of_booked_depreciations":7,
				"value_after_depreciation":5000
					}]
		}).insert()
		target_asset.submit()
	
		asset_maintenance = frappe.get_doc({
		"doctype": "Asset Maintenance",
		"asset_name":target_asset,
		"asset_category": "Test_Category",
		"company": "_Test Company",
		"item_code": "Test_item_receipt_01",
		"item_name": "Test_item_receipt_01",
		"maintenance_team": "Service team",
		"asset_maintenance_tasks": [{
		"maintenance_task": "Regular Task",
		"maintenance_type": "Preventive Maintenance",
		"maintenance_status": "Cancelled",
		"start_date": "2025-01-15",
		"periodicity": "Weekly",
		"certificate_required": 0,
		"assign_to": "abc@gmail.com",
		"assign_to_name": "ABC",
		"next_due_date": "2025-01-22"
		}]
		})
		asset_maintenance.insert()

	# TC_FA_041
	def test_asset_maintenance_creation_planned_quarterly_TC_FA_041(self):
		company = "_Test Company"
		item_code = "Test_maintain_item"
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
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
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
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":0,
			"opening_accumulated_depreciation":8000,
			"opening_number_of_booked_depreciations":8,
			"is_fully_depreciated":1,
			"maintenance_required":1,
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":12,
				"total_number_of_booked_depreciations":7,
				"value_after_depreciation":5000
					}]
		}).insert()
		target_asset.submit()
	
		asset_maintenance = frappe.get_doc({
		"doctype": "Asset Maintenance",
		"asset_name":target_asset,
		"asset_category": "Test_Category",
		"company": "_Test Company",
		"item_code": "Test_item_receipt_01",
		"item_name": "Test_item_receipt_01",
		"maintenance_team": "Service team",
		"asset_maintenance_tasks": [{
			"maintenance_task": "Regular Task",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"start_date": "2025-01-15",
			"periodicity": "Quarterly",
			"certificate_required": 0,
			"assign_to": "abc@gmail.com",
			"assign_to_name": "ABC",
			"next_due_date": "2025-01-22"
			}]
		})
		asset_maintenance.insert()
	
	# TC_FA_042
	def test_asset_maintenance_creation_planned_calibration_TC_FA_042(self):
		company = "_Test Company"
		item_code = "Test_maintain_item"
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
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
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
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":0,
			"opening_accumulated_depreciation":8000,
			"opening_number_of_booked_depreciations":8,
			"is_fully_depreciated":1,
			"maintenance_required":1,
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":12,
				"total_number_of_booked_depreciations":7,
				"value_after_depreciation":5000
					}]
		}).insert()
		target_asset.submit()
	
		asset_maintenance = frappe.get_doc({
		"doctype": "Asset Maintenance",
		"asset_name":target_asset,
		"asset_category": "Test_Category",
		"company": "_Test Company",
		"item_code": "Test_item_receipt_01",
		"item_name": "Test_item_receipt_01",
		"maintenance_team": "Service team",
		"asset_maintenance_tasks": [{
			"maintenance_task": "Regular Task",
			"maintenance_type": "Calibration",
			"maintenance_status": "Planned",
			"start_date": "2025-01-15",
			"periodicity": "Weekly",
			"certificate_required": 0,
			"assign_to": "abc@gmail.com",
			"assign_to_name": "ABC",
			"next_due_date": "2025-01-22"
			}]
		})
		asset_maintenance.insert()

	# TC_FA_043
	def test_asset_maintenance_creation_on_groupeditem_TC_FA_043(self):
		company = "_Test Company"
		item_code = "Test_maintain_item"
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
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
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
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":2,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":0,
			"opening_accumulated_depreciation":8000,
			"opening_number_of_booked_depreciations":8,
			"is_fully_depreciated":1,
			"maintenance_required":1,
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":12,
				"total_number_of_booked_depreciations":7,
				"value_after_depreciation":5000
					}]
		}).insert()
		target_asset.submit()
	
		asset_maintenance = frappe.get_doc({
		"doctype": "Asset Maintenance",
		"asset_name":target_asset,
		"asset_category": "Test_Category",
		"company": "_Test Company",
		"item_code": "Test_item_receipt_01",
		"item_name": "Test_item_receipt_01",
		"maintenance_team": "Service team",
		"asset_maintenance_tasks": [{
			"maintenance_task": "Regular Task",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"start_date": "2025-01-15",
			"periodicity": "Quarterly",
			"certificate_required": 0,
			"assign_to": "abc@gmail.com",
			"assign_to_name": "ABC",
			"next_due_date": "2025-01-22"
			}]
		})
		asset_maintenance.insert()
			
	def test_create_asset_maintenance(self):
		pr = make_purchase_receipt(
			item_code="Photocopier", qty=1, rate=100000.0, location="Test Location"
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		month_end_date = get_last_day(nowdate())

		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset_doc.available_for_use_date = purchase_date
		asset_doc.purchase_date = purchase_date

		asset_doc.calculate_depreciation = 1
		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 10,
				"depreciation_start_date": month_end_date,
			},
		)

		asset_doc.save()

		if not frappe.db.exists("Asset Maintenance", "Photocopier"):
			asset_maintenance = frappe.get_doc(
				{
					"doctype": "Asset Maintenance",
					"asset_name": "Photocopier",
					"maintenance_team": "Team Awesome",
					"company": "_Test Company",
					"asset_maintenance_tasks": get_maintenance_tasks(),
				}
			).insert()

			next_due_date = calculate_next_due_date(nowdate(), "Monthly")
			self.assertEqual(
				asset_maintenance.asset_maintenance_tasks[0].next_due_date, next_due_date
			)

	def test_create_asset_maintenance_log(self):
		if not frappe.db.exists("Asset Maintenance Log", "Photocopier"):
			asset_maintenance_log = frappe.get_doc(
				{
					"doctype": "Asset Maintenance Log",
					"asset_maintenance": "Photocopier",
					"task": "Change Oil",
					"completion_date": add_days(nowdate(), 2),
					"maintenance_status": "Completed",
				}
			).insert()
		asset_maintenance = frappe.get_doc("Asset Maintenance", "Photocopier")
		next_due_date = calculate_next_due_date(
			asset_maintenance_log.completion_date, "Monthly"
		)
		self.assertEqual(
			asset_maintenance.asset_maintenance_tasks[0].next_due_date, next_due_date
		)


def create_asset_data():
	if not frappe.db.exists("Asset Category", "Equipment"):
		create_asset_category()

	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

	if not frappe.db.exists("Item", "Photocopier"):
		meta = frappe.get_meta("Asset")
		naming_series = meta.get_field("naming_series").options
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Photocopier",
				"item_name": "Photocopier",
				"item_group": "All Item Groups",
				"company": "_Test Company",
				"is_fixed_asset": 1,
				"is_stock_item": 0,
				"asset_category": "Equipment",
				"auto_create_assets": 1,
				"asset_naming_series": naming_series,
			}
		).insert()


def create_maintenance_team():
	user_list = ["marcus@abc.com", "thalia@abc.com", "mathias@abc.com"]
	if not frappe.db.exists("Role", "Technician"):
		frappe.get_doc({"doctype": "Role", "role_name": "Technician"}).insert()
	for user in user_list:
		if not frappe.db.get_value("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": user,
					"new_password": "password",
					"roles": [{"doctype": "Has Role", "role": "Technician"}],
				}
			).insert()

	if not frappe.db.exists("Asset Maintenance Team", "Team Awesome"):
		frappe.get_doc(
			{
				"doctype": "Asset Maintenance Team",
				"maintenance_manager": "marcus@abc.com",
				"maintenance_team_name": "Team Awesome",
				"company": "_Test Company",
				"maintenance_team_members": get_maintenance_team(user_list),
			}
		).insert()


def get_maintenance_team(user_list):
	return [
		{"team_member": user, "full_name": user, "maintenance_role": "Technician"}
		for user in user_list[1:]
	]


def get_maintenance_tasks():
	return [
		{
			"maintenance_task": "Change Oil",
			"start_date": nowdate(),
			"periodicity": "Monthly",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"assign_to": "marcus@abc.com",
		},
		{
			"maintenance_task": "Check Gears",
			"start_date": nowdate(),
			"periodicity": "Yearly",
			"maintenance_type": "Calibration",
			"maintenance_status": "Planned",
			"assign_to": "thalia@abc.com",
		},
	]


def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Equipment"
	asset_category.total_number_of_depreciations = 3
	asset_category.frequency_of_depreciation = 3
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
		},
	)
	asset_category.insert()


def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()

	# Enable booking asset depreciation entry automatically
	frappe.db.set_single_value(
		"Accounts Settings", "book_asset_depreciation_entry_automatically", 1
	)
