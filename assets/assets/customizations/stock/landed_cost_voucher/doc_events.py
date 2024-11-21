import frappe
from frappe import _

def update_landed_cost(self):
    for d in self.get("purchase_receipts"):
        doc = frappe.get_doc(d.receipt_document_type, d.receipt_document)
        # check if there are {qty} assets created and linked to this receipt document
        if self.docstatus != 2:
            validate_asset_qty_and_status(self, d.receipt_document_type, doc)

def validate_asset_qty_and_status(self, receipt_document_type, receipt_document):
    for item in self.get("items"):
        if item.is_fixed_asset:
            receipt_document_type = (
                "purchase_invoice"
                if item.receipt_document_type == "Purchase Invoice"
                else "purchase_receipt"
            )
            docs = frappe.db.get_all(
                "Asset",
                filters={receipt_document_type: item.receipt_document, "item_code": item.item_code},
                fields=["name", "docstatus"],
            )
            if not docs or len(docs) < item.qty:
                frappe.throw(
                    _(
                        "There are only {0} asset created or linked to {1}. Please create or link {2} Assets with respective document."
                    ).format(len(docs), item.receipt_document, item.qty)
                )
            if docs:
                for d in docs:
                    if d.docstatus == 1:
                        frappe.throw(
                            _(
                                "{0} <b>{1}</b> has submitted Assets. Remove Item <b>{2}</b> from table to continue."
                            ).format(item.receipt_document_type, item.receipt_document, item.item_code)
                        )