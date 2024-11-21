from assets.assets.customizations.stock.landed_cost_voucher.doc_events import update_landed_cost

def on_submit(doc, method):
    update_landed_cost(doc)

def on_cancel(doc, method):
    update_landed_cost(doc)