{
    'name': 'QuickBooks canada Online Odoo Connector',
    'version': '1.5',
    'category': 'Accounting',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'depends': ['hr', 'sale_management', 'purchase', 'account', 'stock', 'sale_purchase', 'sale_stock', 'stock_sms', 'account_check_printing'],
    'external_dependencies': {
        'python': ['xmltodict', 'requests'],
    },
    'summary': 'Odoo QuickBooks Bundle Odoo Quickbooks Desktop Connector Odoo Quickbooks integration QuickBooks Credit Memo Quickbooks reports odoo quickbooks connect accounting app accounting reports QuickBook Online connector online odoo accounting app QuickBook canada QuickBooks canada',
    'description': """
QuickBook Connector
====================
Odoo Quickbooks online connector is used to export invoices/bill from Odoo get them paid in QBO and import paid invoices/bills in Odoo.

This module has following features
----------------------------------
    1] Import QBO customer into Odoo
    2] Import QBO supplier from QBO into Odoo
    3] Import QBO account into Odoo
    4] Export account into QBO
    5] Import QBO account tax into Odoo
    6] Export account tax into QBO
    7] Export tax agency into QBO
    8] Import QBO product category into Odoo
    9] Import QBO product into Odoo
    10] Import QBO payment method into Odoo
    11] Import QBO payment term into Odoo
    12] Export customer invoice into QBO
    13] Export supplier bill into QBO
    14] Import QBO customer payment into Odoo
    15] Import QBO supplier bill into Odoo
<keywords>
QuickBooks Online Odoo Connector
quickbooks connector 
odoo quickbooks
quickbooks online connector
quickbooks online odoo 
accounting app
""",
    'data': [
        'data/qbo_data.xml',
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/export_partner.xml',
        'views/account_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/details.xml',
        'views/export_sale_order.xml',
        'views/export_purchase_order.xml',
        'views/export_dept.xml',
        'views/export_emp.xml',
        'views/res_config_settings.xml',
        'views/refresh_token_cron.xml',
        'views/import_journal_entry_cron.xml',
        'wizard/connection_successfull_view.xml',
        # 'views/import_customer_cron.xml',
        # 'views/import_sales_order_cron.xml',
        'views/import_cron.xml',
        'views/export_cron.xml',
        # 'views/qbo_logger.xml',
        # 'views/automated_authentication.xml',
    ],
    'images': ['static/description/quickbook-connector_canada.gif'],
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=quickbook-connector',
    'currency': 'USD',
    'license': 'OPL-1',
    'price': 250,
    'installable': True,
    'auto_install': False,
    
    "cloc_exclude": [
    "lib/common.py", # exclude a single file
    "data/*.xml",    # exclude all XML files in a specific folder
    "example/**/*",  # exclude all files in a folder hierarchy recursively
    "**/*.scss",     # exclude all scss file from the module
],
    
    
    
}
