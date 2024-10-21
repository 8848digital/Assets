app_name = "assets"
app_title = "Assets"
app_publisher = "8848 Digital LLP"
app_description = "Assets Management"
app_email = "atul@8848digital.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "assets",
# 		"logo": "/assets/assets/logo.png",
# 		"title": "Assets",
# 		"route": "/assets",
# 		"has_permission": "assets.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/assets/css/assets.css"
# app_include_js = "/assets/assets/js/assets.js"

# include js, css files in header of web template
# web_include_css = "/assets/assets/css/assets.css"
# web_include_js = "/assets/assets/js/assets.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "assets/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "assets/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "assets.utils.jinja_methods",
# 	"filters": "assets.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "assets.install.before_install"
# after_install = "assets.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "assets.uninstall.before_uninstall"
# after_uninstall = "assets.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "assets.utils.before_app_install"
# after_app_install = "assets.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "assets.utils.before_app_uninstall"
# after_app_uninstall = "assets.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "assets.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

period_closing_doctypes = [
	"Asset",
	"Asset Capitalization",
	"Asset Repair",
]

accounting_dimension_doctypes = [
	"Asset",
	"Asset Value Adjustment",
	"Asset Repair",
	"Asset Capitalization",
]

doc_events = {
	tuple(period_closing_doctypes): {
		"validate": "erpnext.accounts.doctype.accounting_period.accounting_period.validate_accounting_period_on_doc_save",
	},
    "Journal Entry": {
		"on_submit": "assets.assets.customizations.journal_entry.journal_entry.on_submit",
		"on_cancel": "assets.assets.customizations.journal_entry.journal_entry.on_cancel",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"assets.assets.doctype.asset.asset.update_maintenance_status",
		"assets.assets.doctype.asset.asset.make_post_gl_entry",
		"assets.assets.doctype.asset_maintenance_log.asset_maintenance_log.update_asset_maintenance_log_status",
	],
	"daily_long": [
		"assets.assets.doctype.asset.depreciation.post_depreciation_entries",
	],
	}

# ERPNext doctypes for Global Search
global_search_doctypes = {
	"Default": [
		{"doctype": "Asset", "index": 28},
],
}
# Testing
# -------

# before_tests = "assets.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "assets.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "assets.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["assets.utils.before_request"]
# after_request = ["assets.utils.after_request"]

# Job Events
# ----------
# before_job = ["assets.utils.before_job"]
# after_job = ["assets.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"assets.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

