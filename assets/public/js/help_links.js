frappe.provide("frappe.help.help_links");

const docsUrl = "https://erpnext.com/docs/";

frappe.help.help_links["List/Asset"] = [
	{
		label: "Managing Fixed Assets",
		url: docsUrl + "user/manual/en/asset",
	},
];

frappe.help.help_links["List/Asset Category"] = [
	{
		label: "Asset Category",
		url: docsUrl + "user/manual/en/asset-category",
	},
];

frappe.help.help_links["List/Item"].push({
	label: "Managing Fixed Assets",
	url: docsUrl + "user/manual/en/asset",
	})

frappe.help.help_links["Form/Item"].push({
	label: "Managing Fixed Assets",
	url: docsUrl + "user/manual/en/asset",
	})