# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from assets.assets.doctype.asset.depreciation import post_depreciation_entries
from assets.assets.doctype.asset.test_asset import create_asset, create_asset_data
from assets.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_depr_schedule,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import TestSalesInvoice, create_sales_invoice

class AssetsTestSalesInvoice(TestSalesInvoice):
    def test_gle_made_when_asset_is_returned(self):
        create_asset_data()
        asset = create_asset(item_code="Macbook Pro")

        si = create_sales_invoice(item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000)
        return_si = create_sales_invoice(
            is_return=1,
            return_against=si.name,
            item_code="Macbook Pro",
            asset=asset.name,
            qty=-1,
            rate=90000,
        )

        disposal_account = frappe.get_cached_value("Company", "_Test Company", "disposal_account")

        # Asset value is 100,000 but it was sold for 90,000, so there should be a loss of 10,000
        loss_for_si = frappe.get_all(
            "GL Entry",
            filters={"voucher_no": si.name, "account": disposal_account},
            fields=["credit", "debit"],
        )[0]

        loss_for_return_si = frappe.get_all(
            "GL Entry",
            filters={"voucher_no": return_si.name, "account": disposal_account},
            fields=["credit", "debit"],
        )[0]

        self.assertEqual(loss_for_si["credit"], loss_for_return_si["debit"])
        self.assertEqual(loss_for_si["debit"], loss_for_return_si["credit"])

    def test_asset_depreciation_on_sale_with_pro_rata(self):
        """
        Tests if an Asset set to depreciate yearly on June 30, that gets sold on Sept 30, creates an additional depreciation entry on its date of sale.
        """

        create_asset_data()
        asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, submit=1)
        post_depreciation_entries(getdate("2021-09-30"))

        create_sales_invoice(
            item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-09-30")
        )
        asset.load_from_db()

        expected_values = [
            ["2020-06-30", 1366.12, 1366.12],
            ["2021-06-30", 20000.0, 21366.12],
            ["2021-09-30", 5041.1, 26407.22],
        ]

        for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
            self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
            self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
            self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
            self.assertTrue(schedule.journal_entry)

    def test_asset_depreciation_on_sale_without_pro_rata(self):
        """
        Tests if an Asset set to depreciate yearly on Dec 31, that gets sold on Dec 31 after two years, created an additional depreciation entry on its date of sale.
        """

        create_asset_data()
        asset = create_asset(
            item_code="Macbook Pro",
            calculate_depreciation=1,
            available_for_use_date=getdate("2019-12-31"),
            total_number_of_depreciations=3,
            expected_value_after_useful_life=10000,
            depreciation_start_date=getdate("2020-12-31"),
            submit=1,
        )

        post_depreciation_entries(getdate("2021-09-30"))

        create_sales_invoice(
            item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-12-31")
        )
        asset.load_from_db()

        expected_values = [["2020-12-31", 30000, 30000], ["2021-12-31", 30000, 60000]]

        for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
            self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
            self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
            self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
            self.assertTrue(schedule.journal_entry)

    def test_depreciation_on_return_of_sold_asset(self):
        from erpnext.controllers.sales_and_purchase_return import make_return_doc

        create_asset_data()
        asset = create_asset(item_code="Macbook Pro", calculate_depreciation=1, submit=1)
        post_depreciation_entries(getdate("2021-09-30"))

        si = create_sales_invoice(
            item_code="Macbook Pro", asset=asset.name, qty=1, rate=90000, posting_date=getdate("2021-09-30")
        )
        return_si = make_return_doc("Sales Invoice", si.name)
        return_si.submit()
        asset.load_from_db()

        expected_values = [
            ["2020-06-30", 1366.12, 1366.12, True],
            ["2021-06-30", 20000.0, 21366.12, True],
            ["2022-06-30", 20000.0, 41366.12, False],
            ["2023-06-30", 20000.0, 61366.12, False],
            ["2024-06-30", 20000.0, 81366.12, False],
            ["2025-06-06", 18633.88, 100000.0, False],
        ]

        for i, schedule in enumerate(get_depr_schedule(asset.name, "Active")):
            self.assertEqual(getdate(expected_values[i][0]), schedule.schedule_date)
            self.assertEqual(expected_values[i][1], schedule.depreciation_amount)
            self.assertEqual(expected_values[i][2], schedule.accumulated_depreciation_amount)
            self.assertEqual(schedule.journal_entry, schedule.journal_entry)