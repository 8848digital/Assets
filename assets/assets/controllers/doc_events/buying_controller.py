import frappe
from frappe.utils import flt, cint
from frappe import _
from erpnext.erpnext.controllers.buying_controller import get_asset_items


def validate(doc, method=None):
    validate_asset_return(doc)


def on_submit(doc, method=None):
    if doc.doctype in ["Purchase Receipt", "Purchase Invoice"]:
        process_fixed_asset(doc)


def on_cancel(doc, method=None):
    if doc.doctype in ["Purchase Receipt", "Purchase Invoice"]:
        field = (
            "purchase_invoice"
            if doc.doctype == "Purchase Invoice"
            else "purchase_receipt"
        )
        delete_linked_asset(doc)
        update_fixed_asset(doc, field, delete_asset=True)


def validate_asset_return(doc):
    if doc.doctype not in ["Purchase Receipt", "Purchase Invoice"] or not doc.is_return:
        return

    purchase_doc_field = (
        "purchase_receipt" if doc.doctype == "Purchase Receipt" else "purchase_invoice"
    )
    not_cancelled_asset = []
    if doc.return_against:
        not_cancelled_asset = [
            d.name
            for d in frappe.db.get_all(
                "Asset", {purchase_doc_field: doc.return_against, "docstatus": 1}
            )
        ]

    if doc.is_return and len(not_cancelled_asset):
        frappe.throw(
            _(
                "{} has submitted assets linked to it. You need to cancel the assets to create purchase return."
            ).format(doc.return_against),
            title=_("Not Allowed"),
        )


def auto_make_assets(doc, asset_items):
    items_data = get_asset_item_details(asset_items)
    messages = []

    for d in doc.items:
        if d.is_fixed_asset:
            item_data = items_data.get(d.item_code)

            if item_data.get("auto_create_assets"):
                # If asset has to be auto created
                # Check for asset naming series
                if item_data.get("asset_naming_series"):
                    created_assets = []
                    if item_data.get("is_grouped_asset"):
                        asset = make_asset(doc, d, is_grouped_asset=True)
                        created_assets.append(asset)
                    else:
                        for _qty in range(cint(d.qty)):
                            asset = make_asset(doc, d)
                            created_assets.append(asset)

                    if len(created_assets) > 5:
                        # dont show asset form links if more than 5 assets are created
                        messages.append(
                            _("{} Assets created for {}").format(
                                len(created_assets), frappe.bold(d.item_code)
                            )
                        )
                    else:
                        assets_link = list(
                            map(
                                lambda d: frappe.utils.get_link_to_form("Asset", d),
                                created_assets,
                            )
                        )
                        assets_link = frappe.bold(",".join(assets_link))

                        is_plural = "s" if len(created_assets) != 1 else ""
                        messages.append(
                            _("Asset{} {assets_link} created for {}").format(
                                is_plural,
                                frappe.bold(d.item_code),
                                assets_link=assets_link,
                            )
                        )
                else:
                    frappe.throw(
                        _(
                            "Row {}: Asset Naming Series is mandatory for the auto creation for item {}"
                        ).format(d.idx, frappe.bold(d.item_code))
                    )
            else:
                messages.append(
                    _(
                        "Assets not created for {0}. You will have to create asset manually."
                    ).format(frappe.bold(d.item_code))
                )

    for message in messages:
        frappe.msgprint(message, title="Success", indicator="green")


def process_fixed_asset(doc):
    if doc.doctype == "Purchase Invoice" and not doc.update_stock:
        return

    asset_items = get_asset_items(doc)
    if asset_items:
        auto_make_assets(doc, asset_items)


def make_asset(doc, row, is_grouped_asset=False):
    if not row.asset_location:
        frappe.throw(
            _("Row {0}: Enter location for the asset item {1}").format(
                row.idx, row.item_code
            )
        )

    item_data = frappe.get_cached_value(
        "Item", row.item_code, ["asset_naming_series", "asset_category"], as_dict=1
    )
    asset_quantity = row.qty if is_grouped_asset else 1
    purchase_amount = flt(row.valuation_rate) * asset_quantity

    asset = frappe.get_doc(
        {
            "doctype": "Asset",
            "item_code": row.item_code,
            "asset_name": row.item_name,
            "naming_series": item_data.get("asset_naming_series") or "AST",
            "asset_category": item_data.get("asset_category"),
            "location": row.asset_location,
            "company": doc.company,
            "supplier": doc.supplier,
            "purchase_date": doc.posting_date,
            "calculate_depreciation": 0,
            "purchase_amount": purchase_amount,
            "gross_purchase_amount": purchase_amount,
            "asset_quantity": asset_quantity,
            "purchase_receipt": doc.name if doc.doctype == "Purchase Receipt" else None,
            "purchase_invoice": doc.name if doc.doctype == "Purchase Invoice" else None,
            "cost_center": row.cost_center,
        }
    )
    fields = frappe.get_list("Accounting Dimension", pluck="fieldname")
    for field in fields:
        if field != "location":
            if hasattr(doc, field):
                setattr(asset, field, getattr(doc, field))

    asset.flags.ignore_validate = True
    asset.flags.ignore_mandatory = True
    asset.set_missing_values()
    asset.db_insert()

    return asset.name


def update_fixed_asset(doc, field, delete_asset=False):
    for d in doc.get("items"):
        if d.is_fixed_asset:
            is_auto_create_enabled = frappe.db.get_value(
                "Item", d.item_code, "auto_create_assets"
            )
            assets = frappe.db.get_all(
                "Asset", filters={field: doc.name, "item_code": d.item_code}
            )

            for asset in assets:
                asset = frappe.get_doc("Asset", asset.name)
                if delete_asset and is_auto_create_enabled:
                    # need to delete movements to delete assets otherwise throws link exists error
                    movements = frappe.db.sql(
                        """SELECT asm.name
						FROM `tabAsset Movement` asm, `tabAsset Movement Item` asm_item
						WHERE asm_item.parent=asm.name and asm_item.asset=%s""",
                        asset.name,
                        as_dict=1,
                    )
                    for movement in movements:
                        frappe.delete_doc("Asset Movement", movement.name, force=1)
                    frappe.delete_doc("Asset", asset.name, force=1)
                    continue

                if doc.docstatus == 2:
                    if asset.docstatus == 2:
                        continue
                    if asset.docstatus == 0:
                        asset.set(field, None)
                        asset.supplier = None
                    if asset.docstatus == 1 and delete_asset:
                        frappe.throw(
                            _(
                                "Cannot cancel this document as it is linked with submitted asset {0}. Please cancel it to continue."
                            ).format(frappe.utils.get_link_to_form("Asset", asset.name))
                        )

                asset.flags.ignore_validate_update_after_submit = True
                asset.flags.ignore_mandatory = True
                if asset.docstatus == 0:
                    asset.flags.ignore_validate = True

                asset.save()


def delete_linked_asset(doc):
    if doc.doctype == "Purchase Invoice" and not doc.get("update_stock"):
        return

    asset_movement = frappe.db.get_value(
        "Asset Movement", {"reference_name": doc.name}, "name"
    )
    frappe.delete_doc("Asset Movement", asset_movement, force=1)


def get_asset_item_details(asset_items):
    asset_items_data = {}
    for d in frappe.get_all(
        "Item",
        fields=[
            "name",
            "auto_create_assets",
            "asset_naming_series",
            "is_grouped_asset",
        ],
        filters={"name": ("in", asset_items)},
    ):
        asset_items_data.setdefault(d.name, d)

    return asset_items_data
