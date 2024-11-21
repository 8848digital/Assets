frappe.ui.form.on("Serial and Batch Bundle", {
	setup(frm) {
		frm.trigger("set_queries");
	},

	set_queries(frm) {
		frm.set_query("voucher_type", () => {
			return {
				filters: {
					istable: 0,
					issingle: 0,
					is_submittable: 1,
					name: [
						"in",
						[
							"Asset Capitalization",
							"Asset Repair",
							"Delivery Note",
							"Installation Note",
							"Job Card",
							"Maintenance Schedule",
							"POS Invoice",
							"Pick List",
							"Purchase Invoice",
							"Purchase Receipt",
							"Quotation",
							"Sales Invoice",
							"Stock Entry",
							"Stock Reconciliation",
							"Subcontracting Receipt",
						],
					],
				},
			};
		});
	},
});