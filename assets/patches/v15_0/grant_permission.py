import frappe

def execute():
    frappe.db.sql(f"""
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {frappe.conf.db_name};
    """, as_dict=True)
    frappe.db.commit()