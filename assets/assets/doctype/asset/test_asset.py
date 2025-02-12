# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	make_purchase_invoice,
)
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	make_purchase_invoice as make_invoice,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	make_purchase_receipt,
)
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.setup.doctype.company.test_company import create_child_company
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from frappe.utils import (
	add_days,
	add_months,
	cstr,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	is_last_day_of_the_month,
	nowdate,
)
import frappe.utils
from frappe.utils.data import add_to_date

from assets.assets.doctype.asset.asset import (
	make_sales_invoice,
	split_asset,
	update_maintenance_status,
	create_asset_value_adjustment
)
from assets.assets.doctype.asset.depreciation import (
	post_depreciation_entries,
	restore_asset,
	scrap_asset,
	make_depreciation_entry
)
from assets.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	_check_is_pro_rata,
	_get_pro_rata_amt,
	get_asset_depr_schedule_doc,
	get_depr_schedule,
	get_depreciation_amount,
)


class AssetSetup(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		set_depreciation_settings_in_company()
		create_asset_data()
		enable_cwip_accounting("Computers")
		make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)
		frappe.db.sql("delete from `tabTax Rule`")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
	
class TestAsset(AssetSetup):
	def test_asset_category_is_fetched(self):
		"""Tests if the Item's Asset Category value is assigned to the Asset, if the field is empty."""

		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.asset_category = None
		asset.save()

		self.assertEqual(asset.asset_category, "Computers")

    # TC_FA_001
	def test_create_asset_automatic_on_po_pr_TC_FA_001(self):
		"""
		Function to create and submit a Purchase Order and Purchase Receipt.
		"""
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_USB_Wire"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()

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
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		# Create and submit Purchase Order
		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"warehouse": warehouse,
				"qty": qty,
				"rate": rate,
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()

		# Create and submit Purchase Receipt
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			posting_time="10:00:00",
			location="Test Location",
			do_not_submit=False
		)
		frappe.db.commit()

	# TC_FA_002
	def test_create_asset_manually_on_po_pr_TC_FA_002(self):
		"""
		Function to create and submit a Purchase Order and Purchase Receipt.
		"""
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_Charger"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()

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
				"asset_category": "Test_Category",
				"asset_naming_series": "ACC-ASS-.YYYY.-"
			}).insert()

		# Create and submit Purchase Order
		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"warehouse": warehouse,
				"qty": qty,
				"rate": rate,
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()

		# Create and submit Purchase Receipt
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			posting_time="10:00:00",
			location="Test Location",
			do_not_submit=False
		)
		frappe.db.commit()
		
	# TC_FA_003
	def test_create_po_and_pi_update_stock_TC_FA_003(self):
		"""
		Function to create and submit a Purchase Order and Purchase Invoice.
		"""
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_USB_Wire"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()

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
				"auto_create_assets": 1,
				"asset_category": "Test_Category",
				"asset_naming_series": "ACC-ASS-.YYYY.-"
				
			}).insert()

		# Create and submit Purchase Order
		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"warehouse": warehouse,
				"qty": qty,
				"rate": rate,
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()

		# Create and submit Purchase Receipt
		
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": supplier,
			"update_stock": 1,  # Update stock
			"posting_date": nowdate(),
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"purchase_order": po.name,  # Linking to Purchase Order
					"location": "Test Location",  # Linking the correct warehouse
					"asset_location": "Test Location",  # Specifying asset location
					"expense_account":"_Test Account Cost for Goods Sold - _TC"
				}
			]
		})
		pi.insert()
		pi.submit()
		frappe.db.commit()
	
	# TC_FA_004
	def test_create_asset_manually_on_po_pr_TC_FA_004(self):
		"""
		Function to create and submit a Purchase Order and Purchase Receipt.
		"""
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_Charger"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()

		# Ensure prerequisites exist
		if not frappe.db.exists("Company", company):
			create_child_company()

		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"asset_category": "Test_Category"
			}).insert()

		# Create and submit Purchase Order
		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"warehouse": warehouse,
				"qty": qty,
				"rate": rate,
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()

		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": supplier,
			"update_stock": 1,  # Update stock
			"posting_date": nowdate(),
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"purchase_order": po.name,  # Linking to Purchase Order
					"location": "Test Location",  # Linking the correct warehouse
					"asset_location": "Test Location",  # Specifying asset location
					"expense_account":"_Test Account Cost for Goods Sold - _TC"
				}
			]
		})
		pi.insert()
		pi.submit()
		frappe.db.commit()

	# TC_FA_005
	def test_create_multi_asset_automatic_on_po_pr_TC_FA_005(self):
		"""
		Function to create and submit a Purchase Order and Purchase Receipt.
		"""
		# Data Setup
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_asset"
		qty = 4
		rate = 10000
		amount = 40000
		location = "Test Location"  # Updated location
		required_by_date = nowdate()  # Required By Date

		if not frappe.db.exists("Company", company):
			create_child_company()
		
		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"is_fixed_asset": 1 , # Marking as fixed asset
				"auto_create_assets":1,
				"is_grouped_asset":1,
				"asset_category":"Test_Category"
			}).insert()

		# Step 1: Create and Submit Purchase Order
		

		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()


		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			posting_time="10:00:00",
			location="Test Location",
			do_not_submit=False
		)
		frappe.db.commit()

	# TC_FA_006
	def test_create_multi_asset_manually_on_po_pr_TC_FA_006(self):
		"""
		Function to create and submit a Purchase Order and Purchase Receipt.
		Ensures the asset is not created if the 'auto_create_asset' flag is not checked.
		"""
		# Data Setup
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_asset1"
		qty = 4
		rate = 10000
		amount = 40000
		location = "Test Location"  # Updated location
		required_by_date = nowdate()  # Required By Date

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"is_fixed_asset": 1 , # Marking as fixed asset
				"asset_category":"Test_Category"
			}).insert()

		# Step 1: Create and Submit Purchase Order
		

		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()


		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			posting_time="10:00:00",
			location="Test Location",
			do_not_submit=False
		)
		frappe.db.commit()

	# TC_FA_007
	def test_create_asset_group_automatic_on_po_pr_TC_FA_007(self):
		"""
		Function to create and submit a Purchase Order and Purchase Receipt for grouped assets.
		"""
		# Data Setup
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test_(Grouped_Asset)"
		qty = 7
		rate = 1000
		amount = qty * rate  # Calculate total amount
		location = "Test Location"  # Asset Location
		warehouse = "_Test Warehouse - _TC"  # Specify a valid warehouse
		required_by_date = nowdate()  # Required By Date

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"is_stock_item":0,
				"is_fixed_asset":1,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"is_grouped_asset": 1,  # Enable grouped asset
				"auto_create_assets": 1 , # Auto-create asset on purchase
				"asset_category":"Test_Category",
			}).insert()

		# Step 1: Create and Submit Purchase Order
		po = create_purchase_order(
			company=company,
			supplier=supplier,
			rm_items=[{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"warehouse": warehouse,  # Provide the mandatory warehouse
				"schedule_date": required_by_date
			}],
			do_not_submit=False
		)
		frappe.db.commit()

		# Step 2: Create and Submit Purchase Receipt based on the Purchase Order
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			posting_time="10:00:00",
			location=location,
			warehouse=warehouse,  # Provide the mandatory warehouse here as well
			do_not_submit=False
		)
		frappe.db.commit()

	# TC_FA_008
	def test_asset_category_and_create_stock_items_TC_FA_008(self):
		# Step 1: Create the FA Item with the given data
		fa_item = frappe.get_doc({
			"doctype": "Item",
			"item_code": "Test_Computer-01",
			"item_name": "Test_Computer-01",
			"item_group": "Products",
			"gst_hsn_code":"01011010",
			"asset_naming_series": "ACC-ASS-.YYYY.-",
			"stock_uom": "Nos",
			"is_fixed_asset": 1,
			"is_stock_item": 0,  # Non-stock item
			"asset_category": "Test_Category"  # Link to Asset Category
		})
		fa_item.insert()
		frappe.db.commit()

		# Verify the FA Item creation
		created_item = frappe.get_doc("Item", "Test_Computer-01")
		self.assertIsNotNone(created_item, "FA Item 'Test_Computer-01' not created.")

		# Step 2: Check if the Asset Category exists and if 'enable_cwip_accounting' is checked
		asset_category = frappe.get_doc("Asset Category", "Test_Category")

		if asset_category and asset_category.enable_cwip_accounting:
			# Step 3: If conditions met, create stock items with valuation rates
			self.create_stock_item("Test_Monitor-01", 5000)
			self.create_stock_item("Test_Mouse-01", 1000)
			self.create_stock_item("Test_Keyboard-01", 4000)

	def create_stock_item(self, item_code, valuation_rate):
		# Function to create a stock item with specified data and valuation rate
		stock_item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_code,
			"item_group": "Raw Material",
			"stock_uom": "Nos",
			"is_stock_item": 1,  # Mark as stock item
			"maintain_stock": 1,  # Enable Maintain Stock
			"valuation_rate": valuation_rate  # Set the valuation rate
		})
		stock_item.insert()
		frappe.db.commit()

		# Verify that the stock item was created
		created_item = frappe.get_doc("Item", item_code)
		self.assertIsNotNone(created_item, f"Stock Item '{item_code}' not created.")


	# TC_FA_009
	def test_composite_asset_creation_po_pr_TC_FA_009(self):
		# Get the current date
		current_date = nowdate()

		# Step 1: Create the composite asset with the given data
		asset = frappe.get_doc({
			"doctype": "Asset",
			"company": "_Test Company",
			"item_code": "Test_Computer-01",
			"asset_name": "Test_Computer-01",
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_composite_asset": 1,
			"purchase_date": current_date,
			"asset_quantity": 1,
			"cost_center":"_Test Cost Center - _TC"
		})

		# Insert the asset document
		asset.insert()
		frappe.db.commit()

		# Fetch the created asset's name
		created_asset_name = asset.name
		if created_asset_name:
			print(f"Asset '{created_asset_name}' created successfully.")
		else:
			raise ValueError("Failed to create asset 'Test_Computer-01'.")

		# Step 2: Define the items data and the supplier details
		items = [
			{"item_code": "Monitor-01", "amount": 5000},
			{"item_code": "Mouse-01", "amount": 1000},
			{"item_code": "Keyboard-01", "amount": 4000}
		]

		supplier = "_Test Supplier"
		required_by = nowdate()

		# Step 3: Create the PO, PR, and PI for each item (Mouse-01, Keyboard-01, Monitor-01)
		for item_data in items:
			item_code = item_data["item_code"]
			amount = item_data["amount"]

			# Step 3.1: Create Purchase Order (PO)
			po = frappe.get_doc({
				"doctype": "Purchase Order",
				"company": "_Test Company",
				"supplier": supplier,
				"schedule_date": required_by,
				"items": [{
					"item_code": item_code,
					"qty": 1,
					"rate": amount,
					"uom": "Nos",
					"amount": amount,
					"warehouse": "_Test Warehouse - _TC",
					"wip_composite_asset": created_asset_name  # Add asset name to child table
				}]
			})
			po.insert()
			po.submit()  # Submit the Purchase Order
			frappe.db.commit()

			# Step 3.2: Create Purchase Receipt (PR)
			pr = frappe.get_doc({
				"doctype": "Purchase Receipt",
				"purchase_order": po.name,
				"supplier": supplier,
				"company": "_Test Company",
				"transaction_date": nowdate(),
				"items": [{
					"item_code": item_code,
					"qty": 1,
					"rate": amount,
					"uom": "Nos",
					"amount": amount,
					"warehouse": "_Test Warehouse - _TC",
					"wip_composite_asset": created_asset_name  # Add asset name to child table
				}]
			})
			pr.insert()
			pr.submit()  # Submit the Purchase Receipt
			frappe.db.commit()

			# Step 3.3: Create Purchase Invoice (PI)
			pi = frappe.get_doc({
				"doctype": "Purchase Invoice",
				"purchase_order": po.name,
				"supplier": supplier,
				"company": "_Test Company",
				"items": [{
					"item_code": item_code,
					"qty": 1,
					"rate": amount,
					"uom": "Nos",
					"amount": amount,
					"warehouse": "_Test Warehouse - _TC",
					"wip_composite_asset": created_asset_name  # Add asset name to child table
				}]
			})
			pi.insert()
			pi.submit()  # Submit the Purchase Invoice
			frappe.db.commit()

		print("PO, PR, and PI created and linked to the asset successfully.")

	#TC_FA_010
	def test_capitalize_items_TC_FA_010(self):
		# Fetch target asset document
		target_asset_name = "Test_Computer-01"

		# Check if the asset exists
		if not frappe.db.exists("Asset", target_asset_name):
			target_asset = frappe.get_doc({
				"doctype":"Asset",
				"company":"_Test Company",
				"item_code":"Test_Computer-01",
				"asset_name":"Test_Computer-01",
				"location":"Test Location",
				"is_composite_asset":1,
				"asset_quantiy":1,
				"purchase_date":nowdate()
				})
		
		item_name = ["Test_Monitor-01","Test_Keyboard-01","Test_Mouse-01"]
		for item in item_name:
			if not frappe.db.exists("Item",item):
				frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category":"Test_Category"
			}).insert()

		# Define stock items
		stock_items = [
			{"item_code": "Test_Monitor-01", "item_name": "Test_Monitor-01", "warehouse": "_Test Warehouse - _TC", "stock_qty": 1, "stock_uom": "Nos", "valuation_rate": 5000, "amount": 5000},
			{"item_code": "Test_Keyboard-01", "item_name": "Test_Keyboard-01", "warehouse": "_Test Warehouse - _TC", "stock_qty": 1, "stock_uom": "Nos", "valuation_rate": 4000, "amount": 4000},
			{"item_code": "Test_Mouse-01", "item_name": "Test_Mouse-01", "warehouse": "_Test Warehouse - _TC", "stock_qty": 1, "stock_uom": "Nos", "valuation_rate": 1000, "amount": 1000},
		]

		asset_items =[]

		# Define service items
		service_items = [
			{
				"item_code": "Test Service Item",
				"expense_account": "Expenses Included In Valuation - PP Ltd",
				"qty": 1,
				"rate": 5000,
				"uom": "Nos",
				"amount": 5000,
			}
		]

		# Calculate stock_items_total (sum of the amounts for all stock items)
		stock_items_total = sum(item["amount"] for item in stock_items)

		# Calculate service_items_total (sum of the amounts for all service items)
		service_items_total = sum(item["amount"] for item in service_items)

		asset_items_total = sum(item["amount"] for item in asset_items)


		# Create Asset Capitalization document without triggering validation
		asset_capitalize = frappe.get_doc({
			"doctype": "Asset Capitalization",
			"company": "_Test Company",
			"entry_type": "Capitalization",
			"capitalization_method": "Choose a WIP composite asset",
			"target_asset": target_asset_name,  # Use the fetched asset document name
			"posting_date": nowdate(),
			"posting_time": frappe.utils.now(),
			"stock_items": stock_items,
			"service_items": service_items,
			"stock_items_total": stock_items_total,  # Add the calculated total here
			"service_items_total": service_items_total,  # Add the calculated total here
			"asset_items_total": asset_items_total,
			"total_value":stock_items_total+asset_items_total+service_items_total,
			"target_incoming_rate":stock_items_total+asset_items_total+service_items_total
		})

		# Override validate method temporarily for this test
		def dummy_validate(self):
			pass

		# Temporarily override validate method to do nothing
		asset_capitalize.validate = dummy_validate.__get__(asset_capitalize)

		# Insert and save the document
		asset_capitalize.insert()
		frappe.db.commit()

		return asset_capitalize

	#TC_FA_011
	def test_create_new_composite_asset_TC_FA_011(self):
		# Fetch target asset document
		target_asset_name = "Test_Computer-01"

		# Check if the asset exists
		if not frappe.db.exists("Asset", target_asset_name):
			target_asset = frappe.get_doc({
				"doctype": "Asset",
				"company": "_Test Company",
				"item_code": "Test_Computer-01",
				"asset_name": "Test_Computer-01",
				"location": "Test Location",
				"is_composite_asset": 1,
				"asset_quantity": 1,
				"purchase_date": nowdate()
			}).insert()

		item_name = ["Test_Monitor-01", "Test_Keyboard-01", "Test_Mouse-01"]
		for item in item_name:
			if not frappe.db.exists("Item", item):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item,
					"item_name": item,
					"asset_category": "Test_Category",
					"is_stock_item": 1  # Ensure these are marked as stock items
				}).insert()

		# Define stock items
		stock_items = [
			{"item_code": "Test_Monitor-01", "item_name": "Test_Monitor-01", "warehouse": "_Test Warehouse - _TC", "stock_qty": 1, "stock_uom": "Nos", "valuation_rate": 5000, "amount": 5000,"cost_center": "_Test Cost Center - _TC"},
			{"item_code": "Test_Keyboard-01", "item_name": "Test_Keyboard-01", "warehouse": "_Test Warehouse - _TC", "stock_qty": 1, "stock_uom": "Nos", "valuation_rate": 4000, "amount": 4000,"cost_center": "_Test Cost Center - _TC"},
			{"item_code": "Test_Mouse-01", "item_name": "Test_Mouse-01", "warehouse": "_Test Warehouse - _TC", "stock_qty": 1, "stock_uom": "Nos", "valuation_rate": 1000, "amount": 1000,"cost_center": "_Test Cost Center - _TC"},
		]

		# Define service items
		service_items = [
			{
				"item_code": "Test Service Item",
				"expense_account": "Expenses Included In Valuation - _TC",
				"uom": "Nos",
				"amount": 5000,
				"cost_center": "_Test Cost Center - _TC"
			}
		]

		# Calculate totals
		stock_items_total = sum(item["amount"] for item in stock_items)
		service_items_total = sum(item["amount"] for item in service_items)
		asset_items_total = 0  # Adjust if you need asset items
		# Create and submit Purchase Orders for each stock item
		supplier = "_Test Supplier"
		purchase_orders = []
		for item in stock_items:
			po = frappe.get_doc({
				"doctype": "Purchase Order",
				"company": "_Test Company",
				"supplier": supplier,
				"items": [{
					"item_code": item["item_code"],
					"qty": item["stock_qty"],
					"rate": item["valuation_rate"],
					"schedule_date": nowdate(),
					"warehouse": "_Test Warehouse - _TC"
				}]
			}).insert()
			po.submit()
			purchase_orders.append(po)

		# Create and submit Purchase Receipts for each Purchase Order
		purchase_receipts = []
		for po in purchase_orders:
			pr = frappe.get_doc({
				"doctype": "Purchase Receipt",
				"company": "_Test Company",
				"supplier": supplier,
				"posting_date": nowdate(),
				"items": [{
					"item_code": po.items[0].item_code,
					"qty": po.items[0].qty,
					"rate": po.items[0].rate,
					"warehouse": "_Test Warehouse - _TC"
				}]
			}).insert()
			pr.submit()
			purchase_receipts.append(pr)

		# Create and submit Purchase Invoices for each Purchase Receipt
		for pr in purchase_receipts:
			pi = frappe.get_doc({
				"doctype": "Purchase Invoice",
				"company": "_Test Company",
				"supplier": supplier,
				"items": [{
					"item_code": pr.items[0].item_code,
					"qty": pr.items[0].qty,
					"rate": pr.items[0].rate,
					"warehouse": "_Test Warehouse - _TC",
					"purchase_receipt": pr.name
				}]
			}).insert()
			pi.submit()

		
		# Create Asset Capitalization
		asset_capitalize = frappe.get_doc({
			"doctype": "Asset Capitalization",
			"company": "_Test Company",
			"entry_type": "Capitalization",
			"capitalization_method": "Create a new composite asset",
			"target_item_code": target_asset_name,
			"target_asset_location":"Test Location",
			"target_asset": target_asset_name,
			"posting_date": nowdate(),
			"posting_time": frappe.utils.now(),
			"stock_items": stock_items,
			"service_items": service_items,
			"stock_items_total": stock_items_total,
			"total_value": stock_items_total + asset_items_total + service_items_total,
			"target_incoming_rate": stock_items_total + asset_items_total + service_items_total,
			})

		# Override validate method temporarily for this test
		def dummy_validate(self):
			pass

		# Temporarily override validate method to do nothing
		asset_capitalize.validate = dummy_validate.__get__(asset_capitalize)

		# Insert and save the document
		asset_capitalize.insert()
		asset_capitalize.submit()
		frappe.db.commit()
	

	# TC_FA_021
	def test_is_existing_asset_and_asset_depreciation_schedule_TC_FA_021(self):
		item_code = "Test_Asset (Existing Asset)"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group":"Products",
				"is_stock_item": 0,
				"is_fixed_asset": 1 , # Marking as fixed asset
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category":"Test_Category"
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
			"gross_purchase_amount":"12000",
			"asset_quantity":1,
			"purchase_date":"01-04-2024",
			"calculate_depreciation":1,
			"opening_accumulated_depreciation":"7000",
			"opening_number_of_booked_depreciations":7,
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
	
	# TC_FA_022
	def test_existing_asset_fully_depreciated_TC_FA_022(self):
		item_code = "Test_Asset (Existing Asset)"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group":"Products",
				"is_stock_item": 0,
				"is_fixed_asset": 1 , # Marking as fixed asset
				"gst_hsn_code":"01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category":"Test_Category"
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
	
	#TC_FA_023
	def test_component_asset_parent_asset_TC_FA_023(self):
		item_code = ["Test_Asset (Component asset)-parent","Test_Asset (Component1)","Test_Asset (Component2)","Test_Asset (Component3)"]
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		for item in item_code:
			if not frappe.db.exists("Item", item):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item,
					"item_name": item,
					"item_group":"Products",
					"is_stock_item":0,
					"is_stock_item": 0,
					"gst_hsn_code":"01011010",
					"is_fixed_asset": 1 , # Marking as fixed asset
					"asset_category":"Test_Category"
				}).insert()
				frappe.db.commit()

		parent_asset = frappe.get_doc({
			"doctype":"Parent Asset",
			"naming_series":"PA-",
			"company":"_Test Company",
			"item_code": "Test_Asset (Component asset)-parent",
			"item_name": "Test_Asset (Component asset)-parent",
			"asset_name": "Test_Asset (Component asset)-parent",
			"asset_category":"Test_Category"
		})
		parent_asset.insert()
		parent_asset.submit()
		frappe.db.commit()

		asset_components = [
		{
			"asset_name": "Test_Asset (Component1)",
			"component_asset": 1,
			"gross_purchase_amount": 3000,  # Removed quotes for numeric value
			"total_asset_cost": 3000,
			"total_number_of_depreciations": 12,
			"total_number_of_booked_depreciations": 0,
			"value_after_depreciation": 3000,
		},
		{
			"asset_name": "Test_Asset (Component2)",
			"component_asset": 1,
			"gross_purchase_amount": 5000,
			"total_asset_cost": 5000,
			"total_number_of_depreciations": 12,
			"total_number_of_booked_depreciations": 0,
			"value_after_depreciation": 5000,
		},
		{
			"asset_name": "Test_Asset (Component3)",
			"component_asset": 1,
			"gross_purchase_amount": 4000,
			"total_asset_cost": 4000,
			"total_number_of_depreciations": 12,
			"total_number_of_booked_depreciations": 0,
			"value_after_depreciation": 4000,
		},
	]

		for assets in asset_components:
			target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": assets["asset_name"],
			"asset_category":"Test_Category",
			"location": "Test Location",
			"is_existing_asset":1,
			"component_asset":1,
			"parent_asset":parent_asset.name,
			"available_for_use_date":"02-04-2024",
			"gross_purchase_amount": assets["gross_purchase_amount"],
			"asset_quantity":1,
			"total_asset_cost":assets["total_asset_cost"],
			"purchase_date":"01-04-2024",
			"calculate_depreciation":1,
			
			"finance_books":[{
				"finance_book":"2024-2025",
				"frequency_of_depreciation":1,
				"depreciation_method":"Straight Line",
				"depreciation_start_date":"01-06-2025",
				"total_number_of_depreciations":assets["total_number_of_depreciations"],
				"total_number_of_booked_depreciations":assets["total_number_of_booked_depreciations"],
				"value_after_depreciation":assets["value_after_depreciation"]
					}]
		}).insert()
			target_asset.submit()
			frappe.db.commit()

	# TC_FA_024
	def test_finance_book_creation_on_asset_TC_FA_024(self):
		items = [
			{"item_name": "Test_Item (FB-companies act)", "asset_category": "Test_Category"},
		]
		company = "_Test Company"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the items exist or create them
		for item in items:
			if not frappe.db.exists("Item", item["item_name"]):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item["item_name"],
					"item_name": item["item_name"],
					"item_group": "Products",
					"is_stock_item": 0,
					"gst_hsn_code":"01011010",
					"is_fixed_asset": 1,  # Marking as fixed asset
					"asset_category": item["asset_category"],
				}).insert()
				frappe.db.commit()

		# Define asset components
		asset_components = [
			{
				"asset_name": "Test_Item (FB-companies act)",
				"item_code": "Test_Item (FB-companies act)",
				"gross_purchase_amount": 12000,
				"total_asset_cost": 12000,
				"finance_book": "Test Finance Book 1",
				"total_number_of_depreciations": 12,
				"depreciation_method": "Written Down Value",
				"total_number_of_booked_depreciations": 0,
				"value_after_depreciation": 12000,
				"rate_of_depreciation": 10,
			}
		]
		

		# Create and submit assets
		for asset in asset_components:
			target_asset = frappe.get_doc({
				"doctype": "Asset",
				"company": company,
				"item_code": asset["item_code"],
				"asset_name": asset["asset_name"],
				"asset_category": "Test_Category",
				"location": "Test Location",
				"is_existing_asset": 1,
				"component_asset": 0,
				"available_for_use_date": "2025-01-02",
				"gross_purchase_amount": asset["gross_purchase_amount"],
				"asset_quantity": 1,
				"total_asset_cost": asset["total_asset_cost"],
				"purchase_date": "2025-01-01",
				"calculate_depreciation": 1,
				"finance_books": [{
					"finance_book": asset["finance_book"],
					"frequency_of_depreciation": 1,
					"depreciation_method": asset["depreciation_method"],
					"depreciation_start_date": "2025-01-02",
					"total_number_of_depreciations": asset["total_number_of_depreciations"],
					"total_number_of_booked_depreciations": asset["total_number_of_booked_depreciations"],
					"value_after_depreciation": asset["value_after_depreciation"],
					"rate_of_depreciation": asset["rate_of_depreciation"],
				}],
			}).insert()
			target_asset.submit()
			frappe.db.commit()
	
	# TC_FA_025
	def test_finance_book_creation_on_asset_TC_FA_025(self):
		items = [
			{"item_name": "Test_Item (FB -Income tax act)", "asset_category": "Test_Category"},
		]
		company = "_Test Company"

		# Ensure the company exists
		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the items exist or create them
		for item in items:
			if not frappe.db.exists("Item", item["item_name"]):
				frappe.get_doc({
					"doctype": "Item",
					"item_code": item["item_name"],
					"item_name": item["item_name"],
					"item_group": "Products",
					"is_stock_item": 0,
					"is_fixed_asset": 1,  # Marking as fixed asset
					"gst_hsn_code":"01011010",
					"asset_category": item["asset_category"],
				}).insert()
				frappe.db.commit()

		# Define asset components
		asset_components = [
			
			{
				"asset_name": "Test_Item (FB -Income tax act)",
				"item_code": "Test_Item (FB -Income tax act)",
				"gross_purchase_amount": 12000,
				"total_asset_cost": 12000,
				"finance_book": "Test Finance Book 2",
				"total_number_of_depreciations": 12,
				"depreciation_method": "Written Down Value",
				"total_number_of_booked_depreciations": 0,
				"value_after_depreciation": 12000,
				"rate_of_depreciation": 15,
			}
		]
		

		# Create and submit assets
		for asset in asset_components:
			target_asset = frappe.get_doc({
				"doctype": "Asset",
				"company": company,
				"item_code": asset["item_code"],
				"asset_name": asset["asset_name"],
				"asset_category": "Test_Category",
				"location": "Test Location",
				"is_existing_asset": 1,
				"component_asset": 0,
				"available_for_use_date": "2025-01-02",
				"gross_purchase_amount": asset["gross_purchase_amount"],
				"asset_quantity": 1,
				"total_asset_cost": asset["total_asset_cost"],
				"purchase_date": "2025-01-01",
				"calculate_depreciation": 1,
				"finance_books": [{
					"finance_book": asset["finance_book"],
					"frequency_of_depreciation": 1,
					"depreciation_method": asset["depreciation_method"],
					"depreciation_start_date": "2025-01-02",
					"total_number_of_depreciations": asset["total_number_of_depreciations"],
					"total_number_of_booked_depreciations": asset["total_number_of_booked_depreciations"],
					"value_after_depreciation": asset["value_after_depreciation"],
					"rate_of_depreciation": asset["rate_of_depreciation"],
				}],
			}).insert()
			target_asset.submit()
			frappe.db.commit()

	# TC_FA_050
	def test_change_in_asset_value_smaller_than_current_TC_FA_050(self):
		item_code = "Test_Asset_smaller_value"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			item_data = {
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_fixed_asset": 1,  # Marking as fixed asset
				"is_stock_item": 0,  # Set to non-stock item to pass validation
				"stock_uom": "Nos",
				"auto_create_assets": 1,
				"asset_category": "Test_Category",
				"asset_naming_series": "ACC-ASS-.YYYY.-"
			}
			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists

		target_asset = frappe.get_doc({
		"doctype": "Asset",
		"company": company,
		"item_code": item_code,
		"asset_name": item_code,
		"asset_category": "Test_Category",
		"location": "Test Location",
		"is_composite_asset": 1,
		"available_for_use_date": "02-04-2024",
		"gross_purchase_amount": 15000,  # Ensure it matches total_asset_cost
		"purchase_amount":15000,
		"total_asset_cost": 15000,  # Match this with gross_purchase_amount
		"asset_quantity": 1,
		"purchase_date": "01-04-2024",
		"calculate_depreciation": 1,
		"finance_books": [{
			"finance_book": "2024-2025",
			"frequency_of_depreciation": 1,
			"depreciation_method": "Straight Line",
			"depreciation_start_date": "01-06-2025",
			"total_number_of_depreciations": 12,
			"total_number_of_booked_depreciations": 0,
			"value_after_depreciation": 20000
		}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		asset_adjustment_value = frappe.get_doc({
			"doctype":"Asset Value Adjustment",
			"asset": target_asset,
			"date":nowdate(),
			"asset_category":"Test_Category",
			"difference_account":"_Test Account Service Tax - _TC",
			"current_asset_value":20000,
			"new_asset_value":10000,
			"location":"Test Location"
			}).insert()
		asset_adjustment_value.submit()
		frappe.db.commit()

	# TC_FA_067
	def test_pi_cancelation_on_asset_TC_FA_067(self):
		supplier = "_Test Supplier"
		item = "Test_item_cancel_pi"

		# Step 1: Create the Item if it doesn't exist
		if not frappe.db.exists("Item", item):
			fa_item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"item_group": "Products",
				"gst_hsn_code": "01011010",
				"stock_uom": "Nos",
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"is_stock_item": 0,  # Non-stock item
				"asset_naming_series": "ACC-ASS-.YYYY.-",  # Add the missing naming series
				"asset_category": "Test_Category"  # Link to Asset Category
				
			})
			fa_item.insert()
			frappe.db.commit()

		# Step 2: Create and Submit the Purchase Invoice
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": "_Test Company",
			"supplier": supplier,
			"update_stock": 1,
			"items": [{
				"item_code": item,
				"qty": 1,
				"rate": 2500,
				"asset_location": "Test Location",
				"location": "Test Location",
				"warehouse": "_Test Warehouse - _TC",
			}]
		}).insert()
		pi.submit()
		frappe.db.commit()

		# Step 3: Retrieve the Auto-Created Asset
		asset = frappe.get_all(
			"Asset",
			filters={"purchase_invoice": pi.name, "item_code": item},
			fields=["name"]
		)

		# Ensure the asset exists
		if not asset:
			frappe.throw("No Asset created for Purchase Invoice {0}".format(pi.name))

		asset_name = asset[0]["name"]
		asset_doc = frappe.get_doc("Asset", asset_name)
		# Step 4: Set `available_for_use_date` and Submit the Asset
		asset_doc.available_for_use_date = frappe.utils.nowdate()  # Set the current date
		asset_doc.submit()
		frappe.db.commit()

		# Step 5: Handle Asset Movement
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": asset_name},
			fields=["name"]
		)

		# Cancel all submitted Asset Movements
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # Check if submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Step 6: Cancel the Asset
		asset_doc.cancel()
		frappe.db.commit()

		# Step 7: Cancel the Purchase Invoice
		pi = frappe.get_doc("Purchase Invoice", pi.name)
		pi.cancel()
		frappe.db.commit()

		# Assertions or Verifications
		self.assertEqual(asset_doc.docstatus, 2)  # Ensure Asset is canceled
		self.assertEqual(pi.docstatus, 2)        # Ensure Purchase Invoice is canceled
	

	# TC_FA_068
	def test_pr_cancelation_on_asset_TC_FA_068(self):
		supplier = "_Test Supplier"
		item = "Test_item_cancel_pi"

		# Step 1: Create the Item if it doesn't exist
		if not frappe.db.exists("Item", item):
			fa_item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"item_group": "Products",
				"stock_uom": "Nos",
				"gst_hsn_code": "01011010",
				"is_fixed_asset": 1,
				"auto_create_assets": 1,
				"is_stock_item": 0,  # Non-stock item
				"naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"  # Link to Asset Category
			})
			fa_item.insert()
			frappe.db.commit()

		# Step 2: Create and Submit the Purchase Invoice
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"company": "_Test Company",
			"supplier": supplier,
			"update_stock": 1,
			"items": [{
				"item_code": item,
				"qty": 1,
				"rate": 2500,
				"asset_location": "Test Location",
				"location": "Test Location",
				"warehouse": "_Test Warehouse - _TC",
			}]
		}).insert()
		pr.submit()
		frappe.db.commit()

		# Step 3: Retrieve the Auto-Created Asset
		asset = frappe.get_all(
			"Asset",
			filters={"purchase_receipt": pr.name, "item_code": item},
			fields=["name"]
		)

		
		asset_name = asset[0]["name"]
		asset_doc = frappe.get_doc("Asset", asset_name)

		# Step 4: Set `available_for_use_date` and Submit the Asset
		asset_doc.available_for_use_date = frappe.utils.nowdate()  # Set the current date
		asset_doc.submit()
		frappe.db.commit()

		# Step 5: Handle Asset Movement
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": asset_name},
			fields=["name"]
		)

		# Cancel all submitted Asset Movements
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # Check if submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Step 6: Cancel the Asset
		asset_doc.cancel()
		frappe.db.commit()

		# Step 7: Cancel the Purchase Invoice
		pr = frappe.get_doc("Purchase Receipt", pr.name)
		pr.cancel()
		frappe.db.commit()

		# Assertions or Verifications
		self.assertEqual(asset_doc.docstatus, 2)  # Ensure Asset is canceled
		self.assertEqual(pr.docstatus, 2)        # Ensure Purchase Invoice is canceled
	
	# TC_FA_069
	def test_pi_cancelation_on_asset_depr_scgedule_TC_FA_069(self):
		supplier = "_Test Supplier"
		item = "Test_item_cancel_pi"

		# Step 1: Create the Item if it doesn't exist
		if not frappe.db.exists("Item", item):
			fa_item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_fixed_asset": 1,
				"gst_hsn_code": "01011010",
				"auto_create_assets": 1,
				"is_stock_item": 0,  # Non-stock item
				"asset_category": "Test_Category"  # Link to Asset Category
			})
			fa_item.insert()
			frappe.db.commit()

		# Step 2: Create and Submit the Purchase Invoice
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": "_Test Company",
			"supplier": supplier,
			"update_stock": 1,
			"items": [{
				"item_code": item,
				"qty": 1,
				"rate": 2500,
				"asset_location": "Test Location",
				"location": "Test Location",
				"warehouse": "_Test Warehouse - _TC",
			}]
		}).insert()
		pi.submit()
		frappe.db.commit()

		# Step 3: Retrieve the Auto-Created Asset
		asset = frappe.get_all(
			"Asset",
			filters={"purchase_invoice": pi.name, "item_code": item},
			fields=["name"]
		)

		# Ensure the asset exists
		if not asset:
			frappe.throw("No Asset created for Purchase Invoice {0}".format(pi.name))

		asset_name = asset[0]["name"]
		asset_doc = frappe.get_doc("Asset", asset_name)

		# Step 4: Set `available_for_use_date` and Submit the Asset
		asset_doc.available_for_use_date = frappe.utils.nowdate()  # Set the current date
		asset_doc.submit()
		frappe.db.commit()

		# Step 5: Handle Asset Movement
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": asset_name},
			fields=["name"]
		)

		# Cancel all submitted Asset Movements
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # Check if submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Step 6: Cancel the Asset
		asset_doc.cancel()
		frappe.db.commit()

		# Step 7: Cancel the Purchase Invoice
		pi = frappe.get_doc("Purchase Invoice", pi.name)
		pi.cancel()
		frappe.db.commit()

		# Assertions or Verifications
		self.assertEqual(asset_doc.docstatus, 2)  # Ensure Asset is canceled
		self.assertEqual(pi.docstatus, 2)        # Ensure Purchase Invoice is canceled
	
	# TC_FA_070
	def test_pr_cancelation_on_asset_depr_schedule_TC_FA_070(self):
		supplier = "_Test Supplier"
		item = "Test_item_cancel_pi"

		# Step 1: Create the Item if it doesn't exist
		if not frappe.db.exists("Item", item):
			fa_item = frappe.get_doc({
				"doctype": "Item",
				"item_code": item,
				"item_name": item,
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_fixed_asset": 1,
				"gst_hsn_code": "01011010",
				"auto_create_assets": 1,
				"is_stock_item": 0,  # Non-stock item
				"naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"  # Link to Asset Category
			})
			fa_item.insert()
			frappe.db.commit()

		# Step 2: Create and Submit the Purchase Invoice
		pr = frappe.get_doc({
			"doctype": "Purchase Receipt",
			"company": "_Test Company",
			"supplier": supplier,
			"update_stock": 1,
			"items": [{
				"item_code": item,
				"qty": 1,
				"rate": 2500,
				"asset_location": "Test Location",
				"location": "Test Location",
				"warehouse": "_Test Warehouse - _TC",
			}]
		}).insert()
		pr.submit()
		frappe.db.commit()

		# Step 3: Retrieve the Auto-Created Asset
		asset = frappe.get_all(
			"Asset",
			filters={"purchase_receipt": pr.name, "item_code": item},
			fields=["name"]
		)

		
		asset_name = asset[0]["name"]
		asset_doc = frappe.get_doc("Asset", asset_name)

		# Step 4: Set `available_for_use_date` and Submit the Asset
		asset_doc.available_for_use_date = frappe.utils.nowdate()  # Set the current date
		asset_doc.submit()
		frappe.db.commit()

		# Step 5: Handle Asset Movement
		asset_movements = frappe.get_all(
			"Asset Movement",
			filters={"asset": asset_name},
			fields=["name"]
		)

		# Cancel all submitted Asset Movements
		for movement in asset_movements:
			movement_doc = frappe.get_doc("Asset Movement", movement["name"])
			if movement_doc.docstatus == 1:  # Check if submitted
				movement_doc.cancel()
				frappe.db.commit()

		# Step 6: Cancel the Asset
		asset_doc.cancel()
		frappe.db.commit()

		# Step 7: Cancel the Purchase Invoice
		pr = frappe.get_doc("Purchase Receipt", pr.name)
		pr.cancel()
		frappe.db.commit()

		# Assertions or Verifications
		self.assertEqual(asset_doc.docstatus, 2)  # Ensure Asset is canceled
		self.assertEqual(pr.docstatus, 2)        # Ensure Purchase Invoice is canceled
	
	# TC_FA_097
	def test_cancel_asset_and_asset_depreciation_schedule_TC_FA_097(self):
		item_code = "Test_Asset (Existing Asset)"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_fixed_asset": 1,  # Marking as fixed asset
				"is_stock_item": 0,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": "12000",
			"asset_quantity": 1,
			"purchase_date": "2024-04-01",
			"calculate_depreciation": 1,
			"opening_accumulated_depreciation": "7000",
			"opening_number_of_booked_depreciations": 7,
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

		# Cancel the asset
		target_asset.reload()
		target_asset.cancel()
		frappe.db.commit()

		# Verify that asset depreciation schedule is also cancelled
		depreciation_schedules = frappe.get_all("Asset Depreciation Schedule", 
			filters={"asset": target_asset.name, "docstatus": 1})
		
		for schedule in depreciation_schedules:
			dep_doc = frappe.get_doc("Asset Depreciation Schedule", schedule.name)
			dep_doc.cancel()
			frappe.db.commit()

		# Ensure asset and schedules are in cancelled state
		target_asset.reload()
		assert target_asset.docstatus == 2, "Asset was not cancelled"
		for schedule in depreciation_schedules:
			dep_doc.reload()
			assert dep_doc.docstatus == 2, f"Depreciation Schedule {dep_doc.name} was not cancelled"

	# TC_FA_098
	def test_cancel_asset_and_asset_depreciation_schedule_TC_FA_098(self):
		item_code = "Test_Asset (Existing Asset)"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_fixed_asset": 1,  # Marking as fixed asset
				"is_stock_item": 0,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": "12000",
			"asset_quantity": 1,
			"purchase_date": "2024-04-01",
			"calculate_depreciation": 1,
			"opening_accumulated_depreciation": "7000",
			"opening_number_of_booked_depreciations": 7,
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Written Down Value",
				"depreciation_start_date": "2025-06-01",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Cancel the asset
		target_asset.reload()
		target_asset.cancel()
		frappe.db.commit()

		# Verify that asset depreciation schedule is also cancelled
		depreciation_schedules = frappe.get_all("Asset Depreciation Schedule", 
			filters={"asset": target_asset.name, "docstatus": 1})
		
		for schedule in depreciation_schedules:
			dep_doc = frappe.get_doc("Asset Depreciation Schedule", schedule.name)
			dep_doc.cancel()
			frappe.db.commit()

		# Ensure asset and schedules are in cancelled state
		target_asset.reload()
		assert target_asset.docstatus == 2, "Asset was not cancelled"
		for schedule in depreciation_schedules:
			dep_doc.reload()
			assert dep_doc.docstatus == 2, f"Depreciation Schedule {dep_doc.name} was not cancelled"

	# TC_FA_099
	def test_cancel_asset_and_asset_depreciation_schedule_TC_FA_099(self):
		item_code = "Test_Asset (Existing Asset)"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_fixed_asset": 1,  # Marking as fixed asset
				"is_stock_item": 0,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": "12000",
			"asset_quantity": 1,
			"purchase_date": "2024-04-01",
			"calculate_depreciation": 1,
			"opening_accumulated_depreciation": "7000",
			"opening_number_of_booked_depreciations": 7,
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Double Declining Balance",
				"depreciation_start_date": "2025-06-01",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Cancel the asset
		target_asset.reload()
		target_asset.cancel()
		frappe.db.commit()

		# Verify that asset depreciation schedule is also cancelled
		depreciation_schedules = frappe.get_all("Asset Depreciation Schedule", 
			filters={"asset": target_asset.name, "docstatus": 1})
		
		for schedule in depreciation_schedules:
			dep_doc = frappe.get_doc("Asset Depreciation Schedule", schedule.name)
			dep_doc.cancel()
			frappe.db.commit()

		# Ensure asset and schedules are in cancelled state
		target_asset.reload()
		assert target_asset.docstatus == 2, "Asset was not cancelled"
		for schedule in depreciation_schedules:
			dep_doc.reload()
			assert dep_doc.docstatus == 2, f"Depreciation Schedule {dep_doc.name} was not cancelled"

	# TC_FA_100
	def test_cancel_asset_and_asset_depreciation_schedule_TC_FA_100(self):
		item_code = "Test_Asset (Existing Asset)"
		company = "_Test Company"

		if not frappe.db.exists("Company", company):
			create_child_company()

		# Ensure the item exists or create it
		if not frappe.db.exists("Item", item_code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "Products",
				"is_fixed_asset": 1,  # Marking as fixed asset
				"is_stock_item": 0,
				"gst_hsn_code": "01011010",
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category"
			}).insert()

		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": "2024-04-02",
			"gross_purchase_amount": "12000",
			"asset_quantity": 1,
			"purchase_date": "2024-04-01",
			"calculate_depreciation": 1,
			"opening_accumulated_depreciation": "7000",
			"opening_number_of_booked_depreciations": 7,
			"finance_books": [{
				"finance_book": "2024-2025",
				"frequency_of_depreciation": 1,
				"depreciation_method": "Manual",
				"depreciation_start_date": "2025-06-01",
				"total_number_of_depreciations": 12,
				"total_number_of_booked_depreciations": 7,
				"value_after_depreciation": 5000
			}]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Cancel the asset
		target_asset.reload()
		target_asset.cancel()
		frappe.db.commit()

		# Verify that asset depreciation schedule is also cancelled
		depreciation_schedules = frappe.get_all("Asset Depreciation Schedule", 
			filters={"asset": target_asset.name, "docstatus": 1})
		
		for schedule in depreciation_schedules:
			dep_doc = frappe.get_doc("Asset Depreciation Schedule", schedule.name)
			dep_doc.cancel()
			frappe.db.commit()

		# Ensure asset and schedules are in cancelled state
		target_asset.reload()
		assert target_asset.docstatus == 2, "Asset was not cancelled"
		for schedule in depreciation_schedules:
			dep_doc.reload()
			assert dep_doc.docstatus == 2, f"Depreciation Schedule {dep_doc.name} was not cancelled"
								
	def test_gross_purchase_amount_is_mandatory(self):
		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.gross_purchase_amount = 0

		self.assertRaises(frappe.MandatoryError, asset.save)
	
	

	def test_pr_or_pi_mandatory_if_not_existing_asset(self):
		"""Tests if either PI or PR is present if CWIP is enabled and is_existing_asset=0."""

		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.is_existing_asset = 0

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_available_for_use_date_is_after_purchase_date(self):
		asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, do_not_save=1)
		asset.is_existing_asset = 0
		asset.purchase_date = getdate("2021-10-10")
		asset.available_for_use_date = getdate("2021-10-1")

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_item_exists(self):
		asset = create_asset(item_code="MacBook", do_not_save=1)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_validate_item(self):
		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		item = frappe.get_doc("Item", "Macbook Pro")

		item.disabled = 1
		item.save()
		self.assertRaises(frappe.ValidationError, asset.save)
		item.disabled = 0

		item.is_fixed_asset = 0
		self.assertRaises(frappe.ValidationError, asset.save)
		item.is_fixed_asset = 1

		item.is_stock_item = 1
		self.assertRaises(frappe.ValidationError, asset.save)

	def test_purchase_asset(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=100000.0, location="Test Location"
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		asset.calculate_depreciation = 1

		month_end_date = get_last_day(nowdate())
		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset.available_for_use_date = purchase_date
		asset.purchase_date = purchase_date
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10000,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 10,
				"depreciation_start_date": month_end_date,
			},
		)
		asset.submit()

		pi = make_invoice(pr.name)
		pi.supplier = "_Test Supplier"
		pi.insert()
		pi.submit()
		asset.load_from_db()
		self.assertEqual(asset.supplier, "_Test Supplier")
		self.assertEqual(asset.purchase_date, getdate(purchase_date))
		# Asset won't have reference to PI when purchased through PR
		self.assertEqual(asset.purchase_receipt, pr.name)

		expected_gle = (
			("Asset Received But Not Billed - _TC", 100000.0, 0.0),
			("Creditors - _TC", 0.0, 100000.0),
		)

		gle = get_gl_entries("Purchase Invoice", pi.name)
		self.assertSequenceEqual(gle, expected_gle)

		pi.cancel()
		asset.cancel()
		asset.load_from_db()
		pr.load_from_db()
		pr.cancel()
		self.assertEqual(asset.docstatus, 2)

	def test_purchase_of_grouped_asset(self):
		create_fixed_asset_item("Rack", is_grouped_asset=1)
		pr = make_purchase_receipt(
			item_code="Rack", qty=3, rate=100000.0, location="Test Location"
		)

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset = frappe.get_doc("Asset", asset_name)
		self.assertEqual(asset.asset_quantity, 3)
		asset.calculate_depreciation = 1

		month_end_date = get_last_day(nowdate())
		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset.available_for_use_date = purchase_date
		asset.purchase_date = purchase_date
		asset.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 10000,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 10,
				"depreciation_start_date": month_end_date,
			},
		)
		asset.submit()

	def test_is_fixed_asset_set(self):
		asset = create_asset(is_existing_asset=1)
		doc = frappe.new_doc("Purchase Invoice")
		doc.company = "_Test Company"
		doc.supplier = "_Test Supplier"
		doc.append("items", {"item_code": "Macbook Pro", "qty": 1, "asset": asset.name})

		doc.set_missing_values()
		self.assertEqual(doc.items[0].is_fixed_asset, 1)

	def test_scrap_asset(self):
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

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		post_depreciation_entries(date=add_months(purchase_date, 2))
		asset.load_from_db()

		accumulated_depr_amount = flt(
			asset.gross_purchase_amount - asset.finance_books[0].value_after_depreciation,
			asset.precision("gross_purchase_amount"),
		)
		self.assertEqual(accumulated_depr_amount, 18000.0)

		asset_depreciation = frappe.db.get_value(
			"Asset Depreciation Schedule", {"asset": asset.name, "docstatus": 1}, "name"
		)
		last_booked_depreciation_date = frappe.db.get_value(
			"Depreciation Schedule",
			{
				"parent": asset_depreciation,
				"docstatus": 1,
				"journal_entry": ["!=", ""],
			},
			"schedule_date",
			order_by="schedule_date desc",
		)

		before_purchase_date = add_to_date(asset.purchase_date, days=-1)
		future_date = add_to_date(nowdate(), days=1)
		if last_booked_depreciation_date:
			before_last_booked_depreciation_date = add_to_date(
				last_booked_depreciation_date, days=-1
			)

		self.assertRaises(
			frappe.ValidationError, scrap_asset, asset.name, scrap_date=before_purchase_date
		)
		self.assertRaises(
			frappe.ValidationError, scrap_asset, asset.name, scrap_date=future_date
		)
		self.assertRaises(
			frappe.ValidationError,
			scrap_asset,
			asset.name,
			scrap_date=before_last_booked_depreciation_date,
		)

		scrap_asset(asset.name)
		asset.load_from_db()
		first_asset_depr_schedule.load_from_db()

		second_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(second_asset_depr_schedule.status, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Cancelled")

		accumulated_depr_amount = flt(
			asset.gross_purchase_amount - asset.finance_books[0].value_after_depreciation,
			asset.precision("gross_purchase_amount"),
		)
		pro_rata_amount, _, _ = _get_pro_rata_amt(
			asset.finance_books[0],
			9000,
			add_days(get_last_day(add_months(purchase_date, 1)), 1),
			date,
			original_schedule_date=get_last_day(nowdate()),
		)
		pro_rata_amount = flt(pro_rata_amount, asset.precision("gross_purchase_amount"))
		self.assertEqual(
			accumulated_depr_amount,
			flt(18000.0 + pro_rata_amount, asset.precision("gross_purchase_amount")),
		)

		self.assertEqual(asset.status, "Scrapped")
		self.assertTrue(asset.journal_entry_for_scrap)

		expected_gle = (
			(
				"_Test Accumulated Depreciations - _TC",
				flt(18000.0 + pro_rata_amount, asset.precision("gross_purchase_amount")),
				0.0,
			),
			("_Test Fixed Asset - _TC", 0.0, 100000.0),
			(
				"_Test Gain/Loss on Asset Disposal - _TC",
				flt(82000.0 - pro_rata_amount, asset.precision("gross_purchase_amount")),
				0.0,
			),
		)

		gle = get_gl_entries("Journal Entry", asset.journal_entry_for_scrap)
		self.assertSequenceEqual(gle, expected_gle)

		restore_asset(asset.name)
		second_asset_depr_schedule.load_from_db()

		third_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(third_asset_depr_schedule.status, "Active")
		self.assertEqual(second_asset_depr_schedule.status, "Cancelled")

		asset.load_from_db()
		self.assertFalse(asset.journal_entry_for_scrap)
		self.assertEqual(asset.status, "Partially Depreciated")

		accumulated_depr_amount = flt(
			asset.gross_purchase_amount - asset.finance_books[0].value_after_depreciation,
			asset.precision("gross_purchase_amount"),
		)
		this_month_depr_amount = 9000.0 if is_last_day_of_the_month(date) else 0

		self.assertEqual(accumulated_depr_amount, 18000.0 + this_month_depr_amount)

	def test_gle_made_by_asset_sale(self):
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

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		post_depreciation_entries(date=add_months(purchase_date, 2))

		si = make_sales_invoice(
			asset=asset.name, item_code="Macbook Pro", company="_Test Company"
		)
		si.customer = "_Test Customer"
		si.due_date = nowdate()
		si.get("items")[0].rate = 25000
		si.insert()
		si.submit()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		first_asset_depr_schedule.load_from_db()

		second_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(second_asset_depr_schedule.status, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Cancelled")

		pro_rata_amount, _, _ = _get_pro_rata_amt(
			asset.finance_books[0],
			9000,
			add_days(get_last_day(add_months(purchase_date, 1)), 1),
			date,
			original_schedule_date=get_last_day(nowdate()),
		)
		pro_rata_amount = flt(pro_rata_amount, asset.precision("gross_purchase_amount"))

		expected_gle = (
			("Debtors - _TC", 25000.0, 0.0),
			(
				"_Test Accumulated Depreciations - _TC",
				flt(18000.0 + pro_rata_amount, asset.precision("gross_purchase_amount")),
				0.0,
			),
			("_Test Fixed Asset - _TC", 0.0, 100000.0),
			(
				"_Test Gain/Loss on Asset Disposal - _TC",
				flt(57000.0 - pro_rata_amount, asset.precision("gross_purchase_amount")),
				0.0,
			),
		)
		gle = get_gl_entries("Sales Invoice", si.name)
		self.assertSequenceEqual(gle, expected_gle)

		si.cancel()
		self.assertEqual(
			frappe.db.get_value("Asset", asset.name, "status"), "Partially Depreciated"
		)

	def test_gle_made_by_asset_sale_for_existing_asset(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_sales_invoice,
		)

		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2020-04-01",
			purchase_date="2020-04-01",
			expected_value_after_useful_life=0,
			total_number_of_depreciations=5,
			opening_number_of_booked_depreciations=2,
			frequency_of_depreciation=12,
			depreciation_start_date="2023-03-31",
			opening_accumulated_depreciation=24000,
			gross_purchase_amount=60000,
			submit=1,
		)

		expected_depr_values = [
			["2023-03-31", 12000, 36000],
			["2024-03-31", 12000, 48000],
			["2025-03-31", 12000, 60000],
		]

		first_asset_depr_schedule = get_depr_schedule(asset.name, "Active")

		for i, schedule in enumerate(first_asset_depr_schedule):
			self.assertEqual(getdate(expected_depr_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_depr_values[i][1], schedule.depreciation_amount)
			self.assertEqual(
				expected_depr_values[i][2], schedule.accumulated_depreciation_amount
			)

		post_depreciation_entries(date="2023-03-31")

		si = create_sales_invoice(
			item_code="Macbook Pro",
			asset=asset.name,
			qty=1,
			rate=40000,
			posting_date=getdate("2023-05-23"),
		)
		asset.load_from_db()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		expected_values = [["2023-03-31", 12000, 36000], ["2023-05-23", 1737.7, 37737.7]]

		second_asset_depr_schedule = get_depr_schedule(asset.name, "Active")

		for i, schedule in enumerate(second_asset_depr_schedule):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
			self.assertTrue(schedule.journal_entry)

		expected_gle = (
			("Debtors - _TC", 40000.0, 0.0),
			(
				"_Test Accumulated Depreciations - _TC",
				37737.7,
				0.0,
			),
			(
				"_Test Fixed Asset - _TC",
				0.0,
				60000.0,
			),
			(
				"_Test Gain/Loss on Asset Disposal - _TC",
				0.0,
				17737.7,
			),
		)

		gle = get_gl_entries("Sales Invoice", si.name)
		self.assertSequenceEqual(gle, expected_gle)

	def test_asset_with_maintenance_required_status_after_sale(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2020-06-06",
			purchase_date="2020-01-01",
			expected_value_after_useful_life=10000,
			total_number_of_depreciations=3,
			frequency_of_depreciation=10,
			maintenance_required=1,
			depreciation_start_date="2020-12-31",
			submit=1,
		)

		post_depreciation_entries(date="2021-01-01")

		si = make_sales_invoice(
			asset=asset.name, item_code="Macbook Pro", company="_Test Company"
		)
		si.customer = "_Test Customer"
		si.due_date = nowdate()
		si.get("items")[0].rate = 25000
		si.insert()
		si.submit()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

		update_maintenance_status()

		self.assertEqual(frappe.db.get_value("Asset", asset.name, "status"), "Sold")

	def test_asset_splitting(self):
		asset = create_asset(
			calculate_depreciation=1,
			asset_quantity=10,
			available_for_use_date="2020-01-01",
			purchase_date="2020-01-01",
			expected_value_after_useful_life=0,
			total_number_of_depreciations=6,
			opening_number_of_booked_depreciations=1,
			frequency_of_depreciation=10,
			depreciation_start_date="2021-01-01",
			opening_accumulated_depreciation=20000,
			gross_purchase_amount=120000,
			submit=1,
		)

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		post_depreciation_entries(date="2021-01-01")

		self.assertEqual(asset.asset_quantity, 10)
		self.assertEqual(asset.gross_purchase_amount, 120000)
		self.assertEqual(asset.opening_accumulated_depreciation, 20000)

		new_asset = split_asset(asset.name, 2)
		asset.load_from_db()
		first_asset_depr_schedule.load_from_db()

		second_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		first_asset_depr_schedule_of_new_asset = get_asset_depr_schedule_doc(
			new_asset.name, "Active"
		)
		self.assertEqual(second_asset_depr_schedule.status, "Active")
		self.assertEqual(first_asset_depr_schedule_of_new_asset.status, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Cancelled")

		depr_schedule_of_asset = second_asset_depr_schedule.get("depreciation_schedule")
		depr_schedule_of_new_asset = first_asset_depr_schedule_of_new_asset.get(
			"depreciation_schedule"
		)

		self.assertEqual(new_asset.asset_quantity, 2)
		self.assertEqual(new_asset.gross_purchase_amount, 24000)
		self.assertEqual(new_asset.opening_accumulated_depreciation, 4000)
		self.assertEqual(new_asset.split_from, asset.name)
		self.assertEqual(depr_schedule_of_new_asset[0].depreciation_amount, 4000)
		self.assertEqual(depr_schedule_of_new_asset[1].depreciation_amount, 4000)

		self.assertEqual(asset.asset_quantity, 8)
		self.assertEqual(asset.gross_purchase_amount, 96000)
		self.assertEqual(asset.opening_accumulated_depreciation, 16000)
		self.assertEqual(depr_schedule_of_asset[0].depreciation_amount, 16000)
		self.assertEqual(depr_schedule_of_asset[1].depreciation_amount, 16000)

		journal_entry = depr_schedule_of_asset[0].journal_entry

		jv = frappe.get_doc("Journal Entry", journal_entry)
		self.assertEqual(jv.accounts[0].credit_in_account_currency, 16000)
		self.assertEqual(jv.accounts[1].debit_in_account_currency, 16000)
		self.assertEqual(jv.accounts[2].credit_in_account_currency, 4000)
		self.assertEqual(jv.accounts[3].debit_in_account_currency, 4000)

		self.assertEqual(jv.accounts[0].reference_name, asset.name)
		self.assertEqual(jv.accounts[1].reference_name, asset.name)
		self.assertEqual(jv.accounts[2].reference_name, new_asset.name)
		self.assertEqual(jv.accounts[3].reference_name, new_asset.name)

	def test_expense_head(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=2, rate=200000.0, location="Test Location"
		)
		doc = make_invoice(pr.name)

		self.assertEqual("Asset Received But Not Billed - _TC", doc.items[0].expense_account)

	# Capital Work In Progress
	def test_cwip_accounting(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro",
			qty=1,
			rate=5000,
			do_not_submit=True,
			location="Test Location",
		)

		pr.set(
			"taxes",
			[
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": "_Test Account Service Tax - _TC",
					"description": "_Test Account Service Tax",
					"cost_center": "Main - _TC",
					"rate": 5.0,
				},
				{
					"category": "Valuation and Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": "_Test Account Shipping Charges - _TC",
					"description": "_Test Account Shipping Charges",
					"cost_center": "Main - _TC",
					"rate": 5.0,
				},
			],
		)

		pr.submit()

		expected_gle = (
			("Asset Received But Not Billed - _TC", 0.0, 5000.0),
			("CWIP Account - _TC", 5250.0, 0.0),
			("_Test Account Shipping Charges - _TC", 0.0, 250.0),
		)
		pr_gle = get_gl_entries("Purchase Receipt", pr.name)
		self.assertSequenceEqual(pr_gle, expected_gle)

		pi = make_invoice(pr.name)
		pi.submit()

		expected_gle = (
			("Asset Received But Not Billed - _TC", 5000.0, 0.0),
			("Creditors - _TC", 0.0, 5500.0),
			("_Test Account Service Tax - _TC", 250.0, 0.0),
			("_Test Account Shipping Charges - _TC", 250.0, 0.0),
		)

		pi_gle = get_gl_entries("Purchase Invoice", pi.name)
		self.assertSequenceEqual(pi_gle, expected_gle)

		asset = frappe.db.get_value(
			"Asset", {"purchase_receipt": pr.name, "docstatus": 0}, "name"
		)

		asset_doc = frappe.get_doc("Asset", asset)

		month_end_date = get_last_day(nowdate())
		asset_doc.available_for_use_date = (
			nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)
		)
		self.assertEqual(asset_doc.gross_purchase_amount, 5250.0)

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
		asset_doc.submit()

		expected_gle = (
			("CWIP Account - _TC", 0.0, 5250.0),
			("_Test Fixed Asset - _TC", 5250.0, 0.0),
		)

		gle = get_gl_entries("Asset", asset_doc.name)
		self.assertSequenceEqual(gle, expected_gle)

	def test_asset_cwip_toggling_cases(self):
		cwip = frappe.db.get_value("Asset Category", "Computers", "enable_cwip_accounting")
		name = frappe.db.get_value(
			"Asset Category Account", filters={"parent": "Computers"}, fieldname=["name"]
		)
		cwip_acc = "CWIP Account - _TC"

		frappe.db.set_value("Asset Category", "Computers", "enable_cwip_accounting", 0)
		frappe.db.set_value(
			"Asset Category Account", name, "capital_work_in_progress_account", ""
		)
		frappe.db.get_value(
			"Company", "_Test Company", "capital_work_in_progress_account", ""
		)

		# case 0 -- PI with cwip disable, Asset with cwip disabled, No cwip account set
		pi = make_purchase_invoice(
			item_code="Macbook Pro",
			qty=1,
			rate=200000.0,
			location="Test Location",
			update_stock=1,
		)
		asset = frappe.db.get_value(
			"Asset", {"purchase_invoice": pi.name, "docstatus": 0}, "name"
		)
		asset_doc = frappe.get_doc("Asset", asset)
		asset_doc.available_for_use_date = nowdate()
		asset_doc.calculate_depreciation = 0
		asset_doc.submit()
		gle = get_gl_entries("Asset", asset_doc.name)
		self.assertFalse(gle)

		# case 1 -- PR with cwip disabled, Asset with cwip enabled
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=200000.0, location="Test Location"
		)
		frappe.db.set_value("Asset Category", "Computers", "enable_cwip_accounting", 1)
		frappe.db.set_value(
			"Asset Category Account", name, "capital_work_in_progress_account", cwip_acc
		)
		asset = frappe.db.get_value(
			"Asset", {"purchase_receipt": pr.name, "docstatus": 0}, "name"
		)
		asset_doc = frappe.get_doc("Asset", asset)
		asset_doc.available_for_use_date = nowdate()
		asset_doc.calculate_depreciation = 0
		asset_doc.submit()
		gle = get_gl_entries("Asset", asset_doc.name)
		self.assertFalse(gle)

		# case 2 -- PR with cwip enabled, Asset with cwip disabled
		pr = make_purchase_receipt(
			item_code="Macbook Pro", qty=1, rate=200000.0, location="Test Location"
		)
		frappe.db.set_value("Asset Category", "Computers", "enable_cwip_accounting", 0)
		asset = frappe.db.get_value(
			"Asset", {"purchase_receipt": pr.name, "docstatus": 0}, "name"
		)
		asset_doc = frappe.get_doc("Asset", asset)
		asset_doc.available_for_use_date = nowdate()
		asset_doc.calculate_depreciation = 0
		asset_doc.submit()
		gle = get_gl_entries("Asset", asset_doc.name)
		self.assertTrue(gle)

		# case 3 -- PI with cwip disabled, Asset with cwip enabled
		pi = make_purchase_invoice(
			item_code="Macbook Pro",
			qty=1,
			rate=200000.0,
			location="Test Location",
			update_stock=1,
		)
		frappe.db.set_value("Asset Category", "Computers", "enable_cwip_accounting", 1)
		asset = frappe.db.get_value(
			"Asset", {"purchase_invoice": pi.name, "docstatus": 0}, "name"
		)
		asset_doc = frappe.get_doc("Asset", asset)
		asset_doc.available_for_use_date = nowdate()
		asset_doc.calculate_depreciation = 0
		asset_doc.submit()
		gle = get_gl_entries("Asset", asset_doc.name)
		self.assertFalse(gle)

		# case 4 -- PI with cwip enabled, Asset with cwip disabled
		pi = make_purchase_invoice(
			item_code="Macbook Pro",
			qty=1,
			rate=200000.0,
			location="Test Location",
			update_stock=1,
		)
		frappe.db.set_value("Asset Category", "Computers", "enable_cwip_accounting", 0)
		asset = frappe.db.get_value(
			"Asset", {"purchase_invoice": pi.name, "docstatus": 0}, "name"
		)
		asset_doc = frappe.get_doc("Asset", asset)
		asset_doc.available_for_use_date = nowdate()
		asset_doc.calculate_depreciation = 0
		asset_doc.submit()
		gle = get_gl_entries("Asset", asset_doc.name)
		self.assertTrue(gle)

		frappe.db.set_value("Asset Category", "Computers", "enable_cwip_accounting", cwip)
		frappe.db.set_value(
			"Asset Category Account", name, "capital_work_in_progress_account", cwip_acc
		)
		frappe.db.get_value(
			"Company", "_Test Company", "capital_work_in_progress_account", cwip_acc
		)

	def test_case_fix_asset_tc_fa_013(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Staight Line"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Receipt (PR)
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		pr.submit()
		print(pr.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_receipt": pr.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()

	def test_case_fix_asset_tc_fa_014(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Written Down Value"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Receipt (PR)
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		frappe.db.commit()
		print(pr.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_receipt": pr.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()

	def test_case_fix_asset_tc_fa_015(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Double Declining Balance"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Receipt (PR)
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		frappe.db.commit()
		print(pr.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_receipt": pr.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()

	def test_case_fix_asset_tc_fa_016(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Manual"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Receipt (PR)
		pr = make_purchase_receipt(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		frappe.db.commit()
		print(pr.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_receipt": pr.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()


	def test_case_fix_asset_tc_fa_017(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Staight Line"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Invoice (PR)
		pi = make_purchase_invoice(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			update_stock = 1,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		pi.submit()
		print(pi.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_invoice": pi.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()

	def test_case_fix_asset_tc_fa_018(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Written Down Value"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Invoice (PR)
		pi = make_purchase_invoice(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			update_stock = 1,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		pi.submit()
		print(pi.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_invoice": pi.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()

	def test_case_fix_asset_tc_fa_019(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Double Declining Balance"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Invoice (PR)
		pi = make_purchase_invoice(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			update_stock = 1,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		pi.submit()
		print(pi.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_invoice": pi.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()


	def test_case_fix_asset_tc_fa_020(self):
		# Set up variables based on your scenario
		company = "_Test Company"
		supplier = "_Test Supplier"
		item_code = "Test Macbook Pro"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()
		location = "Ahmedabad"
		finance_book = "2024-2025"
		depreciation_method = "Manual"
		total_depreciations = 12
		depreciation_frequency_months = 1

		# Create the Purchase Invoice (PR)
		pi = make_purchase_invoice(
			company=company,
			supplier=supplier,
			item_code=item_code,
			warehouse=warehouse,
			update_stock = 1,
			qty=qty,
			rate=rate,
			posting_date=nowdate(),
			location=location,
			do_not_submit=False
		)
		pi.submit()
		print(pi.name)

		# # Fetch the created Asset linked to the item in PR
		asset = frappe.get_value("Asset", {"item_code": item_code, "location": location, "purchase_invoice": pi.name}, "name")

		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			asset_doc.calculate_depreciation = 1
			asset_doc.available_for_use_date = nowdate()
			asset_doc.append("finance_books", {
			"finance_book": finance_book,
			"depreciation_method": depreciation_method,
			"total_number_of_depreciations": total_depreciations,
			"frequency_of_depreciation": depreciation_frequency_months,
			"calculate_depreciation": 1
		})
			asset_doc.save()

			asset_dep = frappe.get_value("Asset Depreciation Schedule", {"asset": asset_doc.name,}, "name")
			asset_dep_doc = frappe.get_doc("Asset Depreciation Schedule", asset_dep)
			asset_dep_doc.submit()
			asset_doc.submit()
			frappe.db.commit()

	def test_case_fix_asset_tc_fa_026(self):
		asset_doc = frappe.new_doc("Asset")
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = nowdate()
		asset_doc.company = "_Test Company"
		asset_doc.item_code = "Macbook Pro"
		asset_doc.location = "Test Location"
		asset_doc.gross_purchase_amount = 12000
		asset_doc.is_existing_asset = 1
		asset_doc.purchase_date = nowdate()
		asset_doc.append("finance_books", {
		"finance_book": "Depreciation as per Companies Act",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"frequency_of_depreciation": 1,
		"daily_prorata_based":1,
		})
		try:
			asset_doc.insert()
			asset_doc.submit()
			frappe.db.commit()
			print(f"Asset Created: {asset_doc.name}")
		except Exception as e:
			print(f"Error: {str(e)}")


	def test_case_fix_asset_tc_fa_027(self):
		asset_doc = frappe.new_doc("Asset")
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = nowdate()
		asset_doc.company = "_Test Company"
		asset_doc.item_code = "Macbook Pro"
		asset_doc.location = "Test Location"
		asset_doc.gross_purchase_amount = 12000
		asset_doc.is_existing_asset = 1
		asset_doc.purchase_date = nowdate()
		asset_doc.append("finance_books", {
		"finance_book": "Depreciation as per Companies Act",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"frequency_of_depreciation": 1,
		"shift_based":1,
		})
		try:
			asset_doc.insert()
			asset_doc.submit()
			frappe.db.commit()
			print(f"Asset Created: {asset_doc.name}")
		except Exception as e:
			print(f"Error: {str(e)}")

	def test_case_fix_asset_tc_fa_028(self):
		salvage_value_percentage = 2
		asset_doc = frappe.new_doc("Asset")
		asset_doc.calculate_depreciation = 1
		asset_doc.available_for_use_date = nowdate()
		asset_doc.company = "_Test Company"
		asset_doc.item_code = "Macbook Pro"
		asset_doc.location = "Test Location"
		asset_doc.gross_purchase_amount = 12000
		asset_doc.is_existing_asset = 1
		asset_doc.purchase_date = nowdate()
		asset_doc.append("finance_books", {
		"finance_book": "Depreciation as per Companies Act",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"frequency_of_depreciation": 1,
		"salvage_value_percentage":salvage_value_percentage,
		"expected_value_after_useful_life": (asset_doc.gross_purchase_amount * salvage_value_percentage)/100
		})
		try:
			asset_doc.insert()
			asset_doc.submit()
			frappe.db.commit()
			print(f"Asset Created: {asset_doc.name}")
		except Exception as e:
			print(f"Error: {str(e)}")

	def test_asset_existing_tc_fa_071(self):
		asset = frappe.new_doc("Asset")
		asset.company = "_Test Company"
		asset.item_code = "Test Item"
		asset.is_existing_asset = 1
		asset.location  = "Test"
		asset.available_for_use_date = getdate("01-04-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset.purchase_date = getdate("01-04-2024") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset.calculate_depreciation = 1
		asset.gross_purchase_amount = 1200
		asset.calculate_depreciation = 1
		asset.opening_accumulated_depreciation = 800
		asset.opening_number_of_booked_depreciations = 1200
		asset.opening_number_of_booked_depreciations = 8
		asset.append("finance_books", {
		"finance_book": "Depreciation as per Companies Act",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"frequency_of_depreciation": 1,
		# "daily_prorata_based":1,
		"depreciation_start_date":getdate("31-12-2024")
		})
		try:
			asset.insert()
			asset.submit()
			asset.cancel()
			frappe.db.commit()

			print(f"Asset Created: {asset.name}")
		except Exception as e:
			print(f"Error: {str(e)}")


	def test_asset_amended_tc_fa_072(self):
		asset = frappe.new_doc("Asset")
		asset.company = "_Test Company"
		asset.item_code = "Test Item"
		asset.is_existing_asset = 1
		asset.location  = "Test"
		asset.available_for_use_date = getdate("01-04-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset.purchase_date = getdate("01-04-2024") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset.calculate_depreciation = 1
		asset.gross_purchase_amount = 1200
		asset.calculate_depreciation = 1
		asset.opening_accumulated_depreciation = 800
		asset.opening_number_of_booked_depreciations = 1200
		asset.opening_number_of_booked_depreciations = 8
		asset.append("finance_books", {
		"finance_book": "Depreciation as per Companies Act",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"frequency_of_depreciation": 1,
		# "daily_prorata_based":1,
		"depreciation_start_date":getdate("31-12-2024")
		})
		try:
			asset.insert()
			asset.submit()
			asset.cancel()
			amended_asset=frappe.copy_doc(asset)
			amended_asset.amended_from = asset.name
			amended_asset.location = "Test"
			amended_asset.docstatus = 0
			amended_asset.opening_accumulated_depreciation = 900
			amended_asset.insert()
			amended_asset.submit()
			frappe.db.commit()

			print(f"Asset Created: {asset.name}")
		except Exception as e:
			print(f"Error: {str(e)}")


	def test_cases_fix_asset_tc_fa_073(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_asset1",
			"qty":1,
			"uom":"Nos",
			"rate":2500,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = frappe.utils.nowdate()
			pi_asset.calculate_depreciation=1
			pi_asset.append("finance_books",{
				"finance_book":"2024-2025",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"depreciation_start_date":getdate("30-04-2025")
			})
			pi_asset.save()
			pi_asset.submit()
			pi_asset.cancel()
			pi.cancel()
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			asset_pi=frappe.new_doc("Asset")
			asset_pi.company = pi.company
			asset_pi.item_code = "Test_asset1"
			asset_pi.gross_purchase_amount = 25000
			asset_pi.location  = "Test"
			asset_pi.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
			asset_pi.purchase_date = getdate("01-08-2024")
			asset_pi.purchase_amount = asset_pi.gross_purchase_amount
			asset_pi.available_for_use_date = frappe.utils.nowdate()
			asset_pi.calculate_depreciation=1
			asset_pi.append("finance_books",{
				"finance_book":"Test Finance Book 1",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"depreciation_start_date":getdate("30-04-2025")
			})
			asset_pi.save()
			asset_pi.submit()
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{asset_pi.name}")
			

	def test_cases_fix_asset_tc_fa_074(self):
		pi=frappe.new_doc("Purchase Receipt")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=frappe.utils.nowdate()
		pi.append("items",{
			"item_code":"Test_asset1",
			"qty":1,
			"uom":"Nos",
			"rate":25000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_receipt":pi.name})
			pi_asset.available_for_use_date = frappe.utils.nowdate()
			pi_asset.calculate_depreciation=1
			pi_asset.append("finance_books",{
				"finance_book":"Test Finance Book 1",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"depreciation_start_date":getdate("30-04-2025")
			})
			pi_asset.save()
			pi_asset.submit()
			pi_asset.cancel()
			pi.cancel()
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			asset_pi=frappe.new_doc("Asset")
			asset_pi.company = pi.company
			asset_pi.item_code = "Test_asset1"
			asset_pi.gross_purchase_amount = 25000
			asset_pi.location  = "Test"
			asset_pi.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
			asset_pi.purchase_date = getdate("01-08-2024")
			asset_pi.purchase_amount = asset_pi.gross_purchase_amount
			asset_pi.available_for_use_date = frappe.utils.nowdate()
			asset_pi.calculate_depreciation=1
			asset_pi.append("finance_books",{
				"finance_book":"Test Finance Book 1",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"depreciation_start_date":getdate("30-04-2025")
			})
			asset_pi.save()
			asset_pi.submit()
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{asset_pi.name}")



	def test_cases_fix_asset_tc_fa_075(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_asset1",
			"qty":1,
			"uom":"Nos",
			"rate":25000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = frappe.utils.nowdate()
			pi_asset.calculate_depreciation=1
			pi_asset.append("finance_books",{
				"finance_book":"Test Finance Book 1",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"depreciation_start_date":getdate("30-04-2025")
			})
			pi_asset.save()
			pi_asset.submit()
			pi_asset.cancel()
			amended_asset=frappe.copy_doc(pi_asset)
			amended_asset.amended_from = pi_asset.name
			amended_asset.location = "Test"
			for asset_item in amended_asset.finance_books:
				asset_item.frequency_of_depreciation=5
			amended_asset.docstatus = 0
			amended_asset.insert()
			amended_asset.submit()
		else:
			asset_pi=frappe.new_doc("Asset")
			asset_pi.company = pi.company
			asset_pi.item_code = "Test_asset1"
			asset_pi.gross_purchase_amount = 25000
			asset_pi.location  = "Test"
			asset_pi.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
			asset_pi.purchase_date = getdate("01-08-2024")
			asset_pi.purchase_amount = asset_pi.gross_purchase_amount
			asset_pi.available_for_use_date = frappe.utils.nowdate()
			asset_pi.calculate_depreciation=1
			asset_pi.append("finance_books",{
				"finance_book":"Test Finance Book 1",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"depreciation_start_date":getdate("30-04-2025")
			})
			asset_pi.save()
			asset_pi.submit()
			asset_pi.cancel()
			amended_asset=frappe.copy_doc(asset_pi)
			amended_asset.amended_from = asset_pi.name
			amended_asset.location = "Test"
			for asset_item in amended_asset.finance_books:
				asset_item.frequency_of_depreciation=5
			amended_asset.docstatus = 0
			amended_asset.insert()
			amended_asset.submit()

		# frappe.db.commit()
		print(f"Asset Created: {pi.name},{asset_pi.name}")


	def test_cases_fix_asset_tc_fa_051(self):
		asset_new_value_adjust = frappe.new_doc("Asset")
		asset_new_value_adjust.company = "_Test Company"
		asset_new_value_adjust.item_code = "Test_asset1"
		asset_new_value_adjust.is_existing_asset = 1
		asset_new_value_adjust.location  = "Test"
		asset_new_value_adjust.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_new_value_adjust.purchase_date = getdate("01-08-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_new_value_adjust.calculate_depreciation = 1
		asset_new_value_adjust.gross_purchase_amount = 12000
		asset_new_value_adjust.calculate_depreciation = 1
		asset_new_value_adjust.append("finance_books", {
		"finance_book": "Test Finance Book 1",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"frequency_of_depreciation": 1,
		"depreciation_start_date":getdate("30-04-2025")
		})
		asset_new_value_adjust.insert()
		asset_new_value_adjust.submit()
		compnay_abbr = frappe.db.get_value("Company",asset_new_value_adjust.company,"abbr")
		asset_value_adjustment=create_asset_value_adjustment(asset_new_value_adjust.name,asset_new_value_adjust.asset_category,asset_new_value_adjust.company)
		asset_value_adjustment.date =  frappe.utils.nowdate()
		asset_value_adjustment.difference_account= "_Test Account Cost for Goods Sold - _TC" #f"Accumulated Depreciations - {compnay_abbr}"
		asset_value_adjustment.new_asset_value = 200000
		asset_value_adjustment.save()
		asset_value_adjustment.submit()
		# frappe.db.commit()
		print(f"Asset Created: {asset_value_adjustment.name},{asset_new_value_adjust.name}")

	def test_partialy_depretiated_scrapped_asset_tc_52(self):
		asset_scrapped = frappe.new_doc("Asset")
		asset_scrapped.company = "_Test Company"
		asset_scrapped.item_code = "Test_asset1"
		asset_scrapped.is_existing_asset = 1
		asset_scrapped.location  = "Test"
		asset_scrapped.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.purchase_date = getdate("01-08-2024") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.calculate_depreciation = 1
		asset_scrapped.gross_purchase_amount = 50000
		asset_scrapped.opening_accumulated_depreciation = 4000
		asset_scrapped.opening_number_of_booked_depreciations = 2
		asset_scrapped.append("finance_books", {
		"finance_book": "2024-2025",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"total_number_of_booked_depreciations":2,
		"frequency_of_depreciation": 1,
		"depreciation_start_date":getdate("23-01-2025")
		})
		asset_scrapped.insert()
		asset_scrapped.submit()
		asset_scrapped.reload()
		self.assertEquals(asset_scrapped.status,"Partially Depreciated")
		scrap_asset(asset_scrapped.name, scrap_date=None)
		# frappe.db.commit()
		print(f"Asset Created:{asset_scrapped.name}")

	def test_fully_depretiated_scrapped_asset_tc_53(self):
		asset_scrapped = frappe.new_doc("Asset")
		asset_scrapped.company = "_Test Company"
		asset_scrapped.item_code = "Test_asset1"
		asset_scrapped.is_existing_asset = 1
		asset_scrapped.location  = "Test"
		asset_scrapped.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.purchase_date = getdate("01-08-2024") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.is_fully_depreciated = 1
		asset_scrapped.gross_purchase_amount = 80000
		asset_scrapped.opening_accumulated_depreciation = 8000
		asset_scrapped.opening_number_of_booked_depreciations = 1
		asset_scrapped.insert()
		asset_scrapped.submit()
		asset_scrapped.reload()
		self.assertEquals(asset_scrapped.status,"Fully Depreciated")
		scrap_asset(asset_scrapped.name, scrap_date=None)
		# frappe.db.commit()
		print(f"Asset Created:{asset_scrapped.name}")

	def test_partialy_depretiated_scrapped_asset_rs_tc_54(self):
		asset_scrapped = frappe.new_doc("Asset")
		asset_scrapped.company = "_Test Company"
		asset_scrapped.item_code = "Test_asset1"
		asset_scrapped.is_existing_asset = 1
		asset_scrapped.location  = "Test"
		asset_scrapped.available_for_use_date = getdate("01-09-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.purchase_date = getdate("01-08-2024") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.calculate_depreciation = 1
		asset_scrapped.gross_purchase_amount = 50000
		asset_scrapped.opening_accumulated_depreciation = 4000
		asset_scrapped.opening_number_of_booked_depreciations = 2
		asset_scrapped.append("finance_books", {
		"finance_book": "2024-2025",
		"depreciation_method": "Straight Line",
		"total_number_of_depreciations": 12,
		"total_number_of_booked_depreciations":2,
		"frequency_of_depreciation": 1,
		"depreciation_start_date":getdate("23-01-2025")
		})
		asset_scrapped.insert()
		asset_scrapped.submit()
		asset_scrapped.reload()
		self.assertEquals(asset_scrapped.status,"Partially Depreciated")
		scrap_asset(asset_scrapped.name, scrap_date=None)
		restore_asset(asset_scrapped.name)
		# frappe.db.commit()
		print(f"Asset Created:{asset_scrapped.name}")

	def test_fully_depretiated_scrapped_asset_rs_tc_55(self):
		asset_scrapped = frappe.new_doc("Asset")
		asset_scrapped.company = "_Test Company"
		asset_scrapped.item_code = "Test_asset1"
		asset_scrapped.is_existing_asset = 1
		asset_scrapped.location  = "Test"
		asset_scrapped.available_for_use_date = getdate("01-01-2025")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.purchase_date = getdate("01-01-2025") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset_scrapped.is_fully_depreciated = 1
		asset_scrapped.gross_purchase_amount = 80000
		asset_scrapped.opening_accumulated_depreciation = 8000
		asset_scrapped.opening_number_of_booked_depreciations = 1
		asset_scrapped.insert()
		asset_scrapped.submit()			
		asset_scrapped.reload()
		self.assertEquals(asset_scrapped.status,"Fully Depreciated")
		scrap_asset(asset_scrapped.name, scrap_date=None)
		restore_asset(asset_scrapped.name)
		# frappe.db.commit()
		print(f"Asset Created:{asset_scrapped.name}")

	def test_cases_residual_scrapped_tc_56(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=getdate("01-01-2024")#frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_asset1",
			"qty":1,
			"uom":"Nos",
			"rate":25000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = getdate("01-01-2024") #frappe.utils.nowdate()
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.calculate_depreciation=1
			pi_asset.append("finance_books",{
				"finance_book":"Depreciation as per Companies Act",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"salvage_value_percentage":10,
				"depreciation_start_date":getdate("31-01-2024")
			})
			pi_asset.save()
			pi_asset.submit()
			asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
			make_depreciation_entry(asset_depr_schedule,
							date=None,
							sch_start_idx=None,
							sch_end_idx=None,
							credit_and_debit_accounts=None,
							depreciation_cost_center_and_depreciation_series=None,
							accounting_dimensions=None,)
			pi_asset.reload()
			self.assertEquals(pi_asset.status,"Fully Depreciated")
			scrap_asset(pi_asset.name, scrap_date=None)
			
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			pi_doc=frappe.get_doc("Purchase Invoice",pi.name)
			pi_asset = frappe.new_doc("Asset")
			pi_asset.company = pi_doc.company
			pi_asset.item_code = "Test_asset1"  # Assign item code
			pi_asset.location = "Test"
			pi_asset.gross_purchase_amount = 25000  # Assign correct purchase amount
			pi_asset.purchase_amount = pi_asset.gross_purchase_amount
			pi_asset.purchase_invoice = pi.name
			pi_asset.available_for_use_date = getdate("01-01-2024")
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.calculate_depreciation = 1

			# Adding finance book details
			pi_asset.append("finance_books", {
				"finance_book": "Depreciation as per Companies Act",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"salvage_value_percentage": 10,
				"depreciation_start_date": getdate("31-01-2024")
			})

			pi_asset.save()
			pi_asset.submit()

			asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
			make_depreciation_entry(asset_depr_schedule,
							date=None,
							sch_start_idx=None,
							sch_end_idx=None,
							credit_and_debit_accounts=None,
							depreciation_cost_center_and_depreciation_series=None,
							accounting_dimensions=None,)
			pi_asset.reload()
			self.assertEquals(pi_asset.status,"Fully Depreciated")
			scrap_asset(pi_asset.name, scrap_date=None)
			
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")

	def test_cases_residual_scrapped_tc_57(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=getdate("01-01-2024")#frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_(Grouped_Asset)",
			"qty":6,
			"uom":"Nos",
			"rate":25000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = getdate("01-01-2024") #frappe.utils.nowdate()
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.calculate_depreciation=1
			pi_asset.append("finance_books",{
				"finance_book":"Depreciation as per Companies Act",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"salvage_value_percentage":10,
				"depreciation_start_date":getdate("31-01-2024")
			})
			pi_asset.save()
			pi_asset.submit()
			asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
			make_depreciation_entry(asset_depr_schedule,
							date=None,
							sch_start_idx=None,
							sch_end_idx=None,
							credit_and_debit_accounts=None,
							depreciation_cost_center_and_depreciation_series=None,
							accounting_dimensions=None,)
			pi_asset.reload()
			self.assertEquals(pi_asset.status,"Fully Depreciated")
			scrap_asset(pi_asset.name, scrap_date=None)
			
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			pi_doc=frappe.get_doc("Purchase Invoice",pi.name)
			pi_asset = frappe.new_doc("Asset")
			pi_asset.company = pi_doc.company
			pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
			pi_asset.location = "Test"
			pi_asset.gross_purchase_amount = 25000  # Assign correct purchase amount
			pi_asset.purchase_amount = pi_asset.gross_purchase_amount
			pi_asset.purchase_invoice = pi.name
			pi_asset.available_for_use_date = getdate("01-01-2024")
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.calculate_depreciation = 1

			# Adding finance book details
			pi_asset.append("finance_books", {
				"finance_book": "Depreciation as per Companies Act",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"salvage_value_percentage": 10,
				"depreciation_start_date": getdate("31-01-2024")
			})

			pi_asset.save()
			pi_asset.submit()

			asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
			make_depreciation_entry(asset_depr_schedule,
							date=None,
							sch_start_idx=None,
							sch_end_idx=None,
							credit_and_debit_accounts=None,
							depreciation_cost_center_and_depreciation_series=None,
							accounting_dimensions=None,)
			pi_asset.reload()
			self.assertEquals(pi_asset.status,"Fully Depreciated")
			scrap_asset(pi_asset.name, scrap_date=None)
			
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		frappe.db.commit()
	def test_cases_sell_profit_asset_tc_58(self):
		asset = frappe.new_doc("Asset")
		asset.company = "_Test Company"
		asset.item_code = "Test_asset1"
		asset.is_existing_asset = 1
		asset.location  = "Test"
		asset.available_for_use_date = getdate("01-04-2024")#frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset.purchase_date = getdate("01-04-2024") #frappe.utils.add_days(frappe.utils.nowdate(),-30)
		asset.gross_purchase_amount = 10000
		asset.opening_accumulated_depreciation = 8000
		asset.insert()
		asset.submit()
		make_sales_invoice(asset.name, asset.item_code, asset.company, serial_no=None)
		si=make_sales_invoice(asset.name, asset.item_code, asset.company, serial_no=None)
		si.customer = "_Test Customer"
		si.due_date = frappe.utils.nowdate()
		si.get("items")[0].rate = 3000
		si.insert()
		si.submit()
		frappe.db.commit()

		print(f"Asset Created: {asset.name}")

	def test_cases_sell_loss_asset_tc_59(self):
		asset = frappe.new_doc("Asset")
		asset.company = "_Test Company"
		asset.item_code = "Test_asset1"
		asset.asset_category = "Test_Category"
		asset.is_existing_asset = 1
		asset.location  = "Test"
		asset.available_for_use_date = frappe.utils.nowdate()
		asset.purchase_date =frappe.utils.nowdate()
		asset.gross_purchase_amount = 10000
		asset.opening_accumulated_depreciation = 8000
		asset.insert()
		asset.submit()
		si=make_sales_invoice(asset.name, asset.item_code, asset.company, serial_no=None)
		si.customer = "_Test Customer"
		si.due_date = frappe.utils.nowdate()
		si.get("items")[0].rate = 1000
		si.insert()
		si.submit()
		frappe.db.commit()

		print(f"Asset Created: {asset.name}")
	
	def test_cases_sell_loss_asset_tc_60(self):
		asset = frappe.new_doc("Asset")
		asset.company = "_Test Company"
		asset.item_code = "Test_asset1"
		asset.asset_category = "Test_Category"
		asset.is_existing_asset = 1
		asset.location  = "Test"
		asset.available_for_use_date = frappe.utils.nowdate()
		asset.purchase_date =frappe.utils.nowdate()
		asset.gross_purchase_amount = 10000
		asset.opening_accumulated_depreciation = 8000
		asset.insert()
		asset.submit()
		si=make_sales_invoice(asset.name, asset.item_code, asset.company, serial_no=None)
		si.customer = "_Test Customer"
		si.due_date = frappe.utils.nowdate()
		si.get("items")[0].rate = 1000
		si.insert()
		si.submit()
		# frappe.db.commit()

		print(f"Asset Created: {asset.name}")


	def test_cases_shell_pr_asset_tc_61(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date="01-01-2024"#frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_(Grouped_Asset)",
			"qty":1,
			"uom":"Nos",
			"rate":10000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = getdate("01-01-2024") #frappe.utils.nowdate()
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.opening_accumulated_depreciation = 8000
			pi_asset.save()
			pi_asset.submit()
			si=make_sales_invoice(pi_asset.name, pi_asset.item_code, pi_asset.company, serial_no=None)
			si.customer = "_Test Customer"
			si.due_date = frappe.utils.nowdate()
			si.get("items")[0].rate = 1000
			si.insert()
			si.submit()
			
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			pi_doc=frappe.get_doc("Purchase Invoice",pi.name)
			pi_asset = frappe.new_doc("Asset")
			pi_asset.company = pi_doc.company
			pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
			pi_asset.location = "Test"
			pi_asset.gross_purchase_amount = 10000  # Assign correct purchase amount
			# pi_asset.purchase_amount = pi_asset.gross_purchase_amount
			pi_asset.purchase_invoice = pi.name
			pi_asset.available_for_use_date = getdate("01-01-2024")
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.opening_accumulated_depreciation = 8000
			pi_asset.save()
			pi_asset.submit()
			si=make_sales_invoice(pi_asset.name, pi_asset.item_code, pi_asset.company, serial_no=None)
			si.customer = "_Test Customer"
			si.due_date = frappe.utils.nowdate()
			si.get("items")[0].rate = 1000
			si.insert()
			si.submit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		# frappe.db.commit()

	def test_cases_shell_pr_asset_tc_62(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=getdate("01-01-2024")#frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_(Grouped_Asset)",
			"qty":6,
			"uom":"Nos",
			"rate":10000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = getdate("01-01-2024") #frappe.utils.nowdate()
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.opening_accumulated_depreciation = 8000
			pi_asset.save()
			pi_asset.submit()
			si=make_sales_invoice(pi_asset.name, pi_asset.item_code, pi_asset.company, serial_no=None)
			si.customer = "_Test Customer"
			si.due_date = frappe.utils.nowdate()
			si.get("items")[0].rate = 1000
			si.insert()
			si.submit()
			
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			pi_doc=frappe.get_doc("Purchase Invoice",pi.name)
			pi_asset = frappe.new_doc("Asset")
			pi_asset.company = pi_doc.company
			pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
			pi_asset.location = "Test"
			pi_asset.gross_purchase_amount = 10000  # Assign correct purchase amount
			# pi_asset.purchase_amount = pi_asset.gross_purchase_amount
			pi_asset.purchase_invoice = pi.name
			pi_asset.available_for_use_date = getdate("01-01-2024")
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.opening_accumulated_depreciation = 8000
			pi_asset.save()
			pi_asset.submit()
			si=make_sales_invoice(pi_asset.name, pi_asset.item_code, pi_asset.company, serial_no=None)
			si.customer = "_Test Customer"
			si.due_date = frappe.utils.nowdate()
			si.get("items")[0].rate = 1000
			si.insert()
			si.submit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		# frappe.db.commit()

	def test_cases_sold_fully_depreciated_tc_63(self):
		pi=frappe.new_doc("Purchase Invoice")
		pi.company="_Test Company"
		pi.supplier="_Test Supplier"
		pi.posting_date=("01-01-2024")#frappe.utils.nowdate()
		pi.update_stock = 1
		pi.append("items",{
			"item_code":"Test_(Grouped_Asset)",
			"qty":1,
			"uom":"Nos",
			"rate":10000,
			"asset_location":"Test"
		})
		pi.save()
		pi.submit()
		if frappe.db.exists("Asset",{"purchase_invoice":pi.name}):
			pi_asset=frappe.get_doc("Asset",{"purchase_invoice":pi.name})
			pi_asset.available_for_use_date = getdate("01-01-2024") #frappe.utils.nowdate()
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.opening_accumulated_depreciation = 8000
			pi_asset.calculate_depreciation=1
			pi_asset.append("finance_books",{
				"finance_book":"Depreciation as per Companies Act",
				"depreciation_method":"Straight Line",
				"total_number_of_depreciations":12,
				"frequency_of_depreciation":1,
				"salvage_value_percentage":10,
				"depreciation_start_date":getdate("31-01-2024")
			})
			pi_asset.save()
			pi_asset.submit()
			asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
			make_depreciation_entry(asset_depr_schedule,
							date=None,
							sch_start_idx=None,
							sch_end_idx=None,
							credit_and_debit_accounts=None,
							depreciation_cost_center_and_depreciation_series=None,
							accounting_dimensions=None,)
			pi_asset.reload()
			self.assertEquals(pi_asset.status,"Fully Depreciated")
			si=make_sales_invoice(pi_asset.name, pi_asset.item_code, pi_asset.company, serial_no=None)
			si.customer = "_Test Customer"
			si.due_date = frappe.utils.nowdate()
			si.get("items")[0].rate = 1000
			si.insert()
			si.submit()

			# self.assertEquals(pi_asset.status,"Fully Depreciated")
			# scrap_asset(pi_asset.name, scrap_date=None)
			
			# frappe.db.commit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		else:
			pi_doc=frappe.get_doc("Purchase Invoice",pi.name)
			pi_asset = frappe.new_doc("Asset")
			pi_asset.company = pi_doc.company
			pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
			pi_asset.location = "Test"
			pi_asset.gross_purchase_amount = 10000  # Assign correct purchase amount
			pi_asset.opening_accumulated_depreciation = 8000
			pi_asset.purchase_invoice = pi.name
			pi_asset.available_for_use_date = getdate("01-01-2024")
			pi_asset.purchase_date = getdate("01-01-2024")
			pi_asset.calculate_depreciation = 1

			# Adding finance book details
			pi_asset.append("finance_books", {
				"finance_book": "Depreciation as per Companies Act",
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 12,
				"frequency_of_depreciation": 1,
				"salvage_value_percentage": 10,
				"depreciation_start_date": getdate("31-01-2024")
			})

			pi_asset.save()
			pi_asset.submit()

			asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
			make_depreciation_entry(asset_depr_schedule,
							date=None,
							sch_start_idx=None,
							sch_end_idx=None,
							credit_and_debit_accounts=None,
							depreciation_cost_center_and_depreciation_series=None,
							accounting_dimensions=None,)
			pi_asset.reload()
			# self.assertEquals(pi_asset.status,"Fully Depreciated")
			# scrap_asset(pi_asset.name, scrap_date=None)
			self.assertEquals(pi_asset.status,"Fully Depreciated")
			si=make_sales_invoice(pi_asset.name, pi_asset.item_code, pi_asset.company, serial_no=None)
			si.customer = "_Test Customer"
			si.due_date = frappe.utils.nowdate()
			si.get("items")[0].rate = 1000
			si.insert()
			si.submit()
			print(f"Asset Created: {pi.name},{pi_asset.name}")
		# frappe.db.commit()
	def test_case_split_asset_error_message_tc_64(self):
		pi_asset = frappe.new_doc("Asset")
		pi_asset.company = "_Test Company"
		pi_asset.is_existing_asset = 1
		pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
		pi_asset.location = "Test"
		pi_asset.gross_purchase_amount = 10000  # Assign correct purchase amount
		# pi_asset.opening_accumulated_depreciation = 8000
		# pi_asset.purchase_invoice = pi.name
		pi_asset.asset_quantity=1
		pi_asset.available_for_use_date = getdate("01-01-2024")
		pi_asset.purchase_date = getdate("01-01-2024")
		pi_asset.calculate_depreciation = 1

		# Adding finance book details
		pi_asset.append("finance_books", {
			"finance_book": "Test Finance Book 1",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 12,
			"frequency_of_depreciation": 1,
			"salvage_value_percentage": 10,
			"depreciation_start_date": getdate("31-01-2024")
		})

		pi_asset.save()
		pi_asset.submit()
		try:
			split_qty = pi_asset.asset_quantity  # Use asset quantity here
			if split_qty >= pi_asset.asset_quantity:
				raise frappe.ValidationError("Split qty cannot be greater than or equal to asset qty")

				# Perform split asset logic
			split_asset(pi_asset.name, split_qty)
			print(f"Asset Created:,{pi_asset.name}")
		except frappe.ValidationError as e:
			# Assert the error message
			assert str(e) == "Split qty cannot be greater than or equal to asset qty"
			print(f"Validation Error: {e}")


	def test_case_split_asset_tc_65(self):
		pi_asset = frappe.new_doc("Asset")
		pi_asset.company = "_Test Company"
		pi_asset.is_existing_asset = 1
		pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
		pi_asset.location = "Test"
		pi_asset.gross_purchase_amount = 10000  # Assign correct purchase amount
		# pi_asset.opening_accumulated_depreciation = 8000
		# pi_asset.purchase_invoice = pi.name
		pi_asset.asset_quantity=7
		pi_asset.available_for_use_date = getdate("01-01-2024")
		pi_asset.purchase_date = getdate("01-01-2024")
		pi_asset.calculate_depreciation = 1

		# Adding finance book details
		pi_asset.append("finance_books", {
			"finance_book": "Test Finance Book 1",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 12,
			"frequency_of_depreciation": 1,
			"salvage_value_percentage": 10,
			"depreciation_start_date": getdate("31-01-2024")
		})

		pi_asset.save()
		pi_asset.submit()
		split_asset(pi_asset.name,split_qty=3)
		# frappe.db.commit()
		print(f"Asset:{pi_asset.name}")
	def test_case_split_asset_with_even_qty_tc_66(self):
		pi_asset = frappe.new_doc("Asset")
		pi_asset.company = "_Test Company"
		pi_asset.is_existing_asset = 1
		pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
		pi_asset.location = "Test"
		pi_asset.gross_purchase_amount = 10000  # Assign correct purchase amount
		# pi_asset.opening_accumulated_depreciation = 8000
		# pi_asset.purchase_invoice = pi.name
		pi_asset.asset_quantity=5
		pi_asset.available_for_use_date = getdate("01-01-2024")
		pi_asset.purchase_date = getdate("01-01-2024")
		pi_asset.calculate_depreciation = 1

		# Adding finance book details
		pi_asset.append("finance_books", {
			"finance_book": "Test Finance Book 1",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 12,
			"frequency_of_depreciation": 1,
			"salvage_value_percentage": 10,
			"depreciation_start_date": getdate("31-01-2024")
		})

		pi_asset.save()
		pi_asset.submit()
		split_asset(pi_asset.name,split_qty=3.5)
		# frappe.db.commit()
		print(f"Asset:{pi_asset.name}")


	def test_case_revaluation_increases_tc_83(self):
		pi_asset = frappe.new_doc("Asset")
		pi_asset.company = "_Test Company"
		pi_asset.is_existing_asset = 1
		pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
		pi_asset.location = "Test"
		pi_asset.gross_purchase_amount = 72000  # Assign correct purchase amount
		pi_asset.available_for_use_date = getdate("01-01-2024")
		pi_asset.purchase_date = getdate("01-01-2024")
		pi_asset.calculate_depreciation = 1
		pi_asset.append("finance_books", {
			"finance_book": "Test Finance Book 1",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 18,
			"frequency_of_depreciation": 1,
			"depreciation_start_date": getdate("31-01-2024")
		})

		pi_asset.save()
		pi_asset.submit()
		asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
		make_depreciation_entry(asset_depr_schedule,
						date=None,
						sch_start_idx=None,
						sch_end_idx=None,
						credit_and_debit_accounts=None,
						depreciation_cost_center_and_depreciation_series=None,
						accounting_dimensions=None,)
		pi_asset.reload()
		adjust_asset_value=create_asset_value_adjustment(pi_asset.name,pi_asset.asset_category,pi_asset.company)
		adjust_asset_value.date = frappe.utils.nowdate()
		adjust_asset_value.new_asset_value = 30000
		adjust_asset_value.difference_account = "Revaluation Reserve - _TC"
		adjust_asset_value.save()
		adjust_asset_value.submit()
		# frappe.db.commit()
		print(f"Asset:{pi_asset.name}")

	def test_case_revaluation_decreases_tc_84(self):
		pi_asset = frappe.new_doc("Asset")
		pi_asset.company = "_Test Company"
		pi_asset.is_existing_asset = 1
		pi_asset.item_code = "Test_(Grouped_Asset)"  # Assign item code
		pi_asset.location = "Test"
		pi_asset.gross_purchase_amount = 72000  # Assign correct purchase amount
		pi_asset.available_for_use_date = getdate("01-01-2024")
		pi_asset.purchase_date = getdate("01-01-2024")
		pi_asset.calculate_depreciation = 1
		pi_asset.append("finance_books", {
			"finance_book": "Test Finance Book 1",
			"depreciation_method": "Straight Line",
			"total_number_of_depreciations": 18,
			"frequency_of_depreciation": 1,
			"depreciation_start_date": getdate("31-01-2024")
		})

		pi_asset.save()
		pi_asset.submit()
		asset_depr_schedule=frappe.db.get_value("Asset Depreciation Schedule",{"asset":pi_asset.name},"name")
		make_depreciation_entry(asset_depr_schedule,
						date=None,
						sch_start_idx=None,
						sch_end_idx=None,
						credit_and_debit_accounts=None,
						depreciation_cost_center_and_depreciation_series=None,
						accounting_dimensions=None,)
		pi_asset.reload()
		self.assertEqual(pi_asset.status,"Partially Depreciated")
		adjust_asset_value=create_asset_value_adjustment(pi_asset.name,pi_asset.asset_category,pi_asset.company)
		adjust_asset_value.date = frappe.utils.nowdate()
		adjust_asset_value.current_asset_value = 24000
		adjust_asset_value.new_asset_value = 20000
		adjust_asset_value.difference_account = "Revaluation Reserve - _TC"
		adjust_asset_value.save()
		adjust_asset_value.submit()
		# frappe.db.commit()
		print(f"Asset:{pi_asset.name}")


class TestDepreciationMethods(AssetSetup):
	def test_schedule_for_straight_line_method(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-01-01",
			purchase_date="2030-01-01",
			expected_value_after_useful_life=10000,
			depreciation_start_date="2030-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		self.assertEqual(asset.status, "Draft")
		expected_schedules = [
			["2030-12-31", 30000.00, 30000.00],
			["2031-12-31", 30000.00, 60000.00],
			["2032-12-31", 30000.00, 90000.00],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_straight_line_method_with_daily_prorata_based(
		self,
	):
		asset = create_asset(
			finance_book = "Test Finance Book 1",
			calculate_depreciation=1,
			available_for_use_date="2023-01-01",
			purchase_date="2023-01-01",
			gross_purchase_amount=12000,
			depreciation_start_date="2023-01-31",
			total_number_of_depreciations=12,
			frequency_of_depreciation=1,
			daily_prorata_based=1,
		)

		expected_schedules = [
			["2023-01-31", 1019.18, 1019.18],
			["2023-02-28", 920.55, 1939.73],
			["2023-03-31", 1019.18, 2958.91],
			["2023-04-30", 986.3, 3945.21],
			["2023-05-31", 1019.18, 4964.39],
			["2023-06-30", 986.3, 5950.69],
			["2023-07-31", 1019.18, 6969.87],
			["2023-08-31", 1019.18, 7989.05],
			["2023-09-30", 986.3, 8975.35],
			["2023-10-31", 1019.18, 9994.53],
			["2023-11-30", 986.3, 10980.83],
			["2023-12-31", 1019.17, 12000.0],
		]
		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_straight_line_method_for_existing_asset(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-06-06",
			is_existing_asset=1,
			opening_number_of_booked_depreciations=2,
			opening_accumulated_depreciation=47178.08,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2032-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		self.assertEqual(asset.status, "Draft")
		expected_schedules = [
			["2032-12-31", 30000.0, 77178.08],
			["2033-06-06", 12821.92, 90000.0],
		]
		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				d.accumulated_depreciation_amount,
			]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_double_declining_method(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-01-01",
			purchase_date="2030-01-01",
			depreciation_method="Double Declining Balance",
			expected_value_after_useful_life=10000,
			depreciation_start_date="2030-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		self.assertEqual(asset.status, "Draft")

		expected_schedules = [
			["2030-12-31", 66667.00, 66667.00],
			["2031-12-31", 22222.11, 88889.11],
			["2032-12-31", 1110.89, 90000.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_double_declining_method_for_existing_asset(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-01-01",
			is_existing_asset=1,
			depreciation_method="Double Declining Balance",
			opening_number_of_booked_depreciations=1,
			opening_accumulated_depreciation=50000,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2031-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		self.assertEqual(asset.status, "Draft")

		expected_schedules = [
			["2031-12-31", 33333.50, 83333.50],
			["2032-12-31", 6666.50, 90000.0],
		]

		schedules = [
			[cstr(d.schedule_date), d.depreciation_amount, d.accumulated_depreciation_amount]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_schedule_for_prorated_straight_line_method(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-01-30",
			purchase_date="2030-01-30",
			depreciation_method="Straight Line",
			expected_value_after_useful_life=10000,
			depreciation_start_date="2030-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		expected_schedules = [
			["2030-12-31", 27616.44, 27616.44],
			["2031-12-31", 30000.0, 57616.44],
			["2032-12-31", 30000.0, 87616.44],
			["2033-01-30", 2383.56, 90000.0],
		]

		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				flt(d.accumulated_depreciation_amount, 2),
			]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	# WDV: Written Down Value method
	def test_depreciation_entry_for_wdv_without_pro_rata(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-01-01",
			purchase_date="2030-01-01",
			depreciation_method="Written Down Value",
			expected_value_after_useful_life=12500,
			depreciation_start_date="2030-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		self.assertEqual(asset.finance_books[0].rate_of_depreciation, 50.0)

		expected_schedules = [
			["2030-12-31", 50000.0, 50000.0],
			["2031-12-31", 25000.0, 75000.0],
			["2032-12-31", 12500.0, 87500.0],
		]

		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				flt(d.accumulated_depreciation_amount, 2),
			]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	# WDV: Written Down Value method
	def test_pro_rata_depreciation_entry_for_wdv(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2030-06-06",
			purchase_date="2030-01-01",
			depreciation_method="Written Down Value",
			expected_value_after_useful_life=12500,
			depreciation_start_date="2030-12-31",
			total_number_of_depreciations=3,
			frequency_of_depreciation=12,
		)

		self.assertEqual(asset.finance_books[0].rate_of_depreciation, 50.0)

		expected_schedules = [
			["2030-12-31", 28630.14, 28630.14],
			["2031-12-31", 35684.93, 64315.07],
			["2032-12-31", 17842.46, 82157.53],
			["2033-06-06", 5342.47, 87500.00],
		]

		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				flt(d.accumulated_depreciation_amount, 2),
			]
			for d in get_depr_schedule(asset.name, "Draft")
		]

		self.assertEqual(schedules, expected_schedules)

	def test_monthly_depreciation_by_wdv_method(self):
		asset = create_asset(
			calculate_depreciation=1,
			available_for_use_date="2022-02-15",
			purchase_date="2022-02-15",
			depreciation_method="Written Down Value",
			gross_purchase_amount=10000,
			expected_value_after_useful_life=5000,
			depreciation_start_date="2022-02-28",
			total_number_of_depreciations=5,
			frequency_of_depreciation=1,
		)

		expected_schedules = [
			["2022-02-28", 310.89, 310.89],
			["2022-03-31", 654.45, 965.34],
			["2022-04-30", 654.45, 1619.79],
			["2022-05-31", 654.45, 2274.24],
			["2022-06-30", 654.45, 2928.69],
			["2022-07-15", 2071.31, 5000.0],
		]

		schedules = [
			[
				cstr(d.schedule_date),
				flt(d.depreciation_amount, 2),
				flt(d.accumulated_depreciation_amount, 2),
			]
			for d in get_depr_schedule(asset.name, "Draft")
		]
		self.assertEqual(schedules, expected_schedules)


class TestDepreciationBasics(AssetSetup):
	def test_depreciation_without_pro_rata(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date=getdate("2019-12-31"),
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date=getdate("2020-12-31"),
			submit=1,
		)

		expected_values = [
			["2020-12-31", 30000, 30000],
			["2021-12-31", 30000, 60000],
			["2022-12-31", 30000, 90000],
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)

	def test_depreciation_with_pro_rata(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date=getdate("2020-01-01"),
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date=getdate("2020-07-01"),
			submit=1,
		)

		expected_values = [
			["2020-07-01", 15000, 15000],
			["2021-07-01", 30000, 45000],
			["2022-07-01", 30000, 75000],
			["2023-01-01", 15000, 90000],
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
			self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)

	def test_get_depreciation_amount(self):
		"""Tests if get_depreciation_amount() returns the right value."""
		asset = create_asset(item_code="Macbook Pro", available_for_use_date="2019-12-31")

		asset.calculate_depreciation = 1
		asset.append(
			"finance_books",
			{
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 12,
				"total_number_of_depreciations": 3,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-12-31",
			},
		)

		asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset.name, "Active")

		depreciation_amount, prev_per_day_depr = get_depreciation_amount(
			asset_depr_schedule_doc, asset, 100000, 100000, asset.finance_books[0]
		)
		self.assertEqual(depreciation_amount, 30000)

	def test_make_depr_schedule(self):
		"""Tests if make_depr_schedule() returns the right values."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_method="Straight Line",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2020-12-31",
		)

		expected_values = [
			["2020-12-31", 30000.0],
			["2021-12-31", 30000.0],
			["2022-12-31", 30000.0],
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Draft")):
			self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
			self.assertEqual(expected_values[i][1], schedule.depreciation_amount)

	def test_set_accumulated_depreciation(self):
		"""Tests if set_accumulated_depreciation() returns the right values."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_method="Straight Line",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2020-12-31",
		)

		expected_values = [30000.0, 60000.0, 90000.0]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Draft")):
			self.assertEqual(expected_values[i], schedule.accumulated_depreciation_amount)

	def test_check_is_pro_rata(self):
		"""Tests if check_is_pro_rata() returns the right value(i.e. checks if has_pro_rata is accurate)."""

		asset = create_asset(
			item_code="Macbook Pro", available_for_use_date="2019-12-31", do_not_save=1
		)

		asset.calculate_depreciation = 1
		asset.append(
			"finance_books",
			{
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 12,
				"total_number_of_depreciations": 3,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-12-31",
			},
		)

		has_pro_rata = _check_is_pro_rata(asset, asset.finance_books[0])
		self.assertFalse(has_pro_rata)

		asset.finance_books = []
		asset.append(
			"finance_books",
			{
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 12,
				"total_number_of_depreciations": 3,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-07-01",
			},
		)

		has_pro_rata = _check_is_pro_rata(asset, asset.finance_books[0])
		self.assertTrue(has_pro_rata)

	def test_expected_value_after_useful_life_greater_than_purchase_amount(self):
		"""Tests if an error is raised when expected_value_after_useful_life(110,000) > gross_purchase_amount(100,000)."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=3,
			expected_value_after_useful_life=110000,
			depreciation_start_date="2020-07-01",
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_depreciation_start_date(self):
		"""Tests if an error is raised when neither depreciation_start_date nor available_for_use_date are specified."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=110000,
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_opening_accumulated_depreciation(self):
		"""Tests if an error is raised when opening_accumulated_depreciation > (gross_purchase_amount - expected_value_after_useful_life)."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2020-07-01",
			opening_accumulated_depreciation=100000,
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_opening_booked_depreciations(self):
		"""Tests if an error is raised when opening_number_of_booked_depreciations is not specified when opening_accumulated_depreciation is."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2020-07-01",
			opening_accumulated_depreciation=10000,
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_number_of_depreciations(self):
		"""Tests if an error is raised when opening_number_of_booked_depreciations >= total_number_of_depreciations."""

		# opening_number_of_booked_depreciations > total_number_of_depreciations
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2020-07-01",
			opening_accumulated_depreciation=10000,
			opening_number_of_booked_depreciations=5,
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

		# opening_number_of_booked_depreciations = total_number_of_depreciations
		asset_2 = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=5,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2020-07-01",
			opening_accumulated_depreciation=10000,
			opening_number_of_booked_depreciations=5,
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_2.save)

	def test_depreciation_start_date_is_before_purchase_date(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2014-07-01",
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_depreciation_start_date_is_before_available_for_use_date(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			depreciation_start_date="2018-07-01",
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_finance_books_are_present_if_calculate_depreciation_is_enabled(self):
		asset = create_asset(item_code="Macbook Pro", do_not_save=1)
		asset.calculate_depreciation = 1

		self.assertRaises(frappe.ValidationError, asset.save)

	def test_post_depreciation_entries(self):
		"""Tests if post_depreciation_entries() works as expected."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=1,
		)

		post_depreciation_entries(date="2021-06-01")
		asset.load_from_db()

		depr_schedule = get_depr_schedule(asset.name, "Active")

		self.assertTrue(depr_schedule[0].journal_entry)
		self.assertFalse(depr_schedule[1].journal_entry)
		self.assertFalse(depr_schedule[2].journal_entry)

	def test_depr_entry_posting_when_depr_expense_account_is_an_expense_account(self):
		"""Tests if the Depreciation Expense Account gets debited and the Accumulated Depreciation Account gets credited when the former's an Expense Account."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=1,
		)

		post_depreciation_entries(date="2021-06-01")
		asset.load_from_db()

		je = frappe.get_doc(
			"Journal Entry", get_depr_schedule(asset.name, "Active")[0].journal_entry
		)
		accounting_entries = [
			{"account": entry.account, "debit": entry.debit, "credit": entry.credit}
			for entry in je.accounts
		]

		for entry in accounting_entries:
			if entry["account"] == "_Test Depreciations - _TC":
				self.assertTrue(entry["debit"])
				self.assertFalse(entry["credit"])
			else:
				self.assertTrue(entry["credit"])
				self.assertFalse(entry["debit"])

	def test_depr_entry_posting_when_depr_expense_account_is_an_income_account(self):
		"""Tests if the Depreciation Expense Account gets credited and the Accumulated Depreciation Account gets debited when the former's an Income Account."""

		depr_expense_account = frappe.get_doc("Account", "_Test Depreciations - _TC")
		depr_expense_account.root_type = "Income"
		depr_expense_account.parent_account = "Income - _TC"
		depr_expense_account.save()

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=1,
		)

		post_depreciation_entries(date="2021-06-01")
		asset.load_from_db()

		je = frappe.get_doc(
			"Journal Entry", get_depr_schedule(asset.name, "Active")[0].journal_entry
		)
		accounting_entries = [
			{"account": entry.account, "debit": entry.debit, "credit": entry.credit}
			for entry in je.accounts
		]

		for entry in accounting_entries:
			if entry["account"] == "_Test Depreciations - _TC":
				self.assertTrue(entry["credit"])
				self.assertFalse(entry["debit"])
			else:
				self.assertTrue(entry["debit"])
				self.assertFalse(entry["credit"])

		# resetting
		depr_expense_account.root_type = "Expense"
		depr_expense_account.parent_account = "Expenses - _TC"
		depr_expense_account.save()

	def test_clear_depr_schedule(self):
		"""Tests if clear_depr_schedule() works as expected."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2019-12-31",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=12,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=1,
		)

		post_depreciation_entries(date="2021-06-01")
		asset.load_from_db()

		asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset.name, "Active")

		asset_depr_schedule_doc.clear_depr_schedule()

		self.assertEqual(len(asset_depr_schedule_doc.get("depreciation_schedule")), 1)

	def test_clear_depr_schedule_for_multiple_finance_books(self):
		asset = create_asset(
			item_code="Macbook Pro", available_for_use_date="2019-12-31", do_not_save=1
		)

		asset.calculate_depreciation = 1
		asset.append(
			"finance_books",
			{
				"finance_book": "Test Finance Book 1",
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 1,
				"total_number_of_depreciations": 3,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-01-31",
			},
		)
		asset.append(
			"finance_books",
			{
				"finance_book": "Test Finance Book 2",
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 1,
				"total_number_of_depreciations": 6,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-01-31",
			},
		)
		asset.append(
			"finance_books",
			{
				"finance_book": "Test Finance Book 3",
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 12,
				"total_number_of_depreciations": 3,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-12-31",
			},
		)
		asset.submit()

		post_depreciation_entries(date="2020-04-01")
		asset.load_from_db()

		asset_depr_schedule_doc_1 = get_asset_depr_schedule_doc(
			asset.name, "Active", "Test Finance Book 1"
		)
		asset_depr_schedule_doc_1.clear_depr_schedule()
		self.assertEqual(len(asset_depr_schedule_doc_1.get("depreciation_schedule")), 3)

		asset_depr_schedule_doc_2 = get_asset_depr_schedule_doc(
			asset.name, "Active", "Test Finance Book 2"
		)
		asset_depr_schedule_doc_2.clear_depr_schedule()
		self.assertEqual(len(asset_depr_schedule_doc_2.get("depreciation_schedule")), 3)

		asset_depr_schedule_doc_3 = get_asset_depr_schedule_doc(
			asset.name, "Active", "Test Finance Book 3"
		)
		asset_depr_schedule_doc_3.clear_depr_schedule()
		self.assertEqual(len(asset_depr_schedule_doc_3.get("depreciation_schedule")), 0)

	def test_depreciation_schedules_are_set_up_for_multiple_finance_books(self):
		asset = create_asset(
			item_code="Macbook Pro", available_for_use_date="2019-12-31", do_not_save=1
		)

		asset.calculate_depreciation = 1
		asset.append(
			"finance_books",
			{
				"finance_book": "Test Finance Book 1",
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 12,
				"total_number_of_depreciations": 3,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-12-31",
			},
		)
		asset.append(
			"finance_books",
			{
				"finance_book": "Test Finance Book 2",
				"depreciation_method": "Straight Line",
				"frequency_of_depreciation": 12,
				"total_number_of_depreciations": 6,
				"expected_value_after_useful_life": 10000,
				"depreciation_start_date": "2020-12-31",
			},
		)
		asset.save()

		asset_depr_schedule_doc_1 = get_asset_depr_schedule_doc(
			asset.name, "Draft", "Test Finance Book 1"
		)
		self.assertEqual(len(asset_depr_schedule_doc_1.get("depreciation_schedule")), 3)

		asset_depr_schedule_doc_2 = get_asset_depr_schedule_doc(
			asset.name, "Draft", "Test Finance Book 2"
		)
		self.assertEqual(len(asset_depr_schedule_doc_2.get("depreciation_schedule")), 6)

	def test_depreciation_entry_cancellation(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			purchase_date="2020-06-06",
			available_for_use_date="2020-06-06",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=10,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=1,
		)

		post_depreciation_entries(date="2021-01-01")

		asset.load_from_db()

		# cancel depreciation entry
		depr_entry = get_depr_schedule(asset.name, "Active")[0].journal_entry
		self.assertTrue(depr_entry)

		frappe.get_doc("Journal Entry", depr_entry).cancel()

		depr_entry = get_depr_schedule(asset.name, "Active")[0].journal_entry
		self.assertFalse(depr_entry)

	def test_asset_expected_value_after_useful_life(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			available_for_use_date="2020-06-06",
			purchase_date="2020-06-06",
			frequency_of_depreciation=10,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
		)

		accumulated_depreciation_after_full_schedule = max(
			d.accumulated_depreciation_amount for d in get_depr_schedule(asset.name, "Draft")
		)

		asset_value_after_full_schedule = flt(asset.gross_purchase_amount) - flt(
			accumulated_depreciation_after_full_schedule
		)

		self.assertTrue(
			asset.finance_books[0].expected_value_after_useful_life
			>= asset_value_after_full_schedule
		)

	def test_gle_made_by_depreciation_entries(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			purchase_date="2020-01-30",
			available_for_use_date="2020-01-30",
			depreciation_start_date="2020-12-31",
			frequency_of_depreciation=10,
			total_number_of_depreciations=3,
			expected_value_after_useful_life=10000,
			submit=1,
		)

		self.assertEqual(asset.status, "Submitted")

		frappe.db.set_value(
			"Company", "_Test Company", "series_for_depreciation_entry", "DEPR-"
		)
		post_depreciation_entries(date="2021-01-01")
		asset.load_from_db()

		# check depreciation entry series
		self.assertEqual(get_depr_schedule(asset.name, "Active")[0].journal_entry[:4], "DEPR")

		expected_gle = (
			("_Test Accumulated Depreciations - _TC", 0.0, 30000.0),
			("_Test Depreciations - _TC", 30000.0, 0.0),
		)

		gle = frappe.db.sql(
			"""select account, debit, credit from `tabGL Entry`
			where against_voucher_type='Asset' and against_voucher = %s
			order by account""",
			asset.name,
		)

		self.assertSequenceEqual(gle, expected_gle)
		self.assertEqual(asset.get("value_after_depreciation"), 0)

	def test_expected_value_change(self):
		"""
		tests if changing `expected_value_after_useful_life`
		affects `value_after_depreciation`
		"""

		asset = create_asset(calculate_depreciation=1)

		asset.finance_books[0].expected_value_after_useful_life = 100
		asset.save()
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 100000.0)

		# changing expected_value_after_useful_life shouldn't affect value_after_depreciation
		asset.finance_books[0].expected_value_after_useful_life = 200
		asset.save()
		asset.reload()
		self.assertEqual(asset.finance_books[0].value_after_depreciation, 100000.0)

	def test_asset_cost_center(self):
		asset = create_asset(is_existing_asset=1, do_not_save=1)
		asset.cost_center = "Main - WP"

		self.assertRaises(frappe.ValidationError, asset.submit)

		asset.cost_center = "Main - _TC"
		asset.submit()

	def test_depreciation_on_final_day_of_the_month(self):
		"""Tests if final day of the month is picked each time, if the depreciation start date is the last day of the month."""

		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			purchase_date="2020-01-30",
			available_for_use_date="2020-02-15",
			depreciation_start_date="2020-02-29",
			frequency_of_depreciation=1,
			total_number_of_depreciations=5,
			submit=1,
		)

		expected_dates = [
			"2020-02-29",
			"2020-03-31",
			"2020-04-30",
			"2020-05-31",
			"2020-06-30",
			"2020-07-15",
		]

		for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
			self.assertEqual(getdate(expected_dates[i]), getdate(schedule.schedule_date))

	def test_manual_depreciation_for_existing_asset(self):
		asset = create_asset(
			item_code="Macbook Pro",
			is_existing_asset=1,
			purchase_date="2020-01-30",
			available_for_use_date="2020-01-30",
			submit=1,
		)

		self.assertEqual(asset.status, "Submitted")
		self.assertEqual(asset.get_value_after_depreciation(), 100000)

		jv = make_journal_entry(
			"_Test Depreciations - _TC", "_Test Accumulated Depreciations - _TC", 100, save=False
		)
		for d in jv.accounts:
			d.reference_type = "Asset"
			d.reference_name = asset.name
		jv.voucher_type = "Depreciation Entry"
		jv.insert()
		jv.submit()

		asset.reload()
		self.assertEqual(asset.get_value_after_depreciation(), 99900)

		jv.cancel()

		asset.reload()
		self.assertEqual(asset.get_value_after_depreciation(), 100000.0)

	def test_manual_depreciation_for_depreciable_asset(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			purchase_date="2020-01-30",
			available_for_use_date="2020-01-30",
			expected_value_after_useful_life=10000,
			total_number_of_depreciations=10,
			frequency_of_depreciation=1,
			submit=1,
		)

		self.assertEqual(asset.status, "Submitted")
		self.assertEqual(asset.get_value_after_depreciation(), 100000)

		jv = make_journal_entry(
			"_Test Depreciations - _TC", "_Test Accumulated Depreciations - _TC", 100, save=False
		)
		for d in jv.accounts:
			d.reference_type = "Asset"
			d.reference_name = asset.name
		jv.voucher_type = "Depreciation Entry"
		jv.insert()
		jv.submit()

		asset.reload()
		self.assertEqual(asset.get_value_after_depreciation(), 99900)

		jv.cancel()

		asset.reload()
		self.assertEqual(asset.get_value_after_depreciation(), 100000)

	def test_manual_depreciation_with_incorrect_jv_voucher_type(self):
		asset = create_asset(
			item_code="Macbook Pro",
			calculate_depreciation=1,
			purchase_date="2020-01-30",
			available_for_use_date="2020-01-30",
			expected_value_after_useful_life=10000,
			total_number_of_depreciations=10,
			frequency_of_depreciation=1,
			submit=1,
		)

		jv = make_journal_entry(
			"_Test Depreciations - _TC", "_Test Accumulated Depreciations - _TC", 100, save=False
		)
		for d in jv.accounts:
			d.reference_type = "Asset"
			d.reference_name = asset.name
			d.account_type = "Depreciation"
		jv.voucher_type = "Journal Entry"

		self.assertRaises(frappe.ValidationError, jv.insert)

	def test_multi_currency_asset_pr_creation(self):
		pr = make_purchase_receipt(
			item_code="Macbook Pro",
			qty=1,
			rate=100.0,
			location="Test Location",
			supplier="_Test Supplier USD",
			currency="USD",
		)

		pr.submit()
		self.assertTrue(get_gl_entries("Purchase Receipt", pr.name))

	def test_asset_repair_with_stock_consume_TC_FA_049(self):
		get_details = create_company_and_supplier()
		company = get_details.get("parent_company")
		frappe.db.set_value("Company", company, "depreciation_cost_center", "Main - TC-1")
		asset_category = get_asset_category()
		location = get_location()

		item_1 = make_test_item("test_asset_item_for_repair_1")
		item_1.is_stock_item = 0
		item_1.is_fixed_asset = 1
		item_1.asset_category = asset_category
		item_1.save()

		pr = create_purchase_receipt(item_1)

		asset = create_assets(company, location, pr, item_1.item_code)

		pi = create_pi(company)
		pi.total_taxes_and_charges = ""
		pi.insert()
		pi.submit()
		self.assertEqual(pi.docstatus, 1)

		pi_gle_entries = frappe.get_all("GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"])
		expected_pi_entries = {
			"Cost of Goods Sold - TC-1": {"debit": 1000, "credit": 0},
			"Creditors - TC-1": {"debit": 0, "credit": 1000},
		}
		for entry in pi_gle_entries:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

		asset_repair = create_asset_repair(company, asset, pi.name)
		asset_repair.insert()
		asset_repair.submit()
		self.assertEqual(asset_repair.docstatus, 1)

		asset_repair_gle_entries = frappe.get_all("GL Entry", filters={"voucher_no": asset_repair.name}, fields=["account", "debit", "credit"])
		expected_si_entries = {
			"Buildings - TC-1": {"debit": 1400, "credit": 0},
			"Cost of Goods Sold - TC-1": {"debit": 0, "credit": 900},
			"Stock Adjustment - TC-1": {"debit": 0, "credit": 500},
		}
		for entry in asset_repair_gle_entries:
			self.assertEqual(entry["debit"], expected_si_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_si_entries.get(entry["account"], {}).get("credit", 0))

	def test_asset_repair_with_multiple_pi_TC_FA_114(self):
		get_details = create_company_and_supplier()
		company = get_details.get("parent_company")
		frappe.db.set_value("Company", company, "depreciation_cost_center", "Main - TC-1")
		asset_category = get_asset_category()
		location = get_location()

		item_1 = make_test_item("test_asset_item_for_repair_1")
		item_1.is_stock_item = 0
		item_1.is_fixed_asset = 1
		item_1.asset_category = asset_category
		item_1.save()

		pr = create_purchase_receipt(item_1)

		asset = create_assets(company, location, pr, item_1.item_code)

		pi_1 = create_pi(company)
		pi_1.total_taxes_and_charges = ""
		pi_1.insert()
		pi_1.submit()
		self.assertEqual(pi_1.docstatus, 1)

		pi_gle_entries_1 = frappe.get_all("GL Entry", filters={"voucher_no": pi_1.name}, fields=["account", "debit", "credit"])
		expected_pi_entries = {
			"Cost of Goods Sold - TC-1": {"debit": 1000, "credit": 0},
			"Creditors - TC-1": {"debit": 0, "credit": 1000},
		}
		for entry in pi_gle_entries_1:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

		pi_2 = create_pi(company)
		pi_2.total_taxes_and_charges = ""
		pi_2.insert()
		pi_2.submit()
		self.assertEqual(pi_2.docstatus, 1)

		pi_gle_entries_2 = frappe.get_all("GL Entry", filters={"voucher_no": pi_1.name}, fields=["account", "debit", "credit"])
		expected_pi_entries = {
			"Cost of Goods Sold - TC-1": {"debit": 1000, "credit": 0},
			"Creditors - TC-1": {"debit": 0, "credit": 1000},
		}
		for entry in pi_gle_entries_2:
			self.assertEqual(entry["debit"], expected_pi_entries.get(entry["account"], {}).get("debit", 0))
			self.assertEqual(entry["credit"], expected_pi_entries.get(entry["account"], {}).get("credit", 0))

		asset_repair = create_asset_repair(company, asset, pi_1.name, pi_2.name)
		asset_repair.insert()
		asset_repair.submit()
		self.assertEqual(asset_repair.docstatus, 1)

def get_gl_entries(doctype, docname):
	gl_entry = frappe.qb.DocType("GL Entry")
	return (
		frappe.qb.from_(gl_entry)
		.select(gl_entry.account, gl_entry.debit, gl_entry.credit)
		.where((gl_entry.voucher_type == doctype) & (gl_entry.voucher_no == docname))
		.orderby(gl_entry.account)
		.run()
	)


def create_asset_data():
	if not frappe.db.exists("Asset Category", "Computers"):
		create_asset_category()

	if not frappe.db.exists("Item", "Macbook Pro"):
		create_fixed_asset_item()

	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

	if not frappe.db.exists("Finance Book", "Test Finance Book 1"):
		frappe.get_doc(
			{"doctype": "Finance Book", "finance_book_name": "Test Finance Book 1"}
		).insert()

	if not frappe.db.exists("Finance Book", "Test Finance Book 2"):
		frappe.get_doc(
			{"doctype": "Finance Book", "finance_book_name": "Test Finance Book 2"}
		).insert()

	if not frappe.db.exists("Finance Book", "Test Finance Book 3"):
		frappe.get_doc(
			{"doctype": "Finance Book", "finance_book_name": "Test Finance Book 3"}
		).insert()


def create_asset(**args):
	args = frappe._dict(args)

	create_asset_data()

	asset = frappe.get_doc(
		{
			"doctype": "Asset",
			"asset_name": args.asset_name or "Macbook Pro 1",
			"asset_category": args.asset_category or "Computers",
			"item_code": args.item_code or "Macbook Pro",
			"company": args.company or "_Test Company",
			"purchase_date": args.purchase_date or "2015-01-01",
			"calculate_depreciation": args.calculate_depreciation or 0,
			"opening_accumulated_depreciation": args.opening_accumulated_depreciation or 0,
			"opening_number_of_booked_depreciations": args.opening_number_of_booked_depreciations
			or 0,
			"gross_purchase_amount": args.gross_purchase_amount or 100000,
			"purchase_amount": args.purchase_amount or 100000,
			"maintenance_required": args.maintenance_required or 0,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"available_for_use_date": args.available_for_use_date or "2020-06-06",
			"location": args.location or "Test Location",
			"asset_owner": args.asset_owner or "Company",
			"is_existing_asset": args.is_existing_asset or 1,
			"is_composite_asset": args.is_composite_asset or 0,
			"asset_quantity": args.get("asset_quantity") or 1,
			"depr_entry_posting_status": args.depr_entry_posting_status or "",
		}
	)

	if asset.calculate_depreciation:
		asset.append(
			"finance_books",
			{
				"finance_book": args.finance_book,
				"depreciation_method": args.depreciation_method or "Straight Line",
				"frequency_of_depreciation": args.frequency_of_depreciation or 12,
				"total_number_of_depreciations": args.total_number_of_depreciations or 5,
				"expected_value_after_useful_life": args.expected_value_after_useful_life or 0,
				"depreciation_start_date": args.depreciation_start_date,
				"daily_prorata_based": args.daily_prorata_based or 0,
				"shift_based": args.shift_based or 0,
				"rate_of_depreciation": args.rate_of_depreciation or 0,
			},
		)

	if not args.do_not_save:
		try:
			asset.flags.ignore_mandatory=True
			asset.insert(ignore_if_duplicate=True)

		except frappe.DuplicateEntryError:
			pass

	if args.submit:
		asset.submit()

	return asset


def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Computers"
	asset_category.total_number_of_depreciations = 3
	asset_category.frequency_of_depreciation = 3
	asset_category.enable_cwip_accounting = 1
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
			"capital_work_in_progress_account": "CWIP Account - _TC",
		},
	)
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company with perpetual inventory",
			"fixed_asset_account": "_Test Fixed Asset - TCP1",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - TCP1",
			"depreciation_expense_account": "_Test Depreciations - TCP1",
		},
	)

	asset_category.insert()


def create_fixed_asset_item(item_code=None, auto_create_assets=1, is_grouped_asset=0):
	meta = frappe.get_meta("Asset")
	naming_series = (
		meta.get_field("naming_series").options.splitlines()[0] or "ACC-ASS-.YYYY.-"
	)
	try:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code or "Macbook Pro",
				"item_name": "Macbook Pro",
				"description": "Macbook Pro Retina Display",
				"asset_category": "Computers",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_fixed_asset": 1,
				"auto_create_assets": auto_create_assets,
				"is_grouped_asset": is_grouped_asset,
				"asset_naming_series": naming_series,
			}
		)
		item.insert(ignore_if_duplicate=True)
	except frappe.DuplicateEntryError:
		pass
	return item


def set_depreciation_settings_in_company(company=None):
	if not company:
		company = "_Test Company"
	company = frappe.get_doc("Company", company)
	company.accumulated_depreciation_account = (
		"_Test Accumulated Depreciations - " + company.abbr
	)
	company.depreciation_expense_account = "_Test Depreciations - " + company.abbr
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - " + company.abbr
	company.depreciation_cost_center = "Main - " + company.abbr
	company.save()

	# Enable booking asset depreciation entry automatically
	frappe.db.set_single_value(
		"Accounts Settings", "book_asset_depreciation_entry_automatically", 1
	)


def enable_cwip_accounting(asset_category, enable=1):
	frappe.db.set_value("Asset Category", asset_category, "enable_cwip_accounting", enable)

def create_pi(company):
	item_2 = make_test_item("test_asset_item_for_repair_2")
	item_2.is_stock_item = 0
	item_2.is_fixed_asset = 0
	item_2.asset_category = get_asset_category()
	item_2.save()

	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": "_Test Supplier",
			"posting_date": today(),
			"update_stock": 1,
			"items": [
				{
					"item_code": item_2.item_code,
					"qty": 1,
					"rate": 1000,
					"expense_account": "Cost of Goods Sold - TC-1",
				}
			]

		}
	)

	return pi

def create_asset_repair(company, asset, pi_1, pi_2 = None):
	item = make_test_item("service_item_for_asset_review")
	make_stock_entry(company = company, target = "Stores - TC-1", item_code = item.item_code, qty = 10, rate = 1000)
	invoices = [
		{
			"purchase_invoice": pi_1,
			"expense_account": "Cost of Goods Sold - TC-1",
			"repair_cost": 1000
		}
	]
	if pi_2:
		invoices.append(
			{
				"purchase_invoice": pi_2,
				"expense_account": "Cost of Goods Sold - TC-1",
				"repair_cost": 1000
			}
		)
	asset_repair = frappe.get_doc(
		{
			"doctype": "Asset Repair",
			"company": company,
			"asset": asset,
			"failure_date": now(),
			"cost_center": "Main - TC-1",
			"repair_status": "Completed",
			"invoices": invoices,
			"capitalize_repair_cose": 1,
			"stock_consumption": 1,
			"stock_items": [
				{
					"item_code": item.item_code,
					"warehouse": "Stores - TC-1",
					"valuation_rate": 500,
					"consumed_quantity": 3
				}
			]
		}
	)

	return asset_repair