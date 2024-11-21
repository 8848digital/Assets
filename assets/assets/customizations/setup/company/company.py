from assets.assets.customizations.setup.company.doc_events import set_default_accounts, create_default_cost_center

def on_update(doc, method = None):
    create_default_cost_center(doc)
    set_default_accounts(doc)