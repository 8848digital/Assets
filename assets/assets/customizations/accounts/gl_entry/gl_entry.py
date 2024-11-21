from assets.assets.customizations.accounts.gl_entry.doc_events import validate_cwip_accounts

def validate(doc, method = None):
    validate_cwip_accounts(doc)