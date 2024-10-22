import frappe
from frappe import _

from assets.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
)


def on_submit(doc, method=None):
	update_asset_value(doc)
	update_booked_depreciation(doc)


def on_cancel(doc, method=None):
	unlink_asset_reference(doc)
	unlink_asset_adjustment_entry(doc)
	update_booked_depreciation(doc, 1)


def unlink_asset_reference(doc):
	for d in doc.get("accounts"):
		if (
			doc.voucher_type == "Depreciation Entry"
			and d.reference_type == "Asset"
			and d.reference_name
			and frappe.get_cached_value("Account", d.account, "root_type") == "Expense"
			and d.debit
		):
			asset = frappe.get_doc("Asset", d.reference_name)

			if asset.calculate_depreciation:
				je_found = False

				for fb_row in asset.get("finance_books"):
					if je_found:
						break

					depr_schedule = get_depr_schedule(asset.name, "Active", fb_row.finance_book)

					for s in depr_schedule or []:
						if s.journal_entry == doc.name:
							s.db_set("journal_entry", None)

							fb_row.value_after_depreciation += d.debit
							fb_row.db_update()

							je_found = True
							break
				if not je_found:
					fb_idx = 1
					if doc.finance_book:
						for fb_row in asset.get("finance_books"):
							if fb_row.finance_book == doc.finance_book:
								fb_idx = fb_row.idx
								break

					fb_row = asset.get("finance_books")[fb_idx - 1]
					fb_row.value_after_depreciation += d.debit
					fb_row.db_update()
			else:
				asset.db_set("value_after_depreciation", asset.value_after_depreciation + d.debit)
			asset.set_status()
		elif (
			doc.voucher_type == "Journal Entry"
			and d.reference_type == "Asset"
			and d.reference_name
		):
			journal_entry_for_scrap = frappe.db.get_value(
				"Asset", d.reference_name, "journal_entry_for_scrap"
			)

			if journal_entry_for_scrap == doc.name:
				frappe.throw(
					_(
						"Journal Entry for Asset scrapping cannot be cancelled. Please restore the Asset."
					)
				)


def update_asset_value(doc):
	if doc.flags.planned_depr_entry or doc.voucher_type != "Depreciation Entry":
		return

	for d in doc.get("accounts"):
		if (
			d.reference_type == "Asset"
			and d.reference_name
			and d.account_type == "Depreciation"
			and d.debit
		):
			asset = frappe.get_doc("Asset", d.reference_name)

			if asset.calculate_depreciation:
				fb_idx = 1
				if doc.finance_book:
					for fb_row in asset.get("finance_books"):
						if fb_row.finance_book == doc.finance_book:
							fb_idx = fb_row.idx
							break
				fb_row = asset.get("finance_books")[fb_idx - 1]
				fb_row.value_after_depreciation -= d.debit
				fb_row.db_update()
			else:
				asset.db_set("value_after_depreciation", asset.value_after_depreciation - d.debit)

			asset.set_status()


def update_booked_depreciation(doc, cancel=0):
	for d in doc.get("accounts"):
		if (
			doc.voucher_type == "Depreciation Entry"
			and d.reference_type == "Asset"
			and d.reference_name
			and frappe.get_cached_value("Account", d.account, "root_type") == "Expense"
			and d.debit
		):
			asset = frappe.get_doc("Asset", d.reference_name)
			for fb_row in asset.get("finance_books"):
				if fb_row.finance_book == doc.finance_book:
					if cancel:
						fb_row.total_number_of_booked_depreciations -= 1
					else:
						fb_row.total_number_of_booked_depreciations += 1
					fb_row.db_update()
					break


def unlink_asset_adjustment_entry(doc):
	frappe.db.sql(
		""" update `tabAsset Value Adjustment`
        set journal_entry = null where journal_entry = %s""",
		doc.name,
	)
