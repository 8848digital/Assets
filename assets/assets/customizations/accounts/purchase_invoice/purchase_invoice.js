frappe.ui.form.on("Purchase Invoice", {
	setup: (frm) => {
		frm.set_query("wip_composite_asset", "items", function () {
			return {
				filters: { is_composite_asset: 1, docstatus: 0 },
			};
		});
	},
});