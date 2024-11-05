// Copyright (c) 2024, manoj and contributors
// For license information, please see license.txt

frappe.ui.form.on("Asset Component Capitalization", {
    refresh: (frm) => {
        if (frm.doc.docstatus > 0) {
            cur_frm.add_custom_button(
                __("Accounting Ledger"),
                function () {
                    frappe.route_options = {
                        voucher_no: frm.doc.name,
                        from_date: frm.doc.posting_date,
                        to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
                        company: frm.doc.company,
                        group_by: "Group by Voucher (Consolidated)",
                        show_cancelled_entries: frm.doc.docstatus === 2,
                    };
                    frappe.set_route("query-report", "General Ledger");
                },
                __("View")
            );
        }

        frm.set_query("parent_asset", () => {
			return {
				query: "assets.assets.doctype.asset_component_capitalization.asset_component_capitalization.parent_asset_filters",
			};
		});
    },

	parent_asset(frm) {
        if (frm.doc.parent_asset) {
            frappe.call({
                method: "assets.assets.doctype.asset_component_capitalization.asset_component_capitalization.fetch_asset",
                args: {
                    "parent_asset": frm.doc.parent_asset,
                },
                callback: function (r) {
                    frm.clear_table("component_asset");

                    r.message.forEach(asset => {
                        let new_row = frm.add_child("component_asset");
                        new_row.asset = asset.name;
                        new_row.asset_name = asset.asset_name;
                        new_row.gross_amount = asset.gross_purchase_amount;
                    });

                    frm.refresh_field("component_asset");
                },
            });
        } else {
            frm.clear_table("component_asset");
            frm.refresh_field("component_asset");
        }
    }
});
