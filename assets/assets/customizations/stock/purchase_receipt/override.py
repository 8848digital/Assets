import frappe
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_stock_value_difference, get_item_account_wise_additional_cost
from frappe.utils import cint, flt
from erpnext.accounts.utils import get_account_currency
import erpnext
from assets.assets.doctype.asset.asset import get_asset_account, is_cwip_accounting_enabled
from erpnext.controllers.accounts_controller import merge_taxes
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_returned_qty_map, get_invoiced_qty_map
from frappe.model.mapper import get_mapped_doc
from frappe import _

def make_item_gl_entries(self, gl_entries, warehouse_account=None):
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import (
		get_purchase_document_details,
	)

	provisional_accounting_for_non_stock_items = cint(
		frappe.db.get_value("Company", self.company, "enable_provisional_accounting_for_non_stock_items")
	)

	exchange_rate_map, net_rate_map = get_purchase_document_details(self)

	def validate_account(account_type):
		frappe.throw(_("{0} account not found while submitting purchase receipt").format(account_type))

	def make_item_asset_inward_gl_entry(item, stock_value_diff, stock_asset_account_name):
		account_currency = get_account_currency(stock_asset_account_name)

		if not stock_asset_account_name:
			validate_account("Asset or warehouse account")

		self.add_gl_entry(
			gl_entries=gl_entries,
			account=stock_asset_account_name,
			cost_center=d.cost_center,
			debit=stock_value_diff,
			credit=0.0,
			remarks=remarks,
			against_account=stock_asset_rbnb,
			account_currency=account_currency,
			item=item,
		)

	def make_stock_received_but_not_billed_entry(item):
		account = (
			warehouse_account[item.from_warehouse]["account"] if item.from_warehouse else stock_asset_rbnb
		)
		account_currency = get_account_currency(account)

		# GL Entry for from warehouse or Stock Received but not billed
		# Intentionally passed negative debit amount to avoid incorrect GL Entry validation
		credit_amount = (
			flt(item.base_net_amount, item.precision("base_net_amount"))
			if account_currency == self.company_currency
			else flt(item.net_amount, item.precision("net_amount"))
		)

		outgoing_amount = item.base_net_amount
		if self.is_internal_transfer() and item.valuation_rate:
			outgoing_amount = abs(get_stock_value_difference(self.name, item.name, item.from_warehouse))
			credit_amount = outgoing_amount

		if credit_amount:
			if not account:
				validate_account("Stock or Asset Received But Not Billed")

			self.add_gl_entry(
				gl_entries=gl_entries,
				account=account,
				cost_center=item.cost_center,
				debit=-1 * flt(outgoing_amount, item.precision("base_net_amount")),
				credit=0.0,
				remarks=remarks,
				against_account=stock_asset_account_name,
				debit_in_account_currency=-1 * flt(outgoing_amount, item.precision("base_net_amount")),
				account_currency=account_currency,
				item=item,
			)

			# check if the exchange rate has changed
			if d.get("purchase_invoice"):
				if (
					exchange_rate_map[item.purchase_invoice]
					and self.conversion_rate != exchange_rate_map[item.purchase_invoice]
					and item.net_rate == net_rate_map[item.purchase_invoice_item]
				):
					discrepancy_caused_by_exchange_rate_difference = (item.qty * item.net_rate) * (
						exchange_rate_map[item.purchase_invoice] - self.conversion_rate
					)

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=discrepancy_caused_by_exchange_rate_difference,
						remarks=remarks,
						against_account=self.supplier,
						debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
						account_currency=account_currency,
						item=item,
					)

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=self.get_company_default("exchange_gain_loss_account"),
						cost_center=d.cost_center,
						debit=discrepancy_caused_by_exchange_rate_difference,
						credit=0.0,
						remarks=remarks,
						against_account=self.supplier,
						debit_in_account_currency=-1 * discrepancy_caused_by_exchange_rate_difference,
						account_currency=account_currency,
						item=item,
					)

		return outgoing_amount

	def make_landed_cost_gl_entries(item):
		# Amount added through landed-cost-voucher
		if item.landed_cost_voucher_amount and landed_cost_entries:
			if (item.item_code, item.name) in landed_cost_entries:
				for account, amount in landed_cost_entries[(item.item_code, item.name)].items():
					account_currency = get_account_currency(account)
					credit_amount = (
						flt(amount["base_amount"])
						if (amount["base_amount"] or account_currency != self.company_currency)
						else flt(amount["amount"])
					)

					if not account:
						validate_account("Landed Cost Account")

					self.add_gl_entry(
						gl_entries=gl_entries,
						account=account,
						cost_center=item.cost_center,
						debit=0.0,
						credit=credit_amount,
						remarks=remarks,
						against_account=stock_asset_account_name,
						credit_in_account_currency=flt(amount["amount"]),
						account_currency=account_currency,
						project=item.project,
						item=item,
					)

	def make_rate_difference_entry(item):
		if item.rate_difference_with_purchase_invoice and stock_asset_rbnb:
			account_currency = get_account_currency(stock_asset_rbnb)
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=stock_asset_rbnb,
				cost_center=item.cost_center,
				debit=0.0,
				credit=flt(item.rate_difference_with_purchase_invoice),
				remarks=_("Adjustment based on Purchase Invoice rate"),
				against_account=stock_asset_account_name,
				account_currency=account_currency,
				project=item.project,
				item=item,
			)

	def make_sub_contracting_gl_entries(item):
		# sub-contracting warehouse
		if flt(item.rm_supp_cost) and warehouse_account.get(self.supplier_warehouse):
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=supplier_warehouse_account,
				cost_center=item.cost_center,
				debit=0.0,
				credit=flt(item.rm_supp_cost),
				remarks=remarks,
				against_account=stock_asset_account_name,
				account_currency=supplier_warehouse_account_currency,
				item=item,
			)

	def make_divisional_loss_gl_entry(item, outgoing_amount):
		if item.is_fixed_asset:
			return

		# divisional loss adjustment
		valuation_amount_as_per_doc = (
			flt(outgoing_amount, d.precision("base_net_amount"))
			+ flt(item.landed_cost_voucher_amount)
			+ flt(item.rm_supp_cost)
			+ flt(item.item_tax_amount)
			+ flt(item.rate_difference_with_purchase_invoice)
		)

		divisional_loss = flt(
			valuation_amount_as_per_doc - flt(stock_value_diff), item.precision("base_net_amount")
		)

		if divisional_loss:
			loss_account = (
				self.get_company_default("default_expense_account", ignore_validation=True)
				or stock_asset_rbnb
			)

			cost_center = item.cost_center or frappe.get_cached_value(
				"Company", self.company, "cost_center"
			)
			account_currency = get_account_currency(loss_account)
			self.add_gl_entry(
				gl_entries=gl_entries,
				account=loss_account,
				cost_center=cost_center,
				debit=divisional_loss,
				credit=0.0,
				remarks=remarks,
				against_account=stock_asset_account_name,
				account_currency=account_currency,
				project=item.project,
				item=item,
			)

	stock_items = self.get_stock_items()
	warehouse_with_no_account = []

	for d in self.get("items"):
		if (
			provisional_accounting_for_non_stock_items
			and d.item_code not in stock_items
			and flt(d.qty)
			and d.get("provisional_expense_account")
			and not d.is_fixed_asset
		):
			self.add_provisional_gl_entry(
				d, gl_entries, self.posting_date, d.get("provisional_expense_account")
			)
		elif flt(d.qty) and (flt(d.valuation_rate) or self.is_return):
			remarks = self.get("remarks") or _("Accounting Entry for {0}").format(
				"Asset" if d.is_fixed_asset else "Stock"
			)

			if not (
				(erpnext.is_perpetual_inventory_enabled(self.company) and d.item_code in stock_items)
				or (d.is_fixed_asset and not d.purchase_invoice)
			):
				continue

			stock_asset_rbnb = (
				self.get_company_default("asset_received_but_not_billed")
				if d.is_fixed_asset
				else self.get_company_default("stock_received_but_not_billed")
			)
			landed_cost_entries = get_item_account_wise_additional_cost(self.name)

			if d.is_fixed_asset:
				account_type = (
					"capital_work_in_progress_account"
					if is_cwip_accounting_enabled(d.asset_category)
					else "fixed_asset_account"
				)

				stock_asset_account_name = get_asset_account(
					account_type, asset_category=d.asset_category, company=self.company
				)

				stock_value_diff = (
					flt(d.base_net_amount) + flt(d.item_tax_amount) + flt(d.landed_cost_voucher_amount)
				)
			elif warehouse_account.get(d.warehouse):
				stock_value_diff = get_stock_value_difference(self.name, d.name, d.warehouse)
				stock_asset_account_name = warehouse_account[d.warehouse]["account"]
				supplier_warehouse_account = warehouse_account.get(self.supplier_warehouse, {}).get(
					"account"
				)
				supplier_warehouse_account_currency = warehouse_account.get(
					self.supplier_warehouse, {}
				).get("account_currency")

				# If PR is sub-contracted and fg item rate is zero
				# in that case if account for source and target warehouse are same,
				# then GL entries should not be posted
				if (
					flt(stock_value_diff) == flt(d.rm_supp_cost)
					and warehouse_account.get(self.supplier_warehouse)
					and stock_asset_account_name == supplier_warehouse_account
				):
					continue

			if (flt(d.valuation_rate) or self.is_return or d.is_fixed_asset) and flt(d.qty):
				make_item_asset_inward_gl_entry(d, stock_value_diff, stock_asset_account_name)
				outgoing_amount = make_stock_received_but_not_billed_entry(d)
				make_landed_cost_gl_entries(d)
				make_rate_difference_entry(d)
				make_sub_contracting_gl_entries(d)
				make_divisional_loss_gl_entry(d, outgoing_amount)
		elif (d.warehouse and d.warehouse not in warehouse_with_no_account) or (
			d.rejected_warehouse and d.rejected_warehouse not in warehouse_with_no_account
		):
			warehouse_with_no_account.append(d.warehouse or d.rejected_warehouse)

		if d.is_fixed_asset and d.landed_cost_voucher_amount:
			self.update_assets(d, d.valuation_rate)

	if warehouse_with_no_account:
		frappe.msgprint(
			_("No accounting entries for the following warehouses")
			+ ": \n"
			+ "\n".join(warehouse_with_no_account)
		)

