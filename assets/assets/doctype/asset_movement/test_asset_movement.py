# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	make_purchase_receipt,
)
from frappe.utils import now

from assets.assets.doctype.asset.test_asset import create_asset_data
from assets.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
)
from erpnext.setup.doctype.company.test_company import create_child_company
from frappe.utils import cstr, flt
from frappe.query_builder import DocType
from assets.assets.doctype.asset_movement.asset_movement import (
	make_asset_movement_entry,
)


class TestAssetMovement(unittest.TestCase):

	#TC_FA_115
	def test_asset_movement_receipt_location_change_TC_FA_115(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":8,
			"purchase_date":"01-04-2024",
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

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Transfer",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"target_location":"Field 1",
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	#TC_FA_116
	def test_asset_movement_issue_location_change_TC_FA_116(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":8,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	#TC_FA_117
	def test_asset_movement_issue_from_employee_to_employee_TC_FA_117(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_frm_employe"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":8,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	#TC_FA_118
	def test_asset_movement_issue_from_employee_to_target_location_TC_FA_118(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_target_location"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":8,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Receipt",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"from_employee":employee_doc.name,
					"target_location":"Field 1",
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	#TC_FA_119
	def test_asset_movement_transfer_location_change_TC_FA_119(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		# Create and submit the asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Create and submit the asset movement
		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Transfer",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_120
	def test_cancel_asset_movement_issue_location_change_TC_FA_120(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_121
	def test_cancel_asset_movement_issue_from_employee_to_employee_TC_FA_121(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_frm_employe"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled
	
	#TC_FA_122
	def test_cancel_asset_movement_issue_from_employee_to_target_location_TC_FA_122(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_target_location"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()
		
		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"custodian": employee_doc.name,
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Receipt",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"from_employee": employee_doc.name,
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled


	# TC_FA_029
	def test_asset_movement_location_transfer_TC_FA_029(self):
		company = "_Test Company"
		item_code = "Test_transfer_item"
		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()
			
		asset_doc_name = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"custodian": employee_doc.name,
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		asset_doc_name.submit()
		frappe.db.commit()
		if asset_doc_name:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Transfer",
				"assets":[{
					"asset":asset_doc_name,
					"source_location":asset_doc_name.location,
					"target_location":"Division 1",
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	#TC_FA_123
	def test_cancel_multiple_asset_movement_transfer_location_change_TC_FA_123(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

			frappe.get_doc(item_data).insert()

		# Create and submit the asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 5,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Create and submit the asset movement
		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Transfer",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled
	
	#TC_FA_124
	def test_cancel_multiple_asset_movement_issue_location_change_TC_FA_124(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_125
	def test_cancel_multiple_asset_movement_issue_from_employee_to_employee_TC_FA_125(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_frm_employe"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled
	
	#TC_FA_126
	def test_cancel_multiple_asset_movement_issue_from_employee_to_target_location_TC_FA_126(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_target_location"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}
			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

			frappe.get_doc(item_data).insert()
		
		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"custodian": employee_doc.name,
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 5,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Receipt",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"from_employee": employee_doc.name,
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled
	
	#TC_FA_127
	def test_cancel_single_asset_movement_transfer_location_change_TC_FA_127(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

		# Create and submit the asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 5,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Create and submit the asset movement
		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Transfer",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_128
	def test_cancel_single_asset_movement_issue_location_change_TC_FA_128(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_129
	def test_cancel_single_asset_movement_issue_from_employee_to_employee_TC_FA_129(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_frm_employe"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_130
	def test_cancel_single_asset_movement_issue_from_employee_to_target_location_TC_FA_130(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_target_location"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}
			
			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"custodian": employee_doc.name,
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 5,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Receipt",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"from_employee": employee_doc.name,
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_131
	def test_cancel_multiple_grouped_asset_movement_transfer_location_change_TC_FA_131(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

			frappe.get_doc(item_data).insert()

		# Create and submit the asset
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 5,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Create and submit the asset movement
		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Transfer",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled
	
	#TC_FA_132
	def test_cancel_multiple_grouped_asset_movement_issue_location_change_TC_FA_132(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_transfer"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled

	#TC_FA_133
	def test_cancel_multiple_grouped_asset_movement_issue_from_employee_to_employee_TC_FA_133(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_frm_employe"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
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
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
					"doctype": "Employee",
					"employee_name": "Test_employee_issue",
					"first_name": "Test_employee_issue",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Issue",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"to_employee":employee_doc.name,
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

			# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled
	
	#TC_FA_134
	def test_cancel_multiple_grouped_asset_movement_issue_from_employee_to_target_location_TC_FA_134(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_target_location"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}
			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

			frappe.get_doc(item_data).insert()
		
		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"custodian": employee_doc.name,
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 5,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Receipt",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Test Location",
					"from_employee": employee_doc.name,
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

		# Cancel associated Asset Movements
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": target_asset.name},
			fields=["name"]
		)
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # If submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Cancel the Asset
		target_asset = frappe.get_doc("Asset", target_asset.name)
		target_asset.cancel()
		frappe.db.commit()

		# Assertions
		self.assertEqual(target_asset.docstatus, 2)  # Ensure Asset is canceled


	# TC_FA_149 - Merge Transfer and Issue Asset Movements with Conditional Cancellation
	def test_multiple_asset_movement_with_purposetype_transfer_issue_149(self):
		company = "_Test Company"
		employees = ["_T-Employee-00001", "_T-Employee-00002"]
		items = ["Test_item_01", "Test_item_02"]
		assets = []

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()

		for emp_id in employees:
			if not frappe.db.exists("Employee", emp_id):
				frappe.get_doc({
					"doctype": "Employee",
					"employee_name": emp_id,
					"first_name": emp_id,
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		for item_code, employee_id in zip(items, employees):
			# Create item if it doesn't exist
			if not frappe.db.exists("Item", item_code):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"gst_hsn_code": "01011010",
					"is_stock_item": 0,
					"is_fixed_asset": 1,
					"auto_create_assets": 1,
					"asset_category": "Test_Category"
				}).insert()

			# Create asset
			asset = frappe.get_doc({
				"doctype": "Asset",
				"company": company,
				"item_code": item_code,
				"asset_name": item_code,
				"asset_category": "Test_Category",
				"location": "Test Location",
				"is_existing_asset": 1,
				"custodian": employee_id,
				"owner": "Company",
				"available_for_use_date": "2024-04-02",
				"gross_purchase_amount": 8000,
				"total_asset": 8000,
				"asset_quantity": 1,
				"purchase_date": "2024-04-01"
			}).insert()
			asset.submit()
			assets.append(asset.name)

		frappe.db.commit()

		# Create Issue Type Asset Movement
		issue_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Issue",
			"assets": [{
				"asset": asset,
				"source_location": "Test Location",
				"to_employee": employee_id,
				"source_cost_center": "_Test Cost Center - _TC"
			} for asset, employee_id in zip(assets, employees)]
		})
		issue_movement.insert()
		issue_movement.submit()
		frappe.db.commit()

		# Cancel the Issue Movement
		issue_movement.cancel()
		frappe.db.commit()

		# Create Transfer Type Asset Movement using the same assets
		transfer_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Transfer",
			"assets": [{
				"asset": asset,
				"source_location": "Test Location",
				"from_employee": employee_id,
				"target_location": "Field 1"
			} for asset, employee_id in zip(assets, employees)]
		})
		transfer_movement.insert()
		transfer_movement.submit()
		frappe.db.commit()

	# TC_FA_150
	def test_single_asset_movement_with_purposetype_transfer_issue_150(self):
		company = "_Test Company"
		employee = "_T-Employee-00001"
		item = "Test_item_01"
		
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Employee", employee):
			frappe.get_doc({
				"doctype": "Employee",
				"employee_name": employee,
				"first_name": employee,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		if not frappe.db.exists("Item", item):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"gst_hsn_code": "01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		# Create a single asset
		asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item,
			"asset_name": item,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"custodian": employee,
			"owner": "Company",
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "2024-04-01"
		}).insert()
		asset.submit()

		frappe.db.commit()

		# Create Issue Type Asset Movement (Single Asset Tagged)
		issue_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Issue",
			"assets": [{
				"asset": asset.name,
				"source_location": "Test Location",
				"to_employee": employee,
				"source_cost_center": "_Test Cost Center - _TC"
			}]
		})
		issue_movement.insert()
		issue_movement.submit()
		frappe.db.commit()

		# Cancel the Issue Movement
		issue_movement.cancel()
		frappe.db.commit()

		# Create Transfer Type Asset Movement (Same Single Asset)
		transfer_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Transfer",
			"assets": [{
				"asset": asset.name,
				"source_location": "Test Location",
				"from_employee": employee,
				"target_location": "Field 1"
			}]
		})
		transfer_movement.insert()
		transfer_movement.submit()
		frappe.db.commit()

	# TC_FA_151
	def test_multiple_asset_movement_with_purposetype_transfer_issue_151(self):
		company = "_Test Company"
		employee = "_T-Employee-00001"
		item = "Test_item_01"
		
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Employee", employee):
			frappe.get_doc({
				"doctype": "Employee",
				"employee_name": employee,
				"first_name": employee,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		if not frappe.db.exists("Item", item):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"gst_hsn_code": "01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		# Create a single asset
		asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item,
			"asset_name": item,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"custodian": employee,
			"owner": "Company",
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "2024-04-01"
		}).insert()
		asset.submit()

		frappe.db.commit()

		# Create Issue Type Asset Movement (Single Asset Tagged)
		issue_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Issue",
			"assets": [{
				"asset": asset.name,
				"source_location": "Test Location",
				"to_employee": employee,
				"source_cost_center": "_Test Cost Center - _TC"
			}]
		})
		issue_movement.insert()
		issue_movement.submit()
		frappe.db.commit()

		# Cancel the Issue Movement
		issue_movement.cancel()
		frappe.db.commit()

		# Create Transfer Type Asset Movement (Same Single Asset)
		transfer_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Transfer",
			"assets": [{
				"asset": asset.name,
				"source_location": "Test Location",
				"from_employee": employee,
				"target_location": "Field 1"
			}]
		})
		transfer_movement.insert()
		transfer_movement.submit()
		frappe.db.commit()

		# Cancel the Issue Movement
		transfer_movement.cancel()
		frappe.db.commit()

	# TC_FA_152
	def test_single_asset_movement_with_purposetype_transfer_issue_152(self):
		company = "_Test Company"
		employee = "_T-Employee-00001"
		item = "Test_item_01"

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Employee", employee):
			frappe.get_doc({
				"doctype": "Employee",
				"employee_name": employee,
				"first_name": employee,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		if not frappe.db.exists("Item", item):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"gst_hsn_code": "01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		# Create a single asset
		asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item,
			"asset_name": item,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"custodian": employee,
			"owner": "Company",
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "2024-04-01"
		}).insert()
		asset.submit()
		frappe.db.commit()

		# Create a single asset movement (either Issue or Transfer)
		asset_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Transfer",  # Keeping Transfer, since Issue is being canceled
			"assets": [{
				"asset": asset.name,
				"source_location": "Test Location",
				"from_employee": employee,
				"target_location": "Field 1"
			}]
		})
		asset_movement.insert()
		asset_movement.submit()
		frappe.db.commit()

		# Cancel the movement
		asset_movement.cancel()
		frappe.db.commit()




	# TC_FA_030
	def test_asset_movement_issue_type_TC_FA_030(self):
		company = "_Test Company"
		item_code = "Test_transfer_item"
		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()
			
		asset_doc_name = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"custodian": employee_doc.name,
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		asset_doc_name.submit()
		frappe.db.commit()
		if asset_doc_name:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Transfer",
				"assets":[{
					"asset":asset_doc_name,
					"source_location":asset_doc_name.location,
					"target_location":"Field 1",
					"source_cost_center":"_Test Cost Center - _TC"
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	#TC_FA_031
	def test_asset_movement_receipt_location_change_TC_FA_031(self):
		company = "_Test Company"
		item_code = "Test_item_receipt"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()
		
		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"custodian":employee_doc.name,
			"owner":"Company",
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
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

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Receipt",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"from_employee":employee_doc.name,
					"target_location":"Field 1",
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	# TC_FA_032
	def test_asset_movement_transfer_location_TC_FA_032(self):
		company = "_Test Company"
		items = ["Test_item_transfer_01", "Test_item_transfer_02"]
		employees = ["_T-Employee-00001", "_T-Employee-00001"]  # Related employees
		assets = []

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		for item_code, employee in zip(items, employees):
			# Create item if it doesn't exist
			if not frappe.db.exists("Item", item_code):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"gst_hsn_code":"01011010",
					"is_stock_item": 0,
					"is_fixed_asset": 1,
					"auto_create_assets": 1,
					"asset_category": "Test_Category"
				}).insert()

			# Create asset for the item
			target_asset = frappe.get_doc({
				"doctype": "Asset",
				"company": company,
				"item_code": item_code,
				"asset_name": item_code,
				"asset_category": "Test_Category",
				"location": "Test Location",
				"is_existing_asset": 1,
				"custodian":employee_doc.name,
				"owner":"Company",# Assign the custodian
				"available_for_use_date": "02-04-2024",
				"gross_purchase_amount": 8000,
				"total_asset": 8000,
				"asset_quantity": 1,
				"purchase_date": "01-04-2024",
				"finance_books": [{
					"finance_book": "2024-2025",
					"frequency_of_depreciation": 1,
					"depreciation_method": "Straight Line",
					"depreciation_start_date": "01-06-2025",
					"total_number_of_depreciations": 12,
					"total_number_of_booked_depreciations": 7,
					"value_after_depreciation": 5000
				}]
			}).insert()
			target_asset.submit()
			frappe.db.commit()

			assets.append({
				"asset": target_asset.name,
				"source_location": "Test Location",
				"from_employee": employee_doc.name,  # Match custodian here
				"target_location": "Field 1"
			})

		# Create Asset Movement with all assets
		asset_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Transfer",
			"assets": assets
		})
		asset_movement.insert()
		asset_movement.submit()
		frappe.db.commit()

	# TC_FA_033
	def test_asset_movement_multiple_issue_type_TC_FA_033(self):
		company = "_Test Company"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the employees `_T-Employee-00001` and `_T-Employee-00002` exist
		employees = [
			{"employee_id": "_T-Employee-00001", "first_name": "Test Employee 1"},
			{"employee_id": "_T-Employee-00002", "first_name": "Test Employee 2"}
		]

		for emp in employees:
			if not frappe.db.exists("Employee", emp["employee_id"]):
				frappe.get_doc({
					"doctype": "Employee",
					"employee_name": emp["employee_id"],
					"first_name": emp["first_name"],
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2023-01-01",
					"status": "Active",
					"company": company
				}).insert()

		# Create items and assets
		assets = []
		items = ["Test_item_issue_01", "Test_item_issue_02"]
		for item_code, employee_id in zip(items, ["_T-Employee-00001", "_T-Employee-00002"]):
			if not frappe.db.exists("Item", item_code):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"gst_hsn_code":"01011010",
					"is_stock_item": 0,
					"is_fixed_asset": 1,
					"auto_create_assets": 1,
					"asset_category": "Test_Category"
				}).insert()

			asset = frappe.get_doc({
				"doctype": "Asset",
				"company": company,
				"item_code": item_code,
				"asset_name": item_code,
				"asset_category": "Test_Category",
				"location": "Test Location",
				"is_existing_asset": 1,
				"asset_owner": "Company",
				"custodian": employee_id,  # Use respective employee
				"available_for_use_date": "2024-04-02",
				"gross_purchase_amount": 8000,
				"purchase_date": "2024-04-01"
			}).insert()
			asset.submit()
			assets.append({"name": asset.name, "location": asset.location, "employee_id": employee_id})

		# Create a single Asset Movement for the two assets
		asset_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Issue",
			"assets": [{
				"asset": asset["name"],
				"source_location": asset["location"],
				"to_employee": asset["employee_id"],
				"source_cost_center": "_Test Cost Center - _TC"
			} for asset in assets]
		})
		asset_movement.insert()
		asset_movement.submit()
		frappe.db.commit()

	# TC_FA_034
	def test_asset_movement_multiple_receipt_location_change_TC_FA_034(self):
		company = "_Test Company"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the employees `_T-Employee-00001` and `_T-Employee-00002` exist
		employees = [
			{"employee_id": "_T-Employee-rec-00001", "first_name": "Test Employee Rec 1"},
			{"employee_id": "_T-Employee-rec-00002", "first_name": "Test Employee Rec 2"}
		]

		for emp in employees:
			employe_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": emp["employee_id"],
				"first_name": emp["first_name"],
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()
			employe_doc.submit()
			frappe.db.commit()

		# Create items and assets
		assets = []
		items = ["Test_item_receipt_01", "Test_item_receipt_02"]
		for item_code, employee_id in zip(items, ["_T-Employee-rec-00001", "_T-Employee-rec-00002"]):
			if not frappe.db.exists("Item", item_code):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_code,
					"gst_hsn_code":"01011010",
					"is_stock_item": 0,
					"is_fixed_asset": 1,
					"auto_create_assets": 1,
					"asset_category": "Test_Category"
				}).insert()

			asset = frappe.get_doc({
				"doctype": "Asset",
				"company": company,
				"item_code": item_code,
				"asset_name": item_code,
				"asset_category": "Test_Category",
				"location": "Test Location",
				"is_existing_asset": 1,
				"asset_owner": "Company",
				"custodian": employe_doc.idx,  # Use respective employee
				"available_for_use_date": "2024-04-02",
				"gross_purchase_amount": 8000,
				"purchase_date": "2024-04-01"
			}).insert()
			asset.submit()
			assets.append({"name": asset.name, "location": asset.location, "employee_id": employee_id})

		# Create a single Asset Movement for the two assets
		asset_movement = frappe.get_doc({
			"doctype": "Asset Movement",
			"company": company,
			"purpose": "Receipt",
			"assets": [{
				"asset": asset["name"],
				"source_location": "Test Location",
				"from_employee": employe_doc.idx,
				"target_location": "Field 1",
			} for asset in assets]
		})
		asset_movement.insert()
		asset_movement.submit()
		frappe.db.commit()

	# TC_FA_035
	def test_asset_movement_grouped_asset_transfer_TC_FA_035(self):
		company = "_Test Company"
		item_code = "Test_location_item"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"is_grouped_asset":1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		if not frappe.db.exists("Employee", "Test_employee_issue"):
			employee_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_employee_issue",
				"first_name": "Test_employee_issue",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()

		# Create asset for the item
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"custodian":employee_doc.name,
			"owner":"Company",# Assign the custodian
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 1,
			"purchase_date": "01-04-2024",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "01-06-2025",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		if target_asset:
			# Create an Asset Movement record with the fetched asset name and location
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Transfer",
				"assets": [{
					"asset": target_asset.name,  # Use the fetched asset name
					"source_location": target_asset.location,  # Use the fetched location
					"target_location": "Field 1",
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	# TC_FA_036
	def test_asset_movement_receipt_grouped_location_change_TC_FA_036(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_receipt"
		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item": 0,
				"gst_hsn_code":"01011010",
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()
		
		employe_doc = frappe.get_doc({
				"doctype": "Employee",
				"employee_name": "Test_Employee_Grouped1",
				"first_name": "Test_Employee_Grouped1",
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2023-01-01",
				"status": "Active",
				"company": company
			}).insert()
		
		employe_doc.submit()
		frappe.db.commit()
		
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"asset_owner":"Company",
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount":8000,
			"total_asset":8000,
			"asset_quantity":6,
			"purchase_date":"01-04-2024",
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

		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype":"Asset Movement",
				"company":company,
				"purpose":"Receipt",
				"assets":[{
					"asset":target_asset,
					"source_location":"Test Location",
					"from_employee":employe_doc.idx,
					"target_location":"Field 1",
				}]
			}) 
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	# TC_FA_037
	def test_asset_movement_issue_type_TC_FA_037(self):
		company = "_Test Company"
		item_code = "Test_item_grouped_issue"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Create the item if it doesn't exist
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"asset_category": "Test_Category"
			}).insert()

		# Create the employee document
		employe_doc = frappe.get_doc({
			"doctype": "Employee",
			"employee_name": "Test_Employee_Grouped_issue1",
			"first_name": "Test_Employee_Grouped_issue1",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2023-01-01",
			"status": "Active",
			"company": company
		}).insert()

		# Create the asset document
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"asset_owner": "Company",
			"custodian": employe_doc.name,  # Use the name (primary key) of the Employee document
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 6,
			"purchase_date": "2024-04-01",
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Straight Line",
				"depreciation_start_date": "2025-06-01",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Create the Asset Movement record
		if target_asset:
			asset_movement = frappe.get_doc({
				"doctype": "Asset Movement",
				"company": company,
				"purpose": "Issue",
				"assets": [{
					"asset": target_asset.name,
					"source_location": "Field 1",
					"to_employee": employe_doc.name,  # Use the name (primary key) of the Employee document
					"source_cost_center": "_Test Cost Center - _TC"
				}]
			})
			asset_movement.insert()
			asset_movement.submit()
			frappe.db.commit()

	def setUp(self):
		frappe.db.set_value(
			"Company", "_Test Company", "capital_work_in_progress_account", "CWIP Account - _TC"
		)
		create_asset_data()
		make_location()

	def test_movement(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = "2020-06-06"
		asset.purchase_date = "2020-06-06"
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

		# check asset movement is created
		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location 2"}).insert()

		create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location 2",
				}
			],
			reference_doctype="Purchase Receipt",
			reference_name=pr.name,
		)
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "location"), "Test Location 2"
		)

		movement1 = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location 2",
					"target_location": "Test Location",
				}
			],
			reference_doctype="Purchase Receipt",
			reference_name=pr.name,
		)
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "location"), "Test Location"
		)

		movement1.cancel()
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "location"), "Test Location 2"
		)

		employee = make_employee("testassetmovemp@example.com", company="_Test Company")
		create_asset_movement(
			purpose="Issue",
			company=asset.company,
			assets=[
				{"asset": asset.name, "source_location": "Test Location 2", "to_employee": employee}
			],
			reference_doctype="Purchase Receipt",
			reference_name=pr.name,
		)

		# after issuing, asset should belong to an employee not at a location
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "location"), None)
		self.assertEqual(frappe.db.get_value("Asset", asset.name, "custodian"), employee)

		create_asset_movement(
			purpose="Receipt",
			company=asset.company,
			assets=[
				{"asset": asset.name, "from_employee": employee, "target_location": "Test Location"}
			],
			reference_doctype="Purchase Receipt",
			reference_name=pr.name,
		)

		# after receiving, asset should belong to a location not at an employee
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "location"), "Test Location"
		)

	def test_last_movement_cancellation(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = "2020-06-06"
		asset.purchase_date = "2020-06-06"
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

		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location 2"}).insert()

		movement = frappe.get_doc({"doctype": "Asset Movement", "reference_name": pr.name})
		self.assertRaises(frappe.ValidationError, movement.cancel)

		movement1 = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location 2",
				}
			],
			reference_doctype="Purchase Receipt",
			reference_name=pr.name,
		)
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "location"), "Test Location 2"
		)

		movement1.cancel()
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "location"), "Test Location"
		)

	def test_depriciation_schedule_entry(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro",
			qty=1,
			rate=100000.0,
			location="Test Location",
			posting_date="2020-06-06",
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = "2020-06-06"
		asset.purchase_date = "2020-06-06"
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2021-03-31",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 12,
			},
		)

		if asset.docstatus == 0:
			asset.submit()

		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location 2"}).insert()

		create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			transaction_date="2022-10-22",
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location 2",
				}
			],
		)

		expected_schedules = [
			["2021-03-31", 24575.34, 75424.66, 24575.34],
			["2022-03-31", 30000.00, 45424.66, 54575.34],
			["2022-10-22", 16849.32, 28575.34, 71424.66],
			["2023-03-31", 13150.68, 15424.66, 84575.34],
			["2023-06-06", 5424.66, 10000.00, 90000.00],
		]
		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				flt(d.wdv, 2),
				flt(d.accumulated_depreciation_amount, 2),
			]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_on_cancel_reverse_depriciation_schedule_entry(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro",
			qty=1,
			rate=100000.0,
			location="Test Location",
			posting_date="2020-06-06",
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = "2020-06-06"
		asset.purchase_date = "2020-06-06"
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2021-03-31",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 12,
			},
		)

		if asset.docstatus == 0:
			asset.submit()

		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location 2"}).insert()

		movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			transaction_date="2022-10-22",
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location 2",
				}
			],
		)
		movement.cancel()

		expected_schedules = [
			["2021-03-31", 24575.34, 75424.66, 24575.34],
			["2022-03-31", 30000.00, 45424.66, 54575.34],
			["2023-03-31", 30000.00, 15424.66, 84575.34],
			["2023-06-06", 5424.66, 10000.00, 90000.00],
		]
		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				flt(d.wdv, 2),
				flt(d.accumulated_depreciation_amount, 2),
			]
			for d in get_depr_schedule(asset.name, "Active")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_sequence_cancel_of_asset_movement(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro",
			qty=1,
			rate=100000.0,
			location="Test Location",
			posting_date="2020-06-06",
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = "2020-06-06"
		asset.purchase_date = "2020-06-06"
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2021-03-31",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 12,
			},
		)

		if asset.docstatus == 0:
			asset.submit()

		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location 2"}).insert()

		create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			transaction_date="2022-10-22",
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location 2",
				}
			],
		)

		AssetMovement = DocType("Asset Movement")
		AssetMovementItem = DocType("Asset Movement Item")

		movements = (
			frappe.qb.from_(AssetMovement)
			.join(AssetMovementItem)
			.on(AssetMovementItem.parent == AssetMovement.name)
			.where((AssetMovementItem.asset == asset_name) & (AssetMovement.docstatus == 1))
			.select(AssetMovement.name)
			.orderby(AssetMovement.creation)
		).run()

		movement = frappe.get_doc("Asset Movement", movements[0][0])
		self.assertRaises(frappe.ValidationError, movement.cancel)

	def test_asset_movement_entry(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro",
			qty=1,
			rate=100000.0,
			location="Test Location",
			posting_date="2020-06-06",
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1
		asset.available_for_use_date = "2020-06-06"
		asset.purchase_date = "2020-06-06"
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2021-03-31",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 12,
			},
		)

		if asset.docstatus == 0:
			asset.submit()

		if not frappe.db.exists("Location", "Test Location 2"):
			frappe.get_doc({"doctype": "Location", "location_name": "Test Location 2"}).insert()

		movement1 = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			transaction_date="2022-10-22",
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location 2",
				}
			],
		)
		movement1 = make_asset_movement_entry(
			movement1.name, movement1.transaction_date, asset.company
		)

		expected_gle = (
			("_Test Fixed Asset - _TC", 28575.34, 0.0),
			("_Test Fixed Asset - _TC", 0.0, 28575.34),
		)
		gle = frappe.db.sql(
			"""select account, debit, credit from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			order by account""",
			movement1.journal_entry,
		)

		self.assertSequenceEqual(gle, expected_gle)


def create_asset_movement(**args):
	args = frappe._dict(args)

	if not args.transaction_date:
		args.transaction_date = now()

	movement = frappe.new_doc("Asset Movement")
	movement.update(
		{
			"assets": args.assets,
			"transaction_date": args.transaction_date,
			"company": args.company,
			"purpose": args.purpose or "Receipt",
			"reference_doctype": args.reference_doctype,
			"reference_name": args.reference_name,
		}
	)

	movement.insert()
	movement.submit()

	return movement


def make_location():
	for location in ["Pune", "Mumbai", "Nagpur"]:
		if not frappe.db.exists("Location", location):
			frappe.get_doc({"doctype": "Location", "location_name": location}).insert(
				ignore_permissions=True
			)
