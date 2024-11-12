# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form
from frappe.utils.data import date_diff, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from assets.assets.doctype.asset.depreciation import make_depreciation_entry
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
		purpose: DF.Literal["", "Issue", "Receipt", "Transfer"]
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		transaction_date: DF.Datetime
	# end: auto-generated types

	def validate(self):
		self.validate_asset()
		self.validate_location()
		self.validate_employee()
		self.validate_dep_schedule()

	def validate_asset(self):
		for d in self.assets:
			status, company = frappe.db.get_value("Asset", d.asset, ["status", "company"])
			if self.purpose == "Transfer" and status in ("Draft", "Scrapped", "Sold"):
				frappe.throw(_("{0} asset cannot be transferred").format(status))

			if company != self.company:
				frappe.throw(
					_("Asset {0} does not belong to company {1}").format(d.asset, self.company)
				)

			if not (d.source_location or d.target_location or d.from_employee or d.to_employee):
				frappe.throw(_("Either location or employee must be required"))

	def validate_location(self):
		for d in self.assets:
			if self.purpose in ["Transfer", "Issue"]:
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

			if self.purpose == "Issue":
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

	def validate_employee(self):
		for d in self.assets:
			if d.from_employee:
				current_custodian = frappe.db.get_value("Asset", d.asset, "custodian")

				if current_custodian != d.from_employee:
					frappe.throw(
						_("Asset {0} does not belongs to the custodian {1}").format(
							d.asset, d.from_employee
						)
					)

			if (
				d.to_employee
				and frappe.db.get_value("Employee", d.to_employee, "company") != self.company
			):
				frappe.throw(
					_("Employee {0} does not belongs to the company {1}").format(
						d.to_employee, self.company
					)
				)

	def validate_dep_schedule(self):
		for asset in self.assets:
			if not frappe.db.exists("Asset Depreciation Schedule", {"asset": asset.asset}):
				return

			asset_depr_schedule_doc = frappe.get_doc(
				"Asset Depreciation Schedule", {"asset": asset.asset}
			)
			transaction_date = getdate(self.transaction_date)

			asset_depr_schedule_list = frappe.db.get_all(
				"Depreciation Schedule",
				filters={"parent": asset_depr_schedule_doc.name},
				fields=[
					"schedule_date",
					"name",
					"depreciation_amount",
					"accumulated_depreciation_amount",
					"journal_entry",
				],
				order_by="schedule_date",
			)

			next_schedule = None
			for schedule in asset_depr_schedule_list:
				if schedule["schedule_date"] >= transaction_date:
					next_schedule = schedule
					break
			if next_schedule:
				if next_schedule["journal_entry"]:
					frappe.throw(_("Depreciation Entry of Transaction Date is already made"))

	def on_submit(self):
		self.set_accounting_dimensions_and_custodian_in_asset()

	def before_cancel(self):
		self.sequence_cancel()

	def on_cancel(self):
		self.set_accounting_dimensions_and_custodian_in_asset()
		self.on_cancel_reverse_depreciation_schedule()

	def set_accounting_dimensions_and_custodian_in_asset(self):
		fieldnames = get_accounting_dimensions(as_list=True)
		target_dimension_fields = [f"target_{fieldname}" for fieldname in fieldnames]
		field_mapping = {tf: tf.split("_", 1)[1] for tf in target_dimension_fields}
		target_dimension_fields_str = (
			", " + ", ".join(target_dimension_fields) if target_dimension_fields else ""
		)

		for d in self.assets:
			args = {"asset": d.asset, "company": self.company}

			# latest entry corresponds to current document's location, employee when transaction date > previous dates
			# In case of cancellation it corresponds to previous latest document's location, employee
			latest_movement_entry = frappe.db.sql(
				f"""
				SELECT asm_item.target_location, asm_item.to_employee, asm_item.target_cost_center{target_dimension_fields_str}
				FROM `tabAsset Movement Item` asm_item, `tabAsset Movement` asm
				WHERE
					asm_item.parent=asm.name and
					asm_item.asset=%(asset)s and
					asm.company=%(company)s and
					asm.docstatus=1
				ORDER BY
					asm.transaction_date desc limit 1
				""",
				args,
				as_dict=True,
			)
			if latest_movement_entry:
				current_location = latest_movement_entry[0]["target_location"]
				current_employee = latest_movement_entry[0]["to_employee"]
				target_cost_center = latest_movement_entry[0]["target_cost_center"]
				current_values = {
					field_mapping[tf]: latest_movement_entry[0][tf] for tf in target_dimension_fields
				}
			else:
				current_location = current_employee = target_cost_center = ""
				current_values = {field: "" for field in fieldnames}

			frappe.db.set_value(
				"Asset",
				d.asset,
				{
					"location": current_location,
					"custodian": current_employee,
					"cost_center": target_cost_center,
					**current_values,
				},
				update_modified=False,
			)
			if self.purpose == "Transfer" and frappe.db.exists(
				"Asset Depreciation Schedule", {"asset": d.asset}
			):
				asset_depr_schedule_doc = frappe.get_doc(
					"Asset Depreciation Schedule", {"asset": d.asset}
				)
				update_depreciation_schedule(
					d.asset, asset_depr_schedule_doc.name, self.transaction_date
				)
				make_depreciation_entry(asset_depr_schedule_doc.name)

				frappe.db.set_value(
					"Asset Depreciation Schedule",
					asset_depr_schedule_doc.name,
					{"cost_center": target_cost_center, **current_values},
					update_modified=True,
				)

			if current_location and current_employee:
				add_asset_activity(
					d.asset,
					_("Asset received at Location {0} and issued to Employee {1}").format(
						get_link_to_form("Location", current_location),
						get_link_to_form("Employee", current_employee),
					),
				)
			elif current_location:
				add_asset_activity(
					d.asset,
					_("Asset transferred to Location {0}").format(
						get_link_to_form("Location", current_location)
					),
				)
			elif current_employee:
				add_asset_activity(
					d.asset,
					_("Asset issued to Employee {0}").format(
						get_link_to_form("Employee", current_employee)
					),
				)

	def on_cancel_reverse_depreciation_schedule(self):
		transaction_date = getdate(self.transaction_date)
		for d in self.assets:
			asset_depr_schedule_list = frappe.db.get_list(
				"Asset Depreciation Schedule", {"asset": d.asset}, pluck="name"
			)
			for asset_depr_schedule in asset_depr_schedule_list:
				if not frappe.db.exists(
					"Depreciation Schedule",
					{"parent": asset_depr_schedule, "schedule_date": transaction_date},
				):
					break

				depreciation_entry = get_depreciation_entry(asset_depr_schedule, transaction_date)
				if not depreciation_entry:
					break
				try:
					cancel_journal_entry(depreciation_entry["journal_entry"])
					reverse_depreciation_entry(
						asset_depr_schedule, depreciation_entry, transaction_date
					)
				except Exception as e:
					frappe.throw(str(e))

	def sequence_cancel(self):
		asset_name_list = frappe.db.get_all(
			"Asset Movement Item", filters={"parent": self.name}, pluck="asset"
		)
		for asset_name in asset_name_list:
			asset_movement_items = frappe.db.get_all(
				"Asset Movement Item", filters={"asset": asset_name}, fields=["parent as name"]
			)
			asset_movement_name_list = list(set(item["name"] for item in asset_movement_items))

			if asset_movement_name_list:
				asset_movement_values = frappe.db.get_all(
					"Asset Movement",
					filters={"name": ["in", asset_movement_name_list], "docstatus": 1},
					fields=["name", "creation"],
				)

				if asset_movement_values:
					asset_movement_values.sort(key=lambda x: x["creation"], reverse=True)
					most_recent_record = asset_movement_values[0]

					if self.name != most_recent_record["name"]:
						frappe.throw("You can only cancel the most recent record.")


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
