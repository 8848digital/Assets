import frappe
from frappe.boot import DocType


def execute():
	# nosemgrep
    ACSI = DocType('Asset Capitalization Stock Item')
    AC = DocType('Asset Capitalization')
    PRI = DocType('Purchase Receipt Item')

    # Construct the update query
    query = (
        frappe.qb.update(ACSI)
        .set(ACSI.purchase_receipt_item, PRI.name)
        .from_(AC)
        .join(PRI)
        .on(
            (ACSI.parent == AC.name) &
            (PRI.item_code == ACSI.item_code) &
            (PRI.wip_composite_asset == AC.target_asset) &
            (ACSI.purchase_receipt_item.isnull()) &
            (AC.docstatus == 1)
        )
    )

    # Execute the query
    query.run()