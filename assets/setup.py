from assets.install import (
    create_custom_fields_for_assets as create_custom_fields,
	create_property_setter,
	delete_property_setters,
	delete_custom_fields
)


def after_install():
	create_custom_fields()
	create_property_setter()

def before_uninstall():
	delete_property_setters()
	delete_custom_fields()