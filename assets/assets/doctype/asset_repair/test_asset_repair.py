# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from frappe.utils import flt, nowdate, nowtime, today
from erpnext.setup.doctype.company.test_company import create_child_company
from assets.assets.doctype.asset.asset import (
	get_asset_account,
	get_asset_value_after_depreciation,
)
from assets.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	set_depreciation_settings_in_company,
)
from assets.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
)


class TestAssetRepair(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		set_depreciation_settings_in_company()
		create_asset_data()
		create_item("_Test Stock Item")
		frappe.db.sql("delete from `tabTax Rule`")
	
	# TC_FA_046
	def test_pending_asset_repair_submit_on_complete_status_TC_FA_046(self):

		company = "_Test Company"
		item_code = "Test_asset_repair_item1"
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
				"gst_hsn_code":"888890",
				"item_group":"Raw Material",
				"stock_uom":"Nos",

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

		company = "_Test Company"
		supplier = "_Test Supplier"
		qty, rate, warehouse = 1, 500, "_Test Warehouse - _TC"
		required_by_date = nowdate()

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
					"location": "Test Location",  # Linking the correct warehouse
					"asset_location": "Test Location",  # Specifying asset location
					"expense_account":"_Test Comapny - _TC"
				}
			]
		})
		pi.insert()
		pi.submit()
		frappe.db.commit()
	
		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset":target_asset,
			"company": company,
			"failure_date":"17-01-2025 14:49:20",
			"completion_date":"17-01-2025 14:52:22",
			"repair_status":"Completed",
			"invoices":[
				{
					"purchase_invoice":pi,
					"expense_account":"Service - _TC",
					"repair_cost":2000
				}
			]

		}).insert()
		asset_repair.submit()
		frappe.db.commit()

	# TC_FA_140
	def test_capitalize_repair_cost_asset_repair_submit_on_complete_status_TC_FA_140(self):
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
				"is_stock_item": 0,  # FIX: Ensuring it is a non-stock item
				"is_fixed_asset": 1,  # Marking as fixed asset
				"is_purchase_item": 1,  # Allow purchase of this asset
				"asset_naming_series": "ACC-ASS-.YYYY.-",
				"asset_category": "Test_Category",
				"item_group": "Raw Material",
				"stock_uom": "Nos",
			}

			# Check if 'gst_hsn_code' exists in Item doctype
			if frappe.db.has_column("Item", "gst_hsn_code"):
				item_data["gst_hsn_code"] = "01011010"  # Add only if field exists
			frappe.get_doc(item_data).insert()
		
		# Create Asset (Non-Stock)
		target_asset = frappe.get_doc({
			"doctype": "Asset",
			"company": company,
			"item_code": item_code,
			"asset_name": item_code,
			"asset_category": "Test_Category",
			"location": "Test Location",
			"is_existing_asset": 1,
			"available_for_use_date": "02-04-2024",
			"gross_purchase_amount": 8000,
			"total_asset": 8000,
			"asset_quantity": 2,
			"purchase_date": "01-04-2024",
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
					"depreciation_start_date": "01-06-2025",
					"total_number_of_depreciations": 12,
					"total_number_of_booked_depreciations": 7,
					"value_after_depreciation": 5000,
				}
			]
		}).insert()
		target_asset.submit()
		frappe.db.commit()

		# Create Purchase Invoice (for Non-Stock Asset)
		supplier = "_Test Supplier"
		qty, rate = 1, 500

		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": supplier,
			"update_stock": 0,  # FIX: No stock update for non-stock item
			"posting_date": nowdate(),
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"location": "Test Location",  # Linking the correct warehouse
					"asset_location": "Test Location",  # Specifying asset location
					"expense_account": "_Test Account Cost for Goods Sold - _TC",
				}
			]
		})
		pi.insert()
		pi.submit()
		frappe.db.commit()

		# Create Asset Repair
		asset_repair = frappe.get_doc({
			"doctype": "Asset Repair",
			"asset": target_asset.name,  # Using asset name instead of object
			"company": company,
			"failure_date": "17-01-2025 14:49:20",
			"completion_date": "17-01-2025 14:52:22",
			"repair_status": "Completed",
			"invoices": [
				{
					"purchase_invoice": pi.name,  # Using .name instead of object
					"expense_account": "Service - _TC",
					"repair_cost": 10000,
				}
			]
		}).insert()
		frappe.db.set_value("Asset Repair", asset_repair.name, "capitalize_repair_cost", 1)
		asset_repair.submit()
		frappe.db.commit()
		
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
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

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
			asset=asset, capitalize_repair_cost=1, item="_Test Non Stock Item", submit=1
		)
		asset.reload()

		increase_in_asset_value = (
			get_asset_value_after_depreciation(asset.name) - initial_asset_value
		)
		self.assertEqual(asset_repair.repair_cost, increase_in_asset_value)

	def test_purchase_invoice(self):
		asset_repair = create_asset_repair(
			capitalize_repair_cost=1, item="_Test Non Stock Item", submit=1
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
		default_expense_account = frappe.get_cached_value(
			"Company", asset_repair.company, "default_expense_account"
		)

		pi_expense_accounts = [pi.expense_account for pi in asset_repair.invoices]

		expected_values = {
			fixed_asset_account: [650, 0],
			pi_expense_accounts[0]: [0, 250],
			default_expense_account: [0, 100],
			pi_expense_accounts[1]: [0, 300],
		}

		for d in gl_entries:
			self.assertEqual(expected_values[d.account][0], d.debit)
			self.assertEqual(expected_values[d.account][1], d.credit)

	def test_increase_in_asset_life(self):
		asset = create_asset(calculate_depreciation=1, submit=1)

		first_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
		self.assertEqual(first_asset_depr_schedule.status, "Active")

		initial_num_of_depreciations = num_of_depreciations(asset)
		create_asset_repair(
			asset=asset, capitalize_repair_cost=1, item="_Test Non Stock Item", submit=1
		)

		asset.reload()
		first_asset_depr_schedule.load_from_db()

		second_asset_depr_schedule = get_asset_depr_schedule_doc(asset.name, "Active")
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


def num_of_depreciations(asset):
	return asset.finance_books[0].total_number_of_depreciations


def create_asset_repair(**args):
	from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
		make_purchase_invoice,
	)
	from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

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
