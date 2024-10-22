# Copyright (c) 2024, 8848 digital and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_days, flt, formatdate


def execute(filters=None):
	filters.day_before_from_date = add_days(filters.from_date, -1)
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_data(filters):
	if filters.get("group_by") == "Asset Category":
		return get_group_by_asset_category_data(filters)
	elif filters.get("group_by") == "Asset":
		return get_group_by_asset_data(filters)


def get_group_by_asset_category_data(filters):
	data = []

	asset_categories = get_asset_categories_for_grouped_by_category(filters)
	assets = get_assets_for_grouped_by_category(filters)

	for asset_category in asset_categories:
		row = frappe._dict()
		# row.asset_category = asset_category
		row.update(asset_category)

		row.cost_as_on_to_date = (
			flt(row.cost_as_on_from_date)
			+ flt(row.cost_of_new_purchase)
			- flt(row.cost_of_sold_asset)
			- flt(row.cost_of_scrapped_asset)
		)

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

		row.net_asset_value_as_on_from_date = flt(row.cost_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.cost_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return data


def get_asset_categories_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition += " and asset_category = %(asset_category)s"
	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT a.asset_category,
			   ifnull(sum(case when a.purchase_date < %(from_date)s then
							   case when ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s then
									a.gross_purchase_amount
							   else
									0
							   end
						   else
								0
						   end), 0) as cost_as_on_from_date,
			   ifnull(sum(case when a.purchase_date >= %(from_date)s then
			   						a.gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as cost_of_new_purchase,
			   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Sold" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_sold_asset,
			   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Scrapped" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_scrapped_asset
		from `tabAsset` a
		where docstatus=1 and company=%(company)s and purchase_date <= %(to_date)s {condition}
		and not exists(select name from `tabAsset Capitalization Asset Item` where asset = a.name)
		group by a.asset_category
	""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"asset_category": filters.get("asset_category"),
		},
		as_dict=1,
	)


def get_asset_details_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset"):
		condition += " and name = %(asset)s"
	return frappe.db.sql(
		f"""
		SELECT name,
			   ifnull(sum(case when purchase_date < %(from_date)s then
							   case when ifnull(disposal_date, 'epoch'::date) = 'epoch'::date or disposal_date >= %(from_date)s then
									gross_purchase_amount
							   else
									0
							   end
						   else
								0
						   end), 0) as cost_as_on_from_date,
			   ifnull(sum(case when purchase_date >= %(from_date)s then
			   						gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as cost_of_new_purchase,
			   ifnull(sum(case when ifnull(disposal_date, 'epoch'::date) != 'epoch'::date
			   						and disposal_date >= %(from_date)s
			   						and disposal_date <= %(to_date)s then
							   case when status = 'Sold' then
							   		gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_sold_asset,
			   ifnull(sum(case when ifnull(disposal_date, 'epoch'::date) != 'epoch'::date
			   						and disposal_date >= %(from_date)s
			   						and disposal_date <= %(to_date)s then
							   case when status = 'Scrapped' then
							   		gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as cost_of_scrapped_asset
		from `tabAsset`
		where docstatus=1 and company=%(company)s and purchase_date <= %(to_date)s {condition}
		group by name
	""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"asset": filters.get("asset"),
		},
		as_dict=1,
	)


def get_group_by_asset_data(filters):
	data = []

	asset_details = get_asset_details_for_grouped_by_category(filters)
	assets = get_assets_for_grouped_by_asset(filters)

	for asset_detail in asset_details:
		row = frappe._dict()
		# row.asset_category = asset_category
		row.update(asset_detail)

		row.cost_as_on_to_date = (
			flt(row.cost_as_on_from_date)
			+ flt(row.cost_of_new_purchase)
			- flt(row.cost_of_sold_asset)
			- flt(row.cost_of_scrapped_asset)
		)

		row.update(next(asset for asset in assets if asset["asset"] == asset_detail.get("name", "")))

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
		)

		row.net_asset_value_as_on_from_date = flt(row.cost_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.cost_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return aggregate_and_calculate_subtotals(data)

def aggregate_and_calculate_subtotals(data):
    # Adjust cost_of_sold_asset by adding cost_of_scrapped_asset
    for entry in data:
        entry['cost_of_sold_asset'] += entry['cost_of_scrapped_asset']

    # Aggregation based on asset_name and asset_category
    aggregated_data = {}
    for entry in data:
        asset_name = entry['asset_name']
        if asset_name not in aggregated_data:
            aggregated_data[asset_name] = {
                'asset_name': asset_name,
                'asset_category': entry['asset_category'],
                'cost_as_on_from_date': 0,
                'cost_of_new_purchase': 0,
                'cost_of_sold_asset': 0,
                'cost_as_on_to_date': 0,
                'accumulated_depreciation_as_on_from_date': 0,
                'depreciation_eliminated_during_the_period': 0,
                'depreciation_amount_during_the_period': 0,
                'accumulated_depreciation_as_on_to_date': 0,
                'net_asset_value_as_on_from_date': 0,
                'net_asset_value_as_on_to_date': 0
            }
        for key in aggregated_data[asset_name]:
            if key != 'asset_name' and key != 'asset_category':
                aggregated_data[asset_name][key] += entry[key]

    # Convert aggregated data to a list and sort by asset_category
    result_sorted = sorted(aggregated_data.values(), key=lambda x: x['asset_category'])

    final_list = []
    subtotal = {key: 0 for key in result_sorted[0] if key != 'asset_name' and key != 'asset_category'}
    last_category = ""

    for row in result_sorted:
        if last_category != row["asset_category"]:
            if last_category:  # Add subtotal for the previous category
                final_list.append({"asset_name": "Sub-total", "asset_category": last_category, **subtotal})

            # Reset subtotal for the new category
            last_category = row["asset_category"]
            subtotal = {key: 0 for key in subtotal}
            final_list.append({"asset_name": row["asset_category"], "asset_category": row["asset_category"]})

        # Accumulate subtotals for the current category
        for key in subtotal:
            subtotal[key] += row[key]

        final_list.append(row)

    # Add the final subtotal after the loop
    if last_category:
        final_list.append({"asset_name": "Sub-total", "asset_category": last_category, **subtotal})

    return final_list



def get_assets_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition = " and a.asset_category = '{}'".format(filters.get("asset_category"))
	return frappe.db.sql(
		"""
		SELECT results.asset_category,results.name as asset,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.asset_category,a.name,
				   ifnull(sum(case when gle.posting_date < %(from_date)s and (ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s) then
								   gle.debit
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and gle.posting_date <= a.disposal_date then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
										and (ifnull(a.disposal_date, 0) = 0 or gle.posting_date <= a.disposal_date) then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_amount_during_the_period
			from `tabGL Entry` gle
			join `tabAsset` a on
				gle.against_voucher = a.name
			join `tabAsset Category Account` aca on
				aca.parent = a.asset_category and aca.company_name = %(company)s
			join `tabCompany` company on
				company.name = %(company)s
			where a.docstatus=1 and gle.finance_book = %(finance_book)s and a.company=%(company)s and a.purchase_date <= %(to_date)s and gle.debit != 0 and gle.is_cancelled = 0 and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account) {0}
			group by a.asset_category
			union
			SELECT a.asset_category,a.name,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and (a.disposal_date < %(from_date)s or a.disposal_date > %(to_date)s) then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when a.disposal_date >= %(from_date)s and a.disposal_date <= %(to_date)s then
								   a.opening_accumulated_depreciation
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   0 as depreciation_amount_during_the_period
			from `tabAsset` a
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {0}
			group by a.asset_category) as results
		group by results.asset_category
		""".format(condition),
		{
		"finance_book":"Company Act","to_date": filters.to_date,
   		"from_date": filters.from_date,
   		"company": filters.company},
		as_dict=1,
	)


def get_assets_for_grouped_by_asset(filters):
	condition = ""
	if filters.get("asset"):
		condition = " and a.name = '{}'".format(filters.get("asset"))
	return frappe.db.sql(
		"""
		SELECT results.name as asset, (ARRAY_AGG(results.asset_category))[1] as asset_category, (ARRAY_AGG(results.asset_name))[1] as asset_name,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.name as name,a.asset_category,a.asset_name,
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
										and (ifnull(a.disposal_date, 'epoch'::date) = 'epoch'::date or gle.posting_date <= a.disposal_date) then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_amount_during_the_period
			from `tabGL Entry` gle
			join `tabAsset` a on
				gle.against_voucher = a.name
			join `tabAsset Category Account` aca on
				aca.parent = a.asset_category and aca.company_name = %(company)s
			join `tabCompany` company on
				company.name = %(company)s
			where a.docstatus=1 and gle.finance_book = %(finance_book)s and a.company=%(company)s and a.purchase_date <= %(to_date)s and gle.debit != 0 and gle.is_cancelled = 0 and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account) {0}
			group by a.name
			union
			SELECT a.name as name,a.asset_category,a.asset_name,
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
				   0 as depreciation_amount_during_the_period
			from `tabAsset` a
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {0}
			group by a.name) as results
		group by results.name
		""".format(condition),
		{"finance_book":"Company Act",
   		"to_date": filters.to_date,
		"from_date": filters.from_date,
		  "company": filters.company},
		as_dict=1,
	)


def get_columns(filters):
	columns = []

	if filters.get("group_by") == "Asset Category":
		columns.append(
			{
				"label": _("Asset Category"),
				"fieldname": "asset_category",
				"fieldtype": "Link",
				"options": "Asset Category",
				"width": 120,
			}
		)
	elif filters.get("group_by") == "Asset":
		columns.append(
			{
					"label": _("DESCRIPTION OF ASSETS"),
					"fieldname": "asset_name",
					"fieldtype": "data",
					"width": 120,
			}
                )

	columns += [
		 {
				"label": _("GROSS BLOCK as on") + " " + formatdate(filters.from_date),
				"fieldname": "cost_as_on_from_date",
				"fieldtype": "Data",
				"width": 140,
		},
		{
				"label": _("Additions / Transfer In"),
				"fieldname": "cost_of_new_purchase",
				"fieldtype": "Data",
				"width": 140,
		},
		{
				"label": _("Deductions /Transfer Out"),
				"fieldname": "cost_of_sold_asset",
				"fieldtype": "Data",
				"width": 140,
		},
		{
				"label": _("GROSS BLOCK as on") + " " + formatdate(filters.to_date),
				"fieldname": "cost_as_on_to_date",
				"fieldtype": "Data",
				"width": 140,
		},
		{
				"label": _("Accumulated Depreciation up to") + " " + formatdate(filters.from_date),
				"fieldname": "accumulated_depreciation_as_on_from_date",
				"fieldtype": "Data",
				"width": 270,
		},
		{
				"label": _("Depreciation for the year"),
				"fieldname": "depreciation_amount_during_the_period",
				"fieldtype": "Data",
				"width": 240,
		},
		{
				"label": _("Depreciation on Deductions /Transfer Out"),
				"fieldname": "depreciation_eliminated_during_the_period",
				"fieldtype": "Data",
				"width": 300,
		},
		{
				"label": _("Accumulated Depreciation as up to") + " " + formatdate(filters.to_date),
				"fieldname": "accumulated_depreciation_as_on_to_date",
				"fieldtype": "Data",
				"width": 270,
		},
		{
				"label": _("Net Block as on") + " " + formatdate(filters.from_date),
				"fieldname": "net_asset_value_as_on_from_date",
				"fieldtype": "Data",
				"width": 200,
		},
		{
				"label": _("Net Block as on") + " " + formatdate(filters.to_date),
				"fieldname": "net_asset_value_as_on_to_date",
				"fieldtype": "Data",
				"width": 200,
		},
	]

	return columns