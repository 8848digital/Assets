import frappe

def execute():
    # nosemgrep
    frappe.db.sql(
        """
        UPDATE "tabAsset Capitalization Stock Item" ACSI
        SET purchase_receipt_item = PRI.name
        FROM "tabAsset Capitalization" AC,
             "tabPurchase Receipt Item" PRI
        WHERE ACSI.parent = AC.name
          AND PRI.item_code = ACSI.item_code
          AND PRI.wip_composite_asset = AC.target_asset
          AND ACSI.purchase_receipt_item IS NULL
          AND AC.docstatus = 1
        """
    )