import frappe

def execute():
    table_schema = frappe.db.sql("""
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type
        FROM
            information_schema.columns
        WHERE
            table_schema = 'public' AND data_type = 'json'
        ORDER BY
            table_name, ordinal_position;
    """, as_dict=True)

    for row in table_schema:
        table_name = row['table_name']
        column_name = row['column_name']
        
        frappe.db.sql(f"""
            ALTER TABLE "{table_name}"
            ALTER COLUMN "{column_name}" TYPE json
            USING "{column_name}"::json;
        """)
        frappe.db.commit()