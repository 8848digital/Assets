frappe.ui.form.on("Sales Invoice", {
	setup: (frm) => {
		frm.set_query("asset", "items", function (doc, cdt, cdn) {
            var d = locals[cdt][cdn];
            return {
                filters: [
                    ["Asset", "item_code", "=", d.item_code],
                    ["Asset", "docstatus", "=", 1],
                    ["Asset", "status", "in", ["Submitted", "Partially Depreciated", "Fully Depreciated"]],
                    ["Asset", "company", "=", doc.company],
                ],
            };
        });
	},
    asset(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.asset) {
			frappe.call({
				method: assets.assets.doctype.asset.depreciation.get_disposal_account_and_cost_center,
				args: {
					company: frm.doc.company,
				},
				callback: function (r, rt) {
					frappe.model.set_value(cdt, cdn, "income_account", r.message[0]);
					frappe.model.set_value(cdt, cdn, "cost_center", r.message[1]);
				},
			});
		}
	}
});