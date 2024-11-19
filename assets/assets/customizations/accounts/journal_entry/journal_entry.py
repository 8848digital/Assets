from assets.assets.customizations.accounts.journal_entry.doc_events import (
	update_asset_value,
	unlink_asset_adjustment_entry,
	unlink_asset_reference,
	update_booked_depreciation,
	unlink_asset_movement_entry,
	validate_depr_entry_voucher_type
)

def validate(doc, method=None):
	validate_depr_entry_voucher_type(doc)

def on_submit(doc, method=None):
	unlink_asset_movement_entry(doc)
	update_asset_value(doc)
	update_booked_depreciation(doc)

def on_cancel(doc, method=None):
	unlink_asset_reference(doc)
	unlink_asset_adjustment_entry(doc)
	update_booked_depreciation(doc, 1)