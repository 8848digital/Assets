import frappe


def execute():
    # nosemgrep
    ACSI = frappe.qb.DocType('Asset Capitalization Stock Item')
    AC = frappe.qb.DocType('Asset Capitalization')
    PRI = frappe.qb.DocType('Purchase Receipt Item')

    query = (
        frappe.qb.update(ACSI)
        .set(ACSI.purchase_receipt_item, PRI.name)
        .where(
            (ACSI.parent == AC.name) &
            (PRI.item_code == ACSI.item_code) &
            (PRI.wip_composite_asset == AC.target_asset) &
            (ACSI.purchase_receipt_item.isnull()) &
            (AC.docstatus == 1)
        )
    )

    query.run()