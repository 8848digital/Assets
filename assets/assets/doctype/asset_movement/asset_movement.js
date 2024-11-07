// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Movement", {
	refresh: function (frm) {
		if (frm.doc.purpose == "Transfer" && frm.doc.docstatus == 1) {
			if (!frm.doc.journal_entry) {
				frm.add_custom_button(
					__("Make Journal Entry"),
					function () {
						frappe.confirm("Are you sure you want to proceed?", () => {
							frappe.call({
								method: "assets.assets.doctype.asset_movement.asset_movement.make_asset_movement_entry",
								args: {
									asset_movement_name: frm.doc.name,
									transaction_date: frm.doc.transaction_date,
									company: frm.doc.company,
								},
								callback: function (r) {
									frappe.model.sync(r.message);
									frm.refresh();
								},
							});
						});
					},
					__("Create")
				);
			}
			frm.add_custom_button(
				__("Make Delivery Note"),
				function () {
					frappe.confirm(
						"Are you sure you want to proceed?",
						() => {
							frappe.call({
								method: "assets.assets.doctype.asset_movement.asset_movement.make_delivery_note",
								args: {
									name: frm.doc.name,
									transaction_date: frm.doc.transaction_date,
								},
								callback: function (r) {
									frappe.model.with_doctype("Delivery Note", function () {
										var doc = frappe.model.get_new_doc("Delivery Note");
										var items = r.message;
										var child = frappe.model.add_child(doc, "items");

										items.forEach(function (item) {
											for (var key in item) {
												if (Object.prototype.hasOwnProperty.call(item, key)) {
													child[key] = item[key];
												}
											}
										});
										frappe.set_route("Form", "Delivery Note", doc.name);
									});
								},
							});
						},
						() => {
							// action to perform if No is selected
						}
					);
				},
				__("Create")
			);
		}
	},

	setup: (frm) => {
		frm.set_query("to_employee", "assets", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});
		frm.set_query("from_employee", "assets", (doc) => {
			return {
				filters: {
					company: doc.company,
				},
			};
		});
		frm.set_query("reference_name", (doc) => {
			return {
				filters: {
					company: doc.company,
					docstatus: 1,
				},
			};
		});
		frm.set_query("reference_doctype", () => {
			return {
				filters: {
					name: ["in", ["Purchase Receipt", "Purchase Invoice"]],
				},
			};
		}),
		frm.set_query("asset", "assets", () => {
			return {
				filters: {
					status: ["not in", ["Draft"]],
				},
			};
		});

		set_cost_center_query(frm, "source_cost_center");
		set_cost_center_query(frm, "target_cost_center");
	},

	onload: (frm) => {
		frm.trigger("set_required_fields");
	},

	purpose: (frm) => {
		frm.trigger("set_required_fields");
	},

	set_required_fields: (frm, cdt, cdn) => {
		let fieldnames_to_be_altered;
		if (frm.doc.purpose === "Transfer") {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 1 },
				source_location: { read_only: 1, reqd: 1 },
				from_employee: { read_only: 1, reqd: 0 },
				to_employee: { read_only: 1, reqd: 0 },
			};
		} else if (frm.doc.purpose === "Receipt") {
			fieldnames_to_be_altered = {
				target_location: { read_only: 0, reqd: 1 },
				source_location: { read_only: 1, reqd: 0 },
				from_employee: { read_only: 0, reqd: 0 },
				to_employee: { read_only: 1, reqd: 0 },
			};
		} else if (frm.doc.purpose === "Issue") {
			fieldnames_to_be_altered = {
				target_location: { read_only: 1, reqd: 0 },
				source_location: { read_only: 1, reqd: 0 },
				from_employee: { read_only: 1, reqd: 0 },
				to_employee: { read_only: 0, reqd: 1 },
			};
		}
		if (fieldnames_to_be_altered) {
			Object.keys(fieldnames_to_be_altered).forEach((fieldname) => {
				let property_to_be_altered = fieldnames_to_be_altered[fieldname];
				Object.keys(property_to_be_altered).forEach((property) => {
					let value = property_to_be_altered[property];
					frm.fields_dict["assets"].grid.update_docfield_property(
						fieldname,
						property,
						value
					);
				});
			});
			frm.refresh_field("assets");
		}
	},
});

function set_cost_center_query(frm, fieldname) {
	frm.fields_dict["assets"].grid.get_field(fieldname).get_query = function (doc, cdt, cdn) {
		return {
			filters: {
				company: frm.doc.company,
				is_group: 0,
			},
		};
	};
}

frappe.ui.form.on("Asset Movement Item", {
	asset: function (frm, cdt, cdn) {
		frappe.db
			.get_list("Accounting Dimension", {
				fields: ["name"],
			})
			.then((fields) => {
				const field_names = fields.map(
					(field) => `source_${field.name.toLowerCase().replace(/ /g, "_")}`
				);
				const target_fields = fields.map(
					(field) => `target_${field.name.toLowerCase().replace(/ /g, "_")}`
				);

				const asset_name = locals[cdt][cdn].asset;

				if (asset_name) {
					frappe.db.get_doc("Asset", asset_name).then((asset_doc) => {
						if (asset_doc.location) {
							frappe.model.set_value(cdt, cdn, "source_location", asset_doc.location);
						}
						if (asset_doc.custodian) {
							frappe.model.set_value(cdt, cdn, "from_employee", asset_doc.custodian);
						}
						if (asset_doc.cost_center) {
							frappe.model.set_value(cdt, cdn, "source_cost_center", asset_doc.cost_center);
						}
						if (frm.doc.purpose == "Reciept") {
							target_fields.forEach((field) => {
								const original_field = field.replace("target_", "");
								if (asset_doc[original_field]) {
									frappe.model.set_value(cdt, cdn, field, asset_doc[original_field]);
								}
							});
							frappe.model.set_value(cdt, cdn, "target_cost_center", asset_doc.cost_center);
						}
						field_names.forEach((field) => {
							const original_field = field.replace("source_", "");
							if (asset_doc[original_field]) {
								frappe.model.set_value(cdt, cdn, field, asset_doc[original_field]);
							}
						});
					});
				}
			});
	},
});
