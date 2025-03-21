# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import unittest

import frappe

test_records = frappe.get_test_records("Location")


class TestLocation(unittest.TestCase):

	# TC_FA_088
	def test_create_location_TC_FA_088(self):
		if not frappe.db.exists("Location", "Test_newyork"):
			location = frappe.get_doc({
				"doctype":"Location",
				"location_name":"Test_newyork",	
			}).insert()
	
	# TC_FA_089
	def test_create_group_location_TC_FA_089(self):
		if not frappe.db.exists("Location", "Test_newyork1"):
			grouped_location = frappe.get_doc({
				"doctype":"Location",
				"location_name":"Test_newyork1",	
				"is_group":1
			}).insert()
			location = frappe.get_doc({
				"doctype":"Location",
				"location_name":"Test_parent",	
				"parent_location":grouped_location
			}).insert()

	# TC_FA_090
	def test_create_group_location_TC_FA_090(self):
		if not frappe.db.exists("Location", "Test_group_location"):
			grouped_location = frappe.get_doc({
				"doctype":"Location",
				"location_name":"Test_group_location",	
				"is_group":1
			}).insert()
			location = frappe.get_doc({
				"doctype":"Location",
				"location_name":"Test_child",	
				"parent_location":grouped_location
			}).insert()
			
	def runTest(self):
		locations = ["Basil Farm", "Division 1", "Field 1", "Block 1"]
		area = 0
		formatted_locations = []

		for location in locations:
			doc = frappe.get_doc("Location", location)
			doc.save()
			area += doc.area
			temp = json.loads(doc.location)
			temp["features"][0]["properties"]["child_feature"] = True
			temp["features"][0]["properties"]["feature_of"] = location
			formatted_locations.extend(temp["features"])

		test_location = frappe.get_doc("Location", "Test Location Area")
		test_location.save()

		test_location_features = json.loads(test_location.get("location"))["features"]
		ordered_test_location_features = sorted(
			test_location_features, key=lambda x: x["properties"]["feature_of"]
		)
		ordered_formatted_locations = sorted(
			formatted_locations, key=lambda x: x["properties"]["feature_of"]
		)

		self.assertEqual(ordered_formatted_locations, ordered_test_location_features)
		self.assertEqual(area, test_location.get("area"))
