frappe.ui.form.on("Purchase Receipt", {
	setup: (frm) => {
        frm.set_query("wip_composite_asset", "items", function () {
            return {
                filters: { is_composite_asset: 1, docstatus: 0 },
            };
        });
    },
	refresh: (frm) => {
        if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("Asset"),
				function () {
					frappe.route_options = {
						purchase_receipt: frm.doc.name,
					};
					frappe.set_route("List", "Asset");
				},
				__("View")
			);

			frm.add_custom_button(
				__("Asset Movement"),
				function () {
					frappe.route_options = {
						reference_name: frm.doc.name,
					};
					frappe.set_route("List", "Asset Movement");
				},
				__("View")
			);
		}
    }
});