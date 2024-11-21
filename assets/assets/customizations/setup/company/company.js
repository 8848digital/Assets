erpnext.company.setup_queries = function (frm) {
	$.each(
		[
			[
				"accumulated_depreciation_account",
				{ root_type: "Asset", account_type: "Accumulated Depreciation" },
			],
			["depreciation_expense_account", { root_type: "Expense", account_type: "Depreciation" }],
			["disposal_account", { report_type: "Profit and Loss" }],
			["depreciation_cost_center", {}],
			[
				"expenses_included_in_asset_valuation",
				{ account_type: "Expenses Included In Asset Valuation" },
			],
			["capital_work_in_progress_account", { account_type: "Capital Work in Progress" }],
			["asset_received_but_not_billed", { account_type: "Asset Received But Not Billed" }],
		],
		function (i, v) {
			erpnext.company.set_custom_query(frm, v);
		}
	);
};