(() => {
  // ../assets/assets/public/js/help_links.js
  frappe.provide("frappe.help.help_links");
  var docsUrl = "https://erpnext.com/docs/";
  frappe.help.help_links["List/Asset"] = [
    {
      label: "Managing Fixed Assets",
      url: docsUrl + "user/manual/en/asset"
    }
  ];
  frappe.help.help_links["List/Asset Category"] = [
    {
      label: "Asset Category",
      url: docsUrl + "user/manual/en/asset-category"
    }
  ];
  frappe.help.help_links["List/Item"].push({
    label: "Managing Fixed Assets",
    url: docsUrl + "user/manual/en/asset"
  });
  frappe.help.help_links["Form/Item"].push({
    label: "Managing Fixed Assets",
    url: docsUrl + "user/manual/en/asset"
  });
})();
//# sourceMappingURL=asset.bundle.LOYXD6M4.js.map
