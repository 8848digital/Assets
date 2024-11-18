from assets.assets.doctype.asset.asset import is_cwip_accounting_enabled
from assets.assets.doctype.asset_category.asset_category import get_asset_category_account
import frappe
import erpnext
from erpnext.stock import get_warehouse_account_map
from frappe import _
from frappe.utils import cint, flt, get_link_to_form
from frappe import throw
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	get_item_account_wise_additional_cost,
)
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import get_purchase_document_details
from erpnext.accounts.utils import get_account_currency






def check_asset_cwip_enabled(self):
    # Check if there exists any item with cwip accounting enabled in it's asset category
    for item in self.get("items"):
        if item.item_code and item.is_fixed_asset:
            asset_category = frappe.get_cached_value("Item", item.item_code, "asset_category")
            if is_cwip_accounting_enabled(asset_category):
                return 1
    return 0

def set_expense_account(self, for_validate=False):
		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)

		if auto_accounting_for_stock:
			stock_not_billed_account = self.get_company_default("stock_received_but_not_billed")
			stock_items = self.get_stock_items()

		self.asset_received_but_not_billed = None

		if self.update_stock:
			self.validate_item_code()
			self.validate_warehouse(for_validate)
			if auto_accounting_for_stock:
				warehouse_account = get_warehouse_account_map(self.company)

		for item in self.get("items"):
			# in case of auto inventory accounting,
			# expense account is always "Stock Received But Not Billed" for a stock item
			# except opening entry, drop-ship entry and fixed asset items
			if (
				auto_accounting_for_stock
				and item.item_code in stock_items
				and self.is_opening == "No"
				and not item.is_fixed_asset
				and (
					not item.po_detail
					or not frappe.db.get_value("Purchase Order Item", item.po_detail, "delivered_by_supplier")
				)
			):
				if self.update_stock and item.warehouse and (not item.from_warehouse):
					if (
						for_validate
						and item.expense_account
						and item.expense_account != warehouse_account[item.warehouse]["account"]
					):
						msg = _(
							"Row {0}: Expense Head changed to {1} because account {2} is not linked to warehouse {3} or it is not the default inventory account"
						).format(
							item.idx,
							frappe.bold(warehouse_account[item.warehouse]["account"]),
							frappe.bold(item.expense_account),
							frappe.bold(item.warehouse),
						)
						frappe.msgprint(msg, title=_("Expense Head Changed"))
					item.expense_account = warehouse_account[item.warehouse]["account"]
				else:
					# check if 'Stock Received But Not Billed' account is credited in Purchase receipt or not
					if item.purchase_receipt:
						negative_expense_booked_in_pr = frappe.db.sql(
							"""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account = %s""",
							(item.purchase_receipt, stock_not_billed_account),
						)

						if negative_expense_booked_in_pr:
							if (
								for_validate
								and item.expense_account
								and item.expense_account != stock_not_billed_account
							):
								msg = _(
									"Row {0}: Expense Head changed to {1} because expense is booked against this account in Purchase Receipt {2}"
								).format(
									item.idx,
									frappe.bold(stock_not_billed_account),
									frappe.bold(item.purchase_receipt),
								)
								frappe.msgprint(msg, title=_("Expense Head Changed"))

							item.expense_account = stock_not_billed_account
					else:
						# If no purchase receipt present then book expense in 'Stock Received But Not Billed'
						# This is done in cases when Purchase Invoice is created before Purchase Receipt
						if (
							for_validate
							and item.expense_account
							and item.expense_account != stock_not_billed_account
						):
							msg = _(
								"Row {0}: Expense Head changed to {1} as no Purchase Receipt is created against Item {2}."
							).format(
								item.idx, frappe.bold(stock_not_billed_account), frappe.bold(item.item_code)
							)
							msg += "<br>"
							msg += _(
								"This is done to handle accounting for cases when Purchase Receipt is created after Purchase Invoice"
							)
							frappe.msgprint(msg, title=_("Expense Head Changed"))

						item.expense_account = stock_not_billed_account
			elif item.is_fixed_asset:
				account = None
				if not item.pr_detail and item.po_detail:
					receipt_item = frappe.get_cached_value(
						"Purchase Receipt Item",
						{
							"purchase_order": item.purchase_order,
							"purchase_order_item": item.po_detail,
							"docstatus": 1,
						},
						["name", "parent"],
						as_dict=1,
					)
					if receipt_item:
						item.pr_detail = receipt_item.name
						item.purchase_receipt = receipt_item.parent

				if item.pr_detail:
					if not self.asset_received_but_not_billed:
						self.asset_received_but_not_billed = self.get_company_default(
							"asset_received_but_not_billed"
						)

					# check if 'Asset Received But Not Billed' account is credited in Purchase receipt or not
					arbnb_booked_in_pr = frappe.db.get_value(
						"GL Entry",
						{
							"voucher_type": "Purchase Receipt",
							"voucher_no": item.purchase_receipt,
							"account": self.asset_received_but_not_billed,
						},
						"name",
					)
					if arbnb_booked_in_pr:
						account = self.asset_received_but_not_billed

				if not account:
					account_type = (
						"capital_work_in_progress_account"
						if is_cwip_accounting_enabled(item.asset_category)
						else "fixed_asset_account"
					)
					account = get_asset_category_account(
						account_type, item=item.item_code, company=self.company
					)
					if not account:
						form_link = get_link_to_form("Asset Category", item.asset_category)
						throw(
							_("Please set Fixed Asset Account in {} against {}.").format(
								form_link, self.company
							),
							title=_("Missing Account"),
						)
				item.expense_account = account
			elif not item.expense_account and for_validate:
				throw(_("Expense account is mandatory for item {0}").format(item.item_code or item.item_name))

