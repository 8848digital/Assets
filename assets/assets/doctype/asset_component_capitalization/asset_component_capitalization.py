import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import DocType
from erpnext.accounts.utils import get_fiscal_year


class AssetComponentCapitalization(Document):
	def on_submit(self):
		self.validate_asset_is_capitalized_or_draft()
		self.gl_entry(cancelled=False)
		self.update_asset_is_capitalized(is_capitalized=1)

	def before_cancel(self):
		self.gl_entry(cancelled=True)
		self.update_asset_is_capitalized(is_capitalized=0)

	def validate_asset_is_capitalized_or_draft(self):
		asset_not_submitted_list = []
		for component in self.component_asset:
			if not frappe.db.get_value("Asset", component.asset, "docstatus"):
				asset_not_submitted_list.append(component.asset)

		if asset_not_submitted_list:
			asset_links = [f'<a href="/app/asset/{asset}" target="_blank">{asset}</a>' for asset in asset_not_submitted_list]
			error_message = "The following assets are not submitted: " + ", ".join(asset_links)
			frappe.throw(_(error_message))

		return asset_not_submitted_list

	def gl_entry(self, cancelled):
		posting_date = self.posting_date
		current_fiscal_year = get_fiscal_year(posting_date, as_dict=True).get("name")

		components = {}
		# Consolidate credit entries for each unique account
		for row in self.component_asset:
			asset_category_data = frappe.db.get_value(
				"Asset", row.asset, ["asset_category", "gross_purchase_amount"], as_dict=True
			)
			cwip_account = frappe.db.get_value(
				"Asset Category Account",
				{"parent": asset_category_data["asset_category"], "company_name": self.company},
				"capital_work_in_progress_account"
			)

			if cwip_account in components:
				components[cwip_account]["credit_in_account_currency"] += asset_category_data["gross_purchase_amount"]
			else:
				components[cwip_account] = {
					"account": cwip_account,
					"credit_in_account_currency": asset_category_data["gross_purchase_amount"]
				}

		# Get the fixed account and set up the debit entry
		fixed_account = frappe.db.get_value(
			"Asset Category Account",
			{"parent": frappe.db.get_value("Parent Asset", self.parent_asset, "asset_category"),
			"company_name": self.company},
			"fixed_asset_account"
		)

		total_debit_in_account_currency = sum(
			component["credit_in_account_currency"] for component in components.values()
		)

		# Add debit entry to components
		components[fixed_account] = {
			"account": fixed_account,
			"debit_in_account_currency": total_debit_in_account_currency,
			"against": ', '.join(components.keys())
		}

		# Generate and save GL entries
		for component in components.values():
			debit = component.get("debit_in_account_currency", 0)
			credit = component.get("credit_in_account_currency", 0)

			# Prepare GL entry data
			gl_data = {
				'doctype': 'GL Entry',
				"posting_date": posting_date,
				'account': component["account"],
				'against': component.get("against", fixed_account),
				"voucher_type": self.doctype,
				"voucher_subtype": self.doctype,
				"voucher_no": self.name,
				"fiscal_year": current_fiscal_year,
				"company": self.company,
				'debit': debit,
				'credit': credit,
				'debit_in_account_currency': debit,
				'credit_in_account_currency': credit,
				"debit_in_transaction_currency": debit,
				"credit_in_transaction_currency": credit,
			}

			# Adjust for canceled entries
			if cancelled:
				gl_data.update({
					'debit': credit,
					'credit': debit,
					'debit_in_account_currency': credit,
					'credit_in_account_currency': debit,
					"debit_in_transaction_currency": credit,
					"credit_in_transaction_currency": debit,
					"is_cancelled": 1,
				})

			# Create and save GL Entry
			doc = frappe.get_doc(gl_data)
			doc.save()

		return doc.name


	def update_asset_is_capitalized(self, is_capitalized):
		if self.component_asset:
			for asset in self.component_asset:
				frappe.db.set_value("Asset", asset.asset, "is_capitalized", is_capitalized)


@frappe.whitelist()
def fetch_asset(parent_asset):
    asset_list = frappe.db.get_all(
        "Asset",
        filters={"parent_asset":parent_asset,"is_capitalized": 0},
        fields=["name", "asset_name", "gross_purchase_amount"]
    )
    return asset_list


# @frappe.whitelist()
# def parent_asset_filters(doctype, txt, searchfield, start, page_len, filters):
#     asset_component_list = frappe.db.sql(
# 			"""
# 				SELECT a.parent_asset
# 				FROM `tabAsset` as a
# 				WHERE a.is_capitalized = 0
# 					AND a.parent_asset IS NOT NULL
# 					AND a.name NOT IN (SELECT ca.asset
# 									FROM `tabComponent Asset` as ca
# 									JOIN `tabAsset Component Capitalization` as acc ON acc.name = ca.parent
# 									WHERE acc.docstatus != 2)

# 				GROUP BY a.parent_asset
# 			"""
#         )
#     return asset_component_list

@frappe.whitelist()
def parent_asset_filters(doctype, txt, searchfield, start, page_len, filters):
    Asset = DocType("Asset")
    ComponentAsset = DocType("Component Asset")
    AssetComponentCapitalization = DocType("Asset Component Capitalization")

    excluded_assets = (
        frappe.qb.from_(ComponentAsset)
        .join(AssetComponentCapitalization)
        .on(AssetComponentCapitalization.name == ComponentAsset.parent)
        .select(ComponentAsset.asset)
        .where(AssetComponentCapitalization.docstatus != 2)
    )

    query = (
        frappe.qb.from_(Asset)
        .select(Asset.parent_asset)
        .where(
            (Asset.is_capitalized == 0)
            & (Asset.parent_asset.isnotnull())
            & (Asset.name.notin(excluded_assets))
        )
        .groupby(Asset.parent_asset)
    )

    return query.run()
