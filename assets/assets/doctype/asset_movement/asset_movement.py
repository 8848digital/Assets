# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_datetime, get_link_to_form
from assets.assets.doctype.asset_activity.asset_activity import add_asset_activity


class AssetMovement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from assets.assets.doctype.asset_movement_item.asset_movement_item import (
			AssetMovementItem,
		)

		amended_from: DF.Link | None
		assets: DF.Table[AssetMovementItem]
		company: DF.Link
		journal_entry: DF.Link | None
		purpose: DF.Literal["", "Issue", "Receipt", "Transfer","Transfer and Issue"]
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		transaction_date: DF.Datetime
	# end: auto-generated types

	def validate(self):
		for d in self.assets:
			self.validate_asset(d)
			self.validate_movement(d)
			self.validate_transaction_date(d)

	def validate_asset(self, d):
		status, company = frappe.db.get_value("Asset", d.asset, ["status", "company"])
		if self.purpose == "Transfer" and status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("{0} asset cannot be transferred").format(status))

		if company != self.company:
			frappe.throw(
				_("Asset {0} does not belong to company {1}").format(d.asset, self.company)
			)

		if not (d.source_location or d.target_location or d.from_employee or d.to_employee):
			frappe.throw(_("Either location or employee must be required"))
	def validate_transaction_date(self, d):
		previous_movement_date = frappe.db.get_value(
			"Asset Movement",
			[["Asset Movement Item", "asset", "=", d.asset], ["docstatus", "=", 1]],
			"transaction_date",
			order_by="transaction_date desc",
		)
		if previous_movement_date and get_datetime(previous_movement_date) > get_datetime(
			self.transaction_date
		):
			frappe.throw(_("Transaction date can't be earlier than previous movement date"))

	def validate_movement(self, d):
		if self.purpose == "Transfer and Issue":
			self.validate_location_and_employee(d)
		elif self.purpose in ["Receipt", "Transfer"]:
			self.validate_location(d)
		else:
			self.validate_employee(d)
	
	def validate_location_and_employee(self, d):
		self.validate_location(d)
		self.validate_employee(d)

	def validate_location(self, d):
		if self.purpose in ["Transfer", "Transfer and Issue"]:
			current_location = frappe.db.get_value("Asset", d.asset, "location")
			if d.source_location:
				if current_location != d.source_location:
					frappe.throw(
						_("Asset {0} does not belongs to the location {1}").format(
							d.asset, d.source_location
						)
					)
			else:
				d.source_location = current_location

		if self.purpose == "Transfer and Issue":
			if d.target_location:
				frappe.throw(
					_(
						"Issuing cannot be done to a location. Please enter employee to issue the Asset {0} to"
					).format(d.asset),
					title=_("Incorrect Movement Purpose"),
				)
			if not d.to_employee:
				frappe.throw(_("Employee is required while issuing Asset {0}").format(d.asset))

		if self.purpose == "Transfer":
			if d.to_employee:
				frappe.throw(
					_(
						"Transferring cannot be done to an Employee. Please enter location where Asset {0} has to be transferred"
					).format(d.asset),
					title=_("Incorrect Movement Purpose"),
				)
			if not d.target_location:
				frappe.throw(
					_("Target Location is required while transferring Asset {0}").format(d.asset)
				)
			if d.source_location == d.target_location:
				frappe.throw(_("Source and Target Location cannot be same"))

		if self.purpose == "Receipt":
			if not (d.source_location) and not (d.target_location or d.to_employee):
				frappe.throw(
					_("Target Location or To Employee is required while receiving Asset {0}").format(
						d.asset
					)
				)
			elif d.source_location:
				if d.from_employee and not d.target_location:
					frappe.throw(
						_(
							"Target Location is required while receiving Asset {0} from an employee"
						).format(d.asset)
					)
				elif d.to_employee and d.target_location:
					frappe.throw(
						_(
							"Asset {0} cannot be received at a location and given to an employee in a single movement"
						).format(d.asset)
					)

	def validate_employee(self, d):
		if self.purpose == "Transfer and Issue":
			if not d.from_employee:
				frappe.throw(_("From Employee is required while issuing Asset {0}").format(d.asset))

		if d.from_employee:
			current_custodian = frappe.db.get_value("Asset", d.asset, "custodian")

			if current_custodian != d.from_employee:
				frappe.throw(
					_("Asset {0} does not belong  to the custodian {1}").format(d.asset, d.from_employee)
				)

		if not d.to_employee:
			frappe.throw(_("Employee is required while issuing Asset {0}").format(d.asset))

		if d.to_employee and frappe.db.get_value("Employee", d.to_employee, "company") != self.company:
			frappe.throw(
				_("Employee {0} does not belong  to the company {1}").format(d.to_employee, self.company)
			)

	def on_submit(self):
		self.set_latest_location_and_custodian_in_asset()

	def on_cancel(self):
		self.set_latest_location_and_custodian_in_asset()

	def set_latest_location_and_custodian_in_asset(self):
		for d in self.assets:
			current_location, current_employee = self.get_latest_location_and_custodian(d.asset)
			self.update_asset_location_and_custodian(d.asset, current_location, current_employee)
			self.log_asset_activity(d.asset, current_location, current_employee)

	def get_latest_location_and_custodian(self, asset):
		current_location, current_employee = "", ""
		cond = "1=1"

		# latest entry corresponds to current document's location, employee when transaction date > previous dates
		# In case of cancellation it corresponds to previous latest document's location, employee
		args = {"asset": asset, "company": self.company}
		latest_movement_entry = frappe.db.sql(
			f"""
			SELECT asm_item.target_location, asm_item.to_employee
			FROM `tabAsset Movement Item` asm_item
			JOIN `tabAsset Movement` asm ON asm_item.parent = asm.name
			WHERE
				asm_item.asset = %(asset)s AND
				asm.company = %(company)s AND
				asm.docstatus = 1 AND {cond}
			ORDER BY asm.transaction_date DESC
			LIMIT 1
			""",
			args,
		)

		if latest_movement_entry:
			current_location = latest_movement_entry[0][0]
			current_employee = latest_movement_entry[0][1]

		return current_location, current_employee

	def update_asset_location_and_custodian(self, asset_id, location, employee):
		asset = frappe.get_doc("Asset", asset_id)

		if cstr(employee) != asset.custodian:
			frappe.db.set_value("Asset", asset_id, "custodian", cstr(employee))
		if location and location != asset.location:
			frappe.db.set_value("Asset", asset_id, "location", location)

	def log_asset_activity(self, asset_id, location, employee):
		if location and employee:
			add_asset_activity(
				asset_id,
				_("Asset received at Location {0} and issued to Employee {1}").format(
					get_link_to_form("Location", location),
					get_link_to_form("Employee", employee),
				),
			)
		elif location:
			add_asset_activity(
				asset_id,
				_("Asset transferred to Location {0}").format(get_link_to_form("Location", location)),
			)
		elif employee:
			add_asset_activity(
				asset_id,
				_("Asset issued to Employee {0}").format(get_link_to_form("Employee", employee)),
			)
				
