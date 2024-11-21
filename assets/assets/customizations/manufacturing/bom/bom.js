frappe.ui.form.on("BOM", {
	setup(frm) {
		frm.set_query("item_code", "items", function (doc) {
			return {
				query: "erpnext.manufacturing.doctype.bom.bom.item_query",
				filters: {
					include_item_in_manufacturing: 1,
					is_fixed_asset: 0,
				},
			};
		});
	},
});