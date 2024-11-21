// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Journal Entry", {
	setup: function (frm) {
		frm.ignore_doctypes_on_cancel_all.push(
			"Asset",
			"Asset Movement",
			"Asset Depreciation Schedule"
		);
	},
});