def update_depreciation_schedule(
	asset_name, asset_depriciation_schedule_name, transaction_date
):
	transaction_date = getdate(transaction_date)
	asset_available_for_use_date, gross_purchase_amount = frappe.db.get_value(
		"Asset", asset_name, ["available_for_use_date", "gross_purchase_amount"]
	)
	previous_schedule, next_schedule = find_previous_and_next_schedules(
		asset_depriciation_schedule_name, transaction_date
	)

	if not (previous_schedule or next_schedule):
		return

	set_depreciation_schedule(
		previous_schedule,
		next_schedule,
		asset_available_for_use_date,
		gross_purchase_amount,
		transaction_date,
		asset_depriciation_schedule_name,
	)


def find_previous_and_next_schedules(
	asset_depriciation_schedule_name, transaction_date
):
	asset_depr_schedule_list = get_asset_depr_schedule(asset_depriciation_schedule_name)
	previous_schedule = None
	next_schedule = None
	for schedule in asset_depr_schedule_list:
		schedule_date = schedule["schedule_date"]
		if schedule_date == transaction_date:
			return None, None
		elif schedule_date < transaction_date:
			previous_schedule = schedule
		else:
			next_schedule = schedule
			break
	return previous_schedule, next_schedule


def get_asset_depr_schedule(asset_depriciation_schedule_name):
	return frappe.db.get_all(
		"Depreciation Schedule",
		filters={"parent": asset_depriciation_schedule_name},
		fields=[
			"schedule_date",
			"name",
			"depreciation_amount",
			"accumulated_depreciation_amount",
			"journal_entry",
			"wdv",
		],
		order_by="schedule_date",
	)