def update_assets(self, item, valuation_rate):
    assets = frappe.db.get_all(
        "Asset",
        filters={"purchase_receipt": self.name, "item_code": item.item_code},
        fields=["name", "asset_quantity"],
    )

    for asset in assets:
        purchase_amount = flt(valuation_rate) * asset.asset_quantity
        frappe.db.set_value(
            "Asset",
            asset.name,
            {
                "gross_purchase_amount": purchase_amount,
                "purchase_amount": purchase_amount,
            },
        )

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None, args=None):
	from erpnext.accounts.party import get_payment_terms_template

	doc = frappe.get_doc("Purchase Receipt", source_name)
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been Invoiced/Returned"))

		doc = frappe.get_doc(target)
		doc.payment_terms_template = get_payment_terms_template(source.supplier, "Supplier", source.company)
		doc.run_method("onload")
		doc.run_method("set_missing_values")

		if args and args.get("merge_taxes"):
			merge_taxes(source.get("taxes") or [], doc)

		doc.run_method("calculate_taxes_and_totals")
		doc.set_payment_schedule()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty, returned_qty = get_pending_qty(source_doc)
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			target_doc.rejected_qty = 0
		target_doc.stock_qty = flt(target_doc.qty) * flt(
			target_doc.conversion_factor, target_doc.precision("conversion_factor")
		)
		returned_qty_map[source_doc.name] = returned_qty

	def get_pending_qty(item_row):
		qty = item_row.qty
		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			qty = item_row.received_qty

		pending_qty = qty - invoiced_qty_map.get(item_row.name, 0)

		if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
			return pending_qty, 0

		returned_qty = flt(returned_qty_map.get(item_row.name, 0))
		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0

		return pending_qty, returned_qty

	doclist = get_mapped_doc(
		"Purchase Receipt",
		source_name,
		{
			"Purchase Receipt": {
				"doctype": "Purchase Invoice",
				"field_map": {
					"supplier_warehouse": "supplier_warehouse",
					"is_return": "is_return",
					"bill_date": "bill_date",
				},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Purchase Receipt Item": {
				"doctype": "Purchase Invoice Item",
				"field_map": {
					"name": "pr_detail",
					"parent": "purchase_receipt",
					"qty": "received_qty",
					"purchase_order_item": "po_detail",
					"purchase_order": "purchase_order",
					"is_fixed_asset": "is_fixed_asset",
					"asset_location": "asset_location",
					"asset_category": "asset_category",
					"wip_composite_asset": "wip_composite_asset",
				},
				"postprocess": update_item,
				"filter": lambda d: get_pending_qty(d)[0] <= 0
				if not doc.get("is_return")
				else get_pending_qty(d)[0] > 0,
			},
			"Purchase Taxes and Charges": {
				"doctype": "Purchase Taxes and Charges",
				"add_if_empty": True,
				"ignore": args.get("merge_taxes") if args else 0,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist