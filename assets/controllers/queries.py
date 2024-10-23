import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_receipts(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select pr.name
		from `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pritem
		where pr.docstatus = 1 and pritem.parent = pr.name
		and pr.name like {txt}""".format(txt=frappe.db.escape(f"%{txt}%"))

	if filters and filters.get("item_code"):
		query += " and pritem.item_code = {item_code}".format(
			item_code=frappe.db.escape(filters.get("item_code"))
		)

	if filters and filters.get("company"):
		query += " and pr.company = {company}".format(
			company=frappe.db.escape(filters.get("company"))
		)

	return frappe.db.sql(query, filters)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_purchase_invoices(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select pi.name
		from `tabPurchase Invoice` pi, `tabPurchase Invoice Item` piitem
		where pi.docstatus = 1 and piitem.parent = pi.name
		and pi.name like {txt}""".format(txt=frappe.db.escape(f"%{txt}%"))

	if filters and filters.get("item_code"):
		query += " and piitem.item_code = {item_code}".format(
			item_code=frappe.db.escape(filters.get("item_code"))
		)

	if filters and filters.get("company"):
		query += " and pi.company = {company}".format(
			company = frappe.db.escape(filters.get("company"))
		)
		
	if filters and filters.get("update_stock"):
		query += " and pi.update_stock = {update_stock}".format(
			update_stock=filters.get("update_stock")
		)

	return frappe.db.sql(query, filters)