def set_depreciation_schedule(
	previous_schedule,
	next_schedule,
	asset_available_for_use_date,
	gross_purchase_amount,
	transaction_date,
	asset_depriciation_schedule_name,
):
	(
		dep_amount_for_today,
		dep_amount_for_next_schedule,
		wdv_for_today,
		wdv_for_next_schedule,
		accumulated_depreciation_amount,
	) = calculate_depreciation_amounts(
		previous_schedule,
		next_schedule,
		asset_available_for_use_date,
		gross_purchase_amount,
		transaction_date,
	)

	if not dep_amount_for_today:
		return

	asset_depreciation_schedule = frappe.get_doc(
		"Asset Depreciation Schedule", asset_depriciation_schedule_name
	)
	asset_depreciation_schedule.append(
		"depreciation_schedule",
		{
			"schedule_date": transaction_date,
			"depreciation_amount": dep_amount_for_today,
			"wdv": wdv_for_today,
			"accumulated_depreciation_amount": accumulated_depreciation_amount,
		},
	)
	asset_depreciation_schedule.save()

	if next_schedule:
		frappe.db.set_value(
			"Depreciation Schedule",
			next_schedule["name"],
			{"depreciation_amount": dep_amount_for_next_schedule, "wdv": wdv_for_next_schedule},
		)

	update_asset_depr_schedule_index(asset_depriciation_schedule_name)


def calculate_depreciation_amounts(
	previous_schedule,
	next_schedule,
	asset_available_for_use_date,
	gross_purchase_amount,
	transaction_date,
):
	if not next_schedule:
		return None, None, None, None, None

	if previous_schedule:
		date_diff_between_schedule = date_diff(
			next_schedule["schedule_date"], previous_schedule["schedule_date"]
		)
		date_difference = date_diff(transaction_date, previous_schedule["schedule_date"])
	else:
		date_diff_between_schedule = date_diff(
			next_schedule["schedule_date"], asset_available_for_use_date
		)
		date_difference = date_diff(transaction_date, asset_available_for_use_date)

	dep_amount_for_today = (
		next_schedule["depreciation_amount"] / date_diff_between_schedule
	) * date_difference
	dep_amount_for_next_schedule = (
		next_schedule["depreciation_amount"] - dep_amount_for_today
	)
	accumulated_depreciation_amount = (
		previous_schedule["accumulated_depreciation_amount"] + dep_amount_for_today
		if previous_schedule
		else dep_amount_for_today
	)
	wdv_for_today = (
		previous_schedule["wdv"] - dep_amount_for_today
		if previous_schedule
		else gross_purchase_amount - dep_amount_for_today
	)

	wdv_for_next_schedule = wdv_for_today - dep_amount_for_next_schedule

	return (
		dep_amount_for_today,
		dep_amount_for_next_schedule,
		wdv_for_today,
		wdv_for_next_schedule,
		accumulated_depreciation_amount,
	)


def update_next_schedule(schedule_name, dep_amount_for_next_schedule):
	frappe.db.set_value(
		"Depreciation Schedule",
		schedule_name,
		"depreciation_amount",
		dep_amount_for_next_schedule,
	)


def update_asset_depr_schedule_index(asset_depriciation_schedule_name):
	updated_asset_depr_schedule = get_asset_depr_schedule(asset_depriciation_schedule_name)
	for idx, schedule in enumerate(updated_asset_depr_schedule):
		frappe.db.set_value("Depreciation Schedule", schedule["name"], "idx", idx + 1)


