// Copyright (c) 2024, 8848 Digital LLP and contributors
// For license information, please see license.txt

frappe.ui.form.on("Parent Asset", {
	setup(frm) {
		frm.set_query("item_code", function () {
			return {
				filters: {
					is_fixed_asset: 1,
				},
			};
		});
	},
});
