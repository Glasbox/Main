# -*- coding: utf-8 -*-
{
    'name': "GlasBox: Accounting budget calculated field",

    'summary': """
        This feature allows the user to keep track of the actual income and expenses for a project. 
        The theoretical amount and percentage do not get affected over time. Hence the period field is not relevant at all.""",

    'description': """
        Task ID: 2528354
        1) Glasbox will set up an analytic account for a project and use the analytic account for vendor bills and invoices associated with the project. 
        1.5) Glasbox will manually add the budget number (planned amount) for each project to the budgetary positions.
        2) The budget overview for the project will show the planned amount and the practical amount as usual but instead of the theoretical amount and the percentage, it will show the remaining available budget, and the percentage of the “used” budget.
    """,

    'author': "Odoo Inc.",
    'website': "http://www.odoo.com",
    'category': 'Customizations',
    'license': 'OEEL-1',
    'version': '1.0.2',
    'depends': [
        'account_budget', 
        'purchase', 
        'sale_management', 
        'account_accountant',
         'project'
         ],
    'data': [
        'views/sale_views.xml',
        'views/purchase_views.xml',
        'views/crossovered_budget_views.xml',
    ],
}
