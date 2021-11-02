{
    'name': "Project GlasBox",

    'summary': """
        This module integrates project tasks with the interactive HTML5 Gantt chart.""",

    'description': """
        Task: 2466433
        Custom fields calculation and 'Gantt Chart' customization.
    """,
    "author": "Odoo Inc",
    "website": "http://www.odoo.com",
    "category": "Custom Development",
    "version": "1.0",
    'depends': [
        'base',
        'project',
        'hr',
        'project_enterprise',
        'web_gantt',
    ],
    'data': [
        'security/task_security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/task_views.xml',
        'views/assets.xml',
    ],
    'qweb': [
        "static/src/xml/gantt_view.xml",
    ],
}
