# -*- coding: utf-8 -*-
{
    "name": "Project GlasBox",
    "summary": """
        This module integrates project tasks with the interactive HTML5 Gantt chart.""",
    "description": """
        Task: 2466433
        Custom fields calculation and 'Gantt Chart' customization.
    """,
    "author": "Odoo Inc",
    "website": "http://www.odoo.com",
    "category": "Custom Development",
    "version": "1.0.1",
    "license": "OEEL-1",
    "depends": [
        "hr",
        "project_enterprise",
        "web_gantt",
    ],
    "data": [
        "security/task_security.xml",
        "security/ir.model.access.csv",
        "data/mail_template_data.xml",
        "views/task_views.xml",
    ],
    "qweb": [
        "static/src/xml/gantt_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "project_glasbox/static/src/css/task.css",
            "project_glasbox/static/src/js/gantt_model.js",
            "project_glasbox/static/src/js/gantt_view.js",
        ]
    },
}
