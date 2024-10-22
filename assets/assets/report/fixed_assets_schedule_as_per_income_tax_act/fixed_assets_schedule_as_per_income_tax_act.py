# Copyright (c) 2024, 8848 digital and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, formatdate
from frappe.query_builder import DocType
from frappe import db


def execute(filters=None):
	filters.day_before_from_date = add_days(filters.from_date, -1)
	filters.half_year_from_date = add_days(filters.from_date, +180)
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_data(filters):
	if filters.get("group_by") == "Asset Category":
		return get_group_by_asset_category_data(filters)


def get_group_by_asset_category_data(filters):
	data = []

	asset_categories = get_asset_categories_for_grouped_by_category(filters)
	# frappe.throw(f"{asset_categories,filters.half_year_from_date}")
	assets = get_assets_for_grouped_by_category(filters)

	for asset_category in asset_categories:
		row = frappe._dict()
		# row.asset_category = asset_category
		row.update(asset_category)

		# row.cost_as_on_to_date = (
		# 	flt(row.cost_as_on_from_date)
		# 	+ flt(row.cost_of_new_purchase)
		# 	- flt(row.cost_of_sold_asset)
		# 	- flt(row.cost_of_scrapped_asset)
		# )



		row.update(
			next(
				asset
				for asset in assets
				if asset["asset_category"] == asset_category.get("asset_category", "")
			)
		)

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
		)

		row.total_depreciation = (
			flt(row.depreciation_amount_during_the_period)
			+ flt(row.depreciation_amount_half_year)
			# - flt(row.depreciation_eliminated_during_the_period)
		)

		row.net_asset_value_as_on_from_date = flt(row.cost_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		# row.net_asset_value_as_on_to_date = flt(row.cost_as_on_to_date) - flt(
		# 	row.accumulated_depreciation_as_on_to_date
		# )
		row.one_plus_2_minus_3 = (
			flt(row.net_asset_value_as_on_from_date)
			+ flt(row.cost_of_new_purchase_more_than_180_days)
			- flt(row.cost_of_sold_asset_before_180_days)
			# - flt(row.cost_of_scrapped_asset)
		)

		row.five_minus_six = (
			flt(row.cost_of_new_purchase_less_than_180_days)
			- flt(row.cost_of_sold_asset_before_using_180_days)
		)

		row.net_asset_value_as_on_to_date = (
			flt(row.one_plus_2_minus_3)
			+ flt(row.five_minus_six)
			- flt(row.total_depreciation)
		)
		row.net_asset_value_as_on_to_date = 0 if row.net_asset_value_as_on_to_date < 0 else row.net_asset_value_as_on_to_date

		row.rate = 0
		AssetFinanceBook = DocType("Asset Finance Book")
		depri_rate = (
			db.get_values(
				AssetFinanceBook,
				filters={
					AssetFinanceBook.parent: asset_category.asset_category,
					AssetFinanceBook.finance_book: "Income Tax book"
				},
				fieldname="rate_of_depreciation",
				as_dict=1
			)
		)
		if depri_rate:
			row.rate = depri_rate[0].rate_of_depreciation
		data.append(row)

		row.capital_gain_or_loss = 0

		capital_gain_or_loss = frappe.db.sql("""
		SELECT SUM(gle.credit_in_account_currency - gle.debit_in_account_currency) as capital_gain,
		(ARRAY_AGG(gle.account))[1] as account, (ARRAY_AGG(a.asset_category))[1] as asset_category, (ARRAY_AGG(a.name))[1] as name, (ARRAY_AGG(sii.parent))[1] as parent
		FROM `tabSales Invoice Item` sii
		LEFT JOIN `tabGL Entry` gle ON gle.voucher_no = sii.parent
		LEFT JOIN `tabAsset` a
		ON a.name = sii.asset
		WHERE gle.company=%(company)s AND gle.voucher_subtype = 'Asset' AND gle.voucher_type = 'Sales Invoice' AND a.status = 'Sold'
		AND sii.income_account = %(disposal_account)s AND gle.account = %(disposal_account)s
		AND a.asset_category = %(asset_category)s AND gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
		""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"asset_category": asset_category.asset_category,
			"disposal_account":frappe.db.get_value("Company",filters.company,"disposal_account")
		},
		as_dict=1,)

		if capital_gain_or_loss:
			row.capital_gain_or_loss = capital_gain_or_loss[0].get("capital_gain")

	return data


def get_asset_categories_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition += " and asset_category = %(asset_category)s"
	# nosemgrep
	asset_data = frappe.db.sql(
		f"""
		SELECT a.asset_category,
			   ifnull(sum(case when a.available_for_use_date < %(from_date)s then
							   case when ifnull(a.disposal_date, 'epoch'::date) = 'epoch'::date or a.disposal_date >= %(from_date)s then
									a.gross_purchase_amount
							   else
									0
							   end
						   else
								0
						   end), 0) as cost_as_on_from_date,
			   ifnull(sum(case when a.available_for_use_date >= %(from_date)s then
			   						a.gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as cost_of_new_purchase,
				ifnull(sum(case when a.available_for_use_date >= %(half_year)s then
			   						a.gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as cost_of_new_purchase_less_than_180_days,
				ifnull(sum(case when a.available_for_use_date < %(half_year)s
									and a.available_for_use_date >= %(from_date)s
									then
			   						a.gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as cost_of_new_purchase_more_than_180_days,
			   ifnull(sum(case when ifnull(a.disposal_date, 'epoch'::date) != 'epoch'::date
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(half_year)s then
							   case when a.status in ('Sold','Scrapped') then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_sold_asset_after_using_180_days,
				ifnull(sum(case when ifnull(a.disposal_date, 'epoch'::date) != 'epoch'::date
			   						and a.disposal_date >= %(half_year)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status in ('Sold','Scrapped') then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_sold_asset_before_using_180_days,
				ifnull(sum(case when ifnull(a.disposal_date, 'epoch'::date) != 'epoch'::date
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status in ('Sold','Scrapped') then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_sold_asset
		from `tabAsset` a
		where docstatus=1 and company=%(company)s and purchase_date <= %(to_date)s {condition}
		and not exists(select name from `tabAsset Capitalization Asset Item` where asset = a.name)
		group by a.asset_category
		""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"half_year":filters.half_year_from_date,
			"asset_category": filters.get("asset_category"),
		},
		as_dict=1,
	)

	return asset_data

def get_assets_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition = " and a.asset_category = '{}'".format(filters.get("asset_category"))
	return frappe.db.sql(
		"""
		SELECT results.asset_category, (ARRAY_AGG(results.name))[1] as asset,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period,
			   sum(results.depreciation_amount_half_year) as depreciation_amount_half_year
		from (SELECT a.asset_category, (ARRAY_AGG(a.name))[1] as name,
				   ifnull(sum(case when gle.posting_date < %(from_date)s and (ifnull(a.disposal_date, 'epoch'::date) = 'epoch'::date or a.disposal_date >= %(from_date)s) then
								   gle.debit
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when ifnull(a.disposal_date, 'epoch'::date) != 'epoch'::date and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and gle.posting_date <= a.disposal_date then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
				   						and (a.available_for_use_date <= %(from_date)s )
										and (ifnull(a.disposal_date, 'epoch'::date) = 'epoch'::date or gle.posting_date <= a.disposal_date) then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_amount_during_the_period,
					ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
										and (a.available_for_use_date >= %(half_year)s and a.available_for_use_date <= %(to_date)s)
										and (ifnull(a.disposal_date, 'epoch'::date) = 'epoch'::date or gle.posting_date <= a.disposal_date) then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_amount_half_year

			from `tabGL Entry` gle
			join `tabAsset` a on
				gle.against_voucher = a.name
			join `tabAsset Category Account` aca on
				aca.parent = a.asset_category and aca.company_name = %(company)s
			join `tabCompany` company on
				company.name = %(company)s
			where a.docstatus=1 and gle.finance_book = %(finance_book)s and  a.company=%(company)s and a.purchase_date <= %(to_date)s and gle.debit != 0 and gle.is_cancelled = 0 and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account) {0}
			group by a.asset_category
			union
			SELECT a.asset_category, (ARRAY_AGG(a.name))[1] as name,
				   ifnull(sum(case when ifnull(a.disposal_date, 'epoch'::date) != 'epoch'::date and (a.disposal_date < %(from_date)s or a.disposal_date > %(to_date)s) then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when a.disposal_date >= %(from_date)s and a.disposal_date <= %(to_date)s then
								   a.opening_accumulated_depreciation
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   0 as depreciation_amount_during_the_period,
				   ifnull(sum(case when a.available_for_use_date >= %(half_year)s and a.available_for_use_date <= %(to_date)s then
								   a.opening_accumulated_depreciation
							  else
								   0
							  end), 0) as depreciation_amount_half_year
			from `tabAsset` a
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {0}
			group by a.asset_category) as results
		group by results.asset_category
		""".format(condition),
		{"finance_book":"Income Tax book","to_date": filters.to_date,
   		 "from_date": filters.from_date,
		 "company": filters.company,
		 "half_year":filters.half_year_from_date},
		as_dict=1,
	)


def get_columns(filters):
	columns = []

	if filters.get("group_by") == "Asset Category":
		columns.append(
			{
				"label": _("Block of Assets"),
				"fieldname": "asset_category",
				"fieldtype": "Link",
				"options": "Asset Category",
				"width": 120,
			}
		)

	columns += [
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Float",
			"width": 80,
		},
		{
			"label": _('WDV as on {0}').format(formatdate(filters.from_date)),
			"fieldname": "net_asset_value_as_on_from_date",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Addition used for more than 180 days"),
			"fieldname": "cost_of_new_purchase_more_than_180_days",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Sale out of 3 or 4"),
			"fieldname": "cost_of_sold_asset_after_using_180_days",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Opening WDV + Additions used for more than 180 days - Sale"),
			"fieldname": "one_plus_2_minus_3",
			"fieldtype": "Currency",
			"width": 140,
		},
				{
			"label": _("Addition used for less than 180 days"),
			"fieldname": "cost_of_new_purchase_less_than_180_days",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Sale out of 7"),
			"fieldname": "cost_of_sold_asset_before_using_180_days",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Addition used for less than 180 days - Sale out of 7"),
			"fieldname": "five_minus_six",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Depreciation for full year"),
			"fieldname": "depreciation_amount_during_the_period",
			"fieldtype": "Currency",
			"width": 240,
		},
		{
			"label": _("Depreciation for half year"),
			"fieldname": "depreciation_amount_half_year",
			"fieldtype": "Currency",
			"width": 240,
		},
		{
			"label": _("Additional Depreciation if any on 4"),
			"fieldname": "additional_depreciation_due_to_revalue",
			"fieldtype": "Currency",
			"width": 240,
		},
		{
			"label": _("Additional Depreciation if any on 7"),
			"fieldname": "additional_depreciation_due_to_revalue_within_180_days",
			"fieldtype": "Currency",
			"width": 240,
		},

		{
			"label": _("Total Depreciation") ,
			"fieldname": "total_depreciation",
			"fieldtype": "Currency",
			"width": 270,
		},
		{
			"label": _("Expenditure incurred in connection with tranfer of asset(s)") ,
			"fieldname": "transfer_expenses",
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"label": _("Capital Gains / Loss under Section 50") ,
			"fieldname": "capital_gain_or_loss",
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"label": _("W.D.V as on") + " " + formatdate(filters.to_date),
			"fieldname": "net_asset_value_as_on_to_date",
			"fieldtype": "Currency",
			"width": 200,
		},
	]

	return columns