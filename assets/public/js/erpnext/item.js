// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Item", {
	onload: function (frm) {
		if (frm.doc.is_fixed_asset) {
			frm.trigger("set_asset_naming_series");
		}
	},

	refresh: function (frm) {

		if (frm.doc.is_fixed_asset) {
			frm.trigger("is_fixed_asset");
			frm.trigger("auto_create_assets");
		}

		if (!frm.doc.is_fixed_asset) {
			erpnext.item.make_dashboard(frm);
		}
	},

	is_fixed_asset: function (frm) {
		// set serial no to false & toggles its visibility
		frm.set_value("has_serial_no", 0);
		frm.set_value("has_batch_no", 0);
		frm.toggle_enable(["has_serial_no", "serial_no_series"], !frm.doc.is_fixed_asset);

		frappe.call({
			method: "assets.overrides.item.item.get_asset_naming_series",
			callback: function (r) {
				frm.set_value("is_stock_item", frm.doc.is_fixed_asset ? 0 : 1);
				frm.events.set_asset_naming_series(frm, r.message);
			},
		});

		frm.trigger("auto_create_assets");
	},

	set_asset_naming_series: function (frm, asset_naming_series) {
		if ((frm.doc.__onload && frm.doc.__onload.asset_naming_series) || asset_naming_series) {
			let naming_series =
				(frm.doc.__onload && frm.doc.__onload.asset_naming_series) || asset_naming_series;
			frm.set_df_property("asset_naming_series", "options", naming_series);
		}
	},

	auto_create_assets: function (frm) {
		frm.toggle_reqd(["asset_naming_series"], frm.doc.auto_create_assets);
		frm.toggle_display(["asset_naming_series"], frm.doc.auto_create_assets);
	},


});