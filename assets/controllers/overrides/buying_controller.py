from erpnext.controllers.buying_controller import BuyingController
from frappe import _
from frappe.utils import flt
from assets.controllers.doc_events.buying_controller import get_asset_items
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.controllers.buying_controller import update_regional_item_valuation_rate

class AssetsBuyingController(BuyingController):
	def validate_stock_or_nonstock_items(self):
		if self.meta.get_field("taxes") and not self.get_stock_items() and not get_asset_items(self):
			msg = _('Tax Category has been changed to "Total" because all the Items are non-stock items')
			self.update_tax_category(msg)

	# update valuation rate
	def update_valuation_rate(self, reset_outgoing_rate=True):
		"""
		item_tax_amount is the total tax amount applied on that item
		stored for valuation

		TODO: rename item_tax_amount to valuation_tax_amount
		"""
		stock_and_asset_items = []
		stock_and_asset_items = self.get_stock_items() + get_asset_items(self)

		stock_and_asset_items_qty, stock_and_asset_items_amount = 0, 0
		last_item_idx = 1
		for d in self.get("items"):
			if d.item_code and d.item_code in stock_and_asset_items:
				stock_and_asset_items_qty += flt(d.qty)
				stock_and_asset_items_amount += flt(d.base_net_amount)
				last_item_idx = d.idx

		total_valuation_amount = sum(
			flt(d.base_tax_amount_after_discount_amount)
			for d in self.get("taxes")
			if d.category in ["Valuation", "Valuation and Total"]
		)

		valuation_amount_adjustment = total_valuation_amount
		for i, item in enumerate(self.get("items")):
			if item.item_code and item.qty and item.item_code in stock_and_asset_items:
				item_proportion = (
					flt(item.base_net_amount) / stock_and_asset_items_amount
					if stock_and_asset_items_amount
					else flt(item.qty) / stock_and_asset_items_qty
				)

				if i == (last_item_idx - 1):
					item.item_tax_amount = flt(
						valuation_amount_adjustment, self.precision("item_tax_amount", item)
					)
				else:
					item.item_tax_amount = flt(
						item_proportion * total_valuation_amount, self.precision("item_tax_amount", item)
					)
					valuation_amount_adjustment -= item.item_tax_amount

				self.round_floats_in(item)
				if flt(item.conversion_factor) == 0.0:
					item.conversion_factor = (
						get_conversion_factor(item.item_code, item.uom).get("conversion_factor") or 1.0
					)

				net_rate = item.base_net_amount
				if item.sales_incoming_rate:  # for internal transfer
					net_rate = item.qty * item.sales_incoming_rate

				qty_in_stock_uom = flt(item.qty * item.conversion_factor)
				if self.get("is_old_subcontracting_flow"):
					item.rm_supp_cost = self.get_supplied_items_cost(item.name, reset_outgoing_rate)
					item.valuation_rate = (
						net_rate
						+ item.item_tax_amount
						+ item.rm_supp_cost
						+ flt(item.landed_cost_voucher_amount)
					) / qty_in_stock_uom
				else:
					item.valuation_rate = (
						net_rate
						+ item.item_tax_amount
						+ flt(item.landed_cost_voucher_amount)
						+ flt(item.get("rate_difference_with_purchase_invoice"))
					) / qty_in_stock_uom
			else:
				item.valuation_rate = 0.0
		update_regional_item_valuation_rate(self)