def set_value_in_journal_entry(
	asset_values,
	fixed_asset_account,
	asset_movement_child_data,
	new_dimension_value,
	old_dimension_value,
	accumulated_depreciation_amount,
):
	reference = {
		"reference_type": "Asset",
		"reference_name": asset_movement_child_data.asset,
	}
	if accumulated_depreciation_amount:
		row1 = {
			"account": fixed_asset_account,
			"debit_in_account_currency": asset_values.gross_purchase_amount
			- accumulated_depreciation_amount,
			"cost_center": asset_movement_child_data.target_cost_center,
		}
		row1.update(reference)
		row1.update(new_dimension_value)
		row2 = {
			"account": fixed_asset_account,
			"credit_in_account_currency": asset_values.gross_purchase_amount
			- accumulated_depreciation_amount,
			"cost_center": asset_movement_child_data.source_cost_center,
		}
		row2.update(reference)
		row2.update(old_dimension_value)
	else:
		row1 = {
			"account": fixed_asset_account,
			"debit_in_account_currency": asset_values.total_asset_cost,
			"cost_center": asset_movement_child_data.target_cost_center,
		}
		row1.update(reference)
		row1.update(new_dimension_value)
		row2 = {
			"account": fixed_asset_account,
			"credit_in_account_currency": asset_values.total_asset_cost,
			"cost_center": asset_movement_child_data.source_cost_center,
		}
		row2.update(reference)
		row2.update(old_dimension_value)
	rows = [row1, row2]

	return rows


def get_depreciation_entry(schedule_name, transaction_date):
	return frappe.db.get_value(
		"Depreciation Schedule",
		{"parent": schedule_name, "schedule_date": transaction_date},
		[
			"name",
			"parent",
			"schedule_date",
			"depreciation_amount",
			"accumulated_depreciation_amount",
			"journal_entry",
		],
		as_dict=True,
	)


def cancel_journal_entry(journal_entry_name):
	if journal_entry_name:
		journal_entry_doc = frappe.get_doc("Journal Entry", journal_entry_name)
		if journal_entry_doc.docstatus == 1:
			journal_entry_doc.cancel()


def reverse_depreciation_entry(
	asset_depr_schedule_name, depreciation_entry, transaction_date
):
	asset_depr_schedule = get_asset_depr_schedule(asset_depr_schedule_name)
	previous_schedule, next_schedule = previous_and_next_schedules(
		asset_depr_schedule, transaction_date
	)
	frappe.get_doc("Depreciation Schedule", depreciation_entry["name"]).cancel()
	frappe.db.delete("Depreciation Schedule", depreciation_entry["name"])

	set_depr_schedule_value(previous_schedule, next_schedule, depreciation_entry)
	update_asset_depr_schedule_index(asset_depr_schedule_name)


def previous_and_next_schedules(schedule_list, transaction_date):
	previous_schedule = None
	next_schedule = None
	for schedule in schedule_list:
		if schedule["schedule_date"] < transaction_date:
			previous_schedule = schedule
		elif schedule["schedule_date"] > transaction_date:
			next_schedule = schedule
			break
	return previous_schedule, next_schedule


def set_depr_schedule_value(previous_schedule, next_schedule, depreciation_entry):
	if next_schedule:
		new_dep_amount = (
			next_schedule["depreciation_amount"] + depreciation_entry["depreciation_amount"]
		)
		frappe.db.set_value(
			"Depreciation Schedule", next_schedule["name"], "depreciation_amount", new_dep_amount
		)

		if previous_schedule:
			accumulated_depreciation_amount = (
				previous_schedule["accumulated_depreciation_amount"] + new_dep_amount
			)
			frappe.db.set_value(
				"Depreciation Schedule",
				next_schedule["name"],
				"accumulated_depreciation_amount",
				accumulated_depreciation_amount,
			)


@frappe.whitelist()
def make_asset_movement_entry(asset_movement_name, transaction_date, company):
	frappe.has_permission("Journal Entry", throw=True)

	transaction_date = frappe.utils.getdate(transaction_date)
	asset_movement_doc = frappe.get_doc("Asset Movement", asset_movement_name)

	fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")
	child_rows = []
	for asset in asset_movement_doc.assets:
		asset_values = frappe.db.get_value("Asset", {"name": asset.asset}, "*")

		fixed_asset_account = frappe.db.get_value(
			"Asset Category Account",
			{"parent": asset_values.asset_category, "company_name": asset_values.company},
			"fixed_asset_account",
		)
		asset_depr_schedule = frappe.db.get_all(
			"Asset Depreciation Schedule", {"asset": asset.asset, "docstatus": 1}, pluck="name"
		)
		asset_movement_child_data = frappe.db.get_value(
			"Asset Movement Item",
			{"parent": asset_movement_name, "asset": asset.asset},
			"*",
			as_dict=True,
		)

		old_dimension_value = {
			fieldname: asset_movement_child_data.get("from_" + fieldname)
			for fieldname in fieldnames
		}
		new_dimension_value = {
			fieldname: asset_movement_child_data.get("target_" + fieldname)
			for fieldname in fieldnames
		}

		if asset_values.calculate_depreciation and asset_depr_schedule:
			for schedule in asset_depr_schedule:
				accumulated_depreciation_amount = frappe.db.get_value(
					"Depreciation Schedule",
					{"parent": schedule, "schedule_date": transaction_date},
					"accumulated_depreciation_amount",
				)

				dep_row = set_value_in_journal_entry(
					asset_values,
					fixed_asset_account,
					asset_movement_child_data,
					new_dimension_value,
					old_dimension_value,
					accumulated_depreciation_amount,
				)
				child_rows += dep_row
		else:
			no_dep_row = set_value_in_journal_entry(
				asset_values,
				fixed_asset_account,
				asset_movement_child_data,
				new_dimension_value,
				old_dimension_value,
				None,
			)
			child_rows += no_dep_row

	doc = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"posting_date": transaction_date,
			"company": company,
			"accounts": child_rows,
			"remark": f"Asset Movement Entry against {asset_movement_name}",
		}
	)
	doc.save()
	doc.submit()
	asset_movement_doc.db_set("journal_entry", doc.name)

	return asset_movement_doc


@frappe.whitelist()
def make_delivery_note(**kwargs):
	transaction_date = getdate(kwargs.get("transaction_date"))
	asset_movement_item_list = frappe.db.get_all(
		"Asset Movement Item", {"parent": kwargs.get("name")}, ["*"]
	)

	fieldnames = frappe.get_list("Accounting Dimension", pluck="fieldname")

	asset_names = [item.asset for item in asset_movement_item_list]
	assets_info = frappe.db.get_all(
		"Asset",
		filters={"name": ["in", asset_names]},
		fields=["name", "item_code", "asset_quantity"],
	)

	item_codes = [asset["item_code"] for asset in assets_info]
	item_details = frappe.db.get_all(
		"Item",
		filters={"item_code": ["in", item_codes]},
		fields=["item_code", "item_name", "stock_uom"],
	)

	assets_info_dict = {asset["name"]: asset for asset in assets_info}
	item_details_dict = {item["item_code"]: item for item in item_details}

	delivery_note_item_rows = []

	for item in asset_movement_item_list:
		asset_info = assets_info_dict.get(item.asset)
		item_info = item_details_dict.get(asset_info["item_code"])

		asset_schedule = frappe.db.get_all(
			"Asset Depreciation Schedule", {"asset": item.asset}, pluck="name"
		)

		depreciation_data = frappe.db.get_all(
			"Depreciation Schedule",
			filters={"parent": ["in", asset_schedule], "schedule_date": transaction_date},
			fields=["parent", "accumulated_depreciation_amount"],
		)

		depreciation_dict = {
			dep["parent"]: dep["accumulated_depreciation_amount"] for dep in depreciation_data
		}

		for schedule in asset_schedule:
			accumulated_depreciation = depreciation_dict.get(schedule)

			old_dimension_value = {
				"item_code": asset_info["item_code"],
				"rate": accumulated_depreciation or 0,
				"item_name": item_info["item_name"],
				"uom": item_info["stock_uom"],
				"qty": asset_info["asset_quantity"],
			}

			for fieldname in fieldnames:
				old_dimension_value[fieldname] = item.get("source_" + fieldname)
			delivery_note_item_rows.append(old_dimension_value)

	return delivery_note_item_rows
