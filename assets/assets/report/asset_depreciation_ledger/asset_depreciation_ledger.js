// Copyright (c) 2024, 8848 Digital LLP and contributors
// For license information, please see license.txt

frappe.query_reports["Asset Depreciation Ledger"] = {
	"filters": [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "asset",
			label: __("Asset"),
			fieldtype: "Link",
			options: "Asset",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					doctype: "Asset",
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "asset_category",
			label: __("Asset Category"),
			fieldtype: "Link",
			options: "Asset Category",
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				return {
					query: "assets.assets.report.asset_depreciation_ledger.asset_depreciation_ledger.asset_category_filter",
					filters: { company: company },
				};
			},
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
			get_query: function () {
				var company = frappe.query_report.get_filter_value("company");
				return {
					doctype: "Cost Center",
					filters: {
						company: company,
					},
				};
			},
		},
		{
			fieldname: "finance_book",
			label: __("Finance Book"),
			fieldtype: "Link",
			options: "Finance Book",
		},
		{
			fieldname: "include_default_book_assets",
			label: __("Include Default FB Assets"),
			fieldtype: "Check",
			default: 1,
		},
	],
};