def make_item_gl_entries(self, gl_entries):
		# item gl entries
		stock_items = self.get_stock_items()
		if self.update_stock and self.auto_accounting_for_stock:
			warehouse_account = get_warehouse_account_map(self.company)

		landed_cost_entries = get_item_account_wise_additional_cost(self.name)

		voucher_wise_stock_value = {}
		if self.update_stock:
			stock_ledger_entries = frappe.get_all(
				"Stock Ledger Entry",
				fields=["voucher_detail_no", "stock_value_difference", "warehouse"],
				filters={"voucher_no": self.name, "voucher_type": self.doctype, "is_cancelled": 0},
			)
			for d in stock_ledger_entries:
				voucher_wise_stock_value.setdefault(
					(d.voucher_detail_no, d.warehouse), d.stock_value_difference
				)

		valuation_tax_accounts = [
			d.account_head
			for d in self.get("taxes")
			if d.category in ("Valuation", "Total and Valuation")
			and flt(d.base_tax_amount_after_discount_amount)
		]

		exchange_rate_map, net_rate_map = get_purchase_document_details(self)

		provisional_accounting_for_non_stock_items = cint(
			frappe.get_cached_value(
				"Company", self.company, "enable_provisional_accounting_for_non_stock_items"
			)
		)
		if provisional_accounting_for_non_stock_items:
			self.get_provisional_accounts()

		for item in self.get("items"):
			if flt(item.base_net_amount):
				account_currency = get_account_currency(item.expense_account)
				if item.item_code:
					frappe.get_cached_value("Item", item.item_code, "asset_category")

				if (
					self.update_stock
					and self.auto_accounting_for_stock
					and (item.item_code in stock_items or item.is_fixed_asset)
				):
					# warehouse account
					warehouse_debit_amount = self.make_stock_adjustment_entry(
						gl_entries, item, voucher_wise_stock_value, account_currency
					)

					if item.from_warehouse:
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": warehouse_account[item.warehouse]["account"],
									"against": warehouse_account[item.from_warehouse]["account"],
									"cost_center": item.cost_center,
									"project": item.project or self.project,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"debit": warehouse_debit_amount,
								},
								warehouse_account[item.warehouse]["account_currency"],
								item=item,
							)
						)

						credit_amount = item.base_net_amount
						if self.is_internal_supplier and item.valuation_rate:
							credit_amount = flt(item.valuation_rate * item.stock_qty)

						# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": warehouse_account[item.from_warehouse]["account"],
									"against": warehouse_account[item.warehouse]["account"],
									"cost_center": item.cost_center,
									"project": item.project or self.project,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"debit": -1 * flt(credit_amount, item.precision("base_net_amount")),
								},
								warehouse_account[item.from_warehouse]["account_currency"],
								item=item,
							)
						)

						# Do not book expense for transfer within same company transfer
						if not self.is_internal_transfer():
							gl_entries.append(
								self.get_gl_dict(
									{
										"account": item.expense_account,
										"against": self.supplier,
										"debit": flt(item.base_net_amount, item.precision("base_net_amount")),
										"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
										"cost_center": item.cost_center,
										"project": item.project,
									},
									account_currency,
									item=item,
								)
							)

					else:
						if not self.is_internal_transfer():
							gl_entries.append(
								self.get_gl_dict(
									{
										"account": item.expense_account,
										"against": self.supplier,
										"debit": warehouse_debit_amount,
										"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
										"cost_center": item.cost_center,
										"project": item.project or self.project,
									},
									account_currency,
									item=item,
								)
							)

					# Amount added through landed-cost-voucher
					if landed_cost_entries:
						if (item.item_code, item.name) in landed_cost_entries:
							for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
								gl_entries.append(
									self.get_gl_dict(
										{
											"account": account,
											"against": item.expense_account,
											"cost_center": item.cost_center,
											"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
											"credit": flt(amount["base_amount"]),
											"credit_in_account_currency": flt(amount["amount"]),
											"project": item.project or self.project,
										},
										item=item,
									)
								)

					# sub-contracting warehouse
					if flt(item.rm_supp_cost):
						supplier_warehouse_account = warehouse_account[self.supplier_warehouse]["account"]
						if not supplier_warehouse_account:
							frappe.throw(
								_("Please set account in Warehouse {0}").format(self.supplier_warehouse)
							)
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": supplier_warehouse_account,
									"against": item.expense_account,
									"cost_center": item.cost_center,
									"project": item.project or self.project,
									"remarks": self.get("remarks") or _("Accounting Entry for Stock"),
									"credit": flt(item.rm_supp_cost),
								},
								warehouse_account[self.supplier_warehouse]["account_currency"],
								item=item,
							)
						)

				else:
					expense_account = (
						item.expense_account
						if (not item.enable_deferred_expense or self.is_return)
						else item.deferred_expense_account
					)

					dummy, amount = self.get_amount_and_base_amount(item, None)

					if provisional_accounting_for_non_stock_items:
						self.make_provisional_gl_entry(gl_entries, item)

					if not self.is_internal_transfer():
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": expense_account,
									"against": self.supplier,
									"debit": amount,
									"cost_center": item.cost_center,
									"project": item.project or self.project,
								},
								account_currency,
								item=item,
							)
						)

						# check if the exchange rate has changed
						if item.get("purchase_receipt") and self.auto_accounting_for_stock:
							if (
								exchange_rate_map[item.purchase_receipt]
								and self.conversion_rate != exchange_rate_map[item.purchase_receipt]
								and item.net_rate == net_rate_map[item.pr_detail]
							):
								discrepancy_caused_by_exchange_rate_difference = (
									item.qty * item.net_rate
								) * (exchange_rate_map[item.purchase_receipt] - self.conversion_rate)

								gl_entries.append(
									self.get_gl_dict(
										{
											"account": expense_account,
											"against": self.supplier,
											"debit": discrepancy_caused_by_exchange_rate_difference,
											"cost_center": item.cost_center,
											"project": item.project or self.project,
										},
										account_currency,
										item=item,
									)
								)
								gl_entries.append(
									self.get_gl_dict(
										{
											"account": self.get_company_default("exchange_gain_loss_account"),
											"against": self.supplier,
											"credit": discrepancy_caused_by_exchange_rate_difference,
											"cost_center": item.cost_center,
											"project": item.project or self.project,
										},
										account_currency,
										item=item,
									)
								)
			if (
				self.auto_accounting_for_stock
				and self.is_opening == "No"
				and item.item_code in stock_items
				and item.item_tax_amount
			):
				# Post reverse entry for Stock-Received-But-Not-Billed if it is booked in Purchase Receipt
				if item.purchase_receipt and valuation_tax_accounts:
					negative_expense_booked_in_pr = frappe.db.sql(
						"""select name from `tabGL Entry`
							where voucher_type='Purchase Receipt' and voucher_no=%s and account in %s""",
						(item.purchase_receipt, valuation_tax_accounts),
					)

					stock_rbnb = (
						self.get_company_default("asset_received_but_not_billed")
						if item.is_fixed_asset
						else self.stock_received_but_not_billed
					)

					if not negative_expense_booked_in_pr:
						gl_entries.append(
							self.get_gl_dict(
								{
									"account": stock_rbnb,
									"against": self.supplier,
									"debit": flt(item.item_tax_amount, item.precision("item_tax_amount")),
									"remarks": self.remarks or _("Accounting Entry for Stock"),
									"cost_center": self.cost_center,
									"project": item.project or self.project,
								},
								item=item,
							)
						)

						self.negative_expense_to_be_booked += flt(
							item.item_tax_amount, item.precision("item_tax_amount")
						)

			if item.is_fixed_asset and item.landed_cost_voucher_amount:
				self.update_gross_purchase_amount_for_linked_assets(item)

def update_gross_purchase_amount_for_linked_assets(self, item):
    assets = frappe.db.get_all(
        "Asset",
        filters={"purchase_invoice": self.name, "item_code": item.item_code},
        fields=["name", "asset_quantity"],
    )
    for asset in assets:
        purchase_amount = flt(item.valuation_rate) * asset.asset_quantity
        frappe.db.set_value(
            "Asset",
            asset.name,
            {
                "gross_purchase_amount": purchase_amount,
                "purchase_amount": purchase_amount,
            },
        )