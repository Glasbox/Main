# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def write(self, vals):
        """
        Recomputes dates of tasks that depend on these calendars
        """
        res = super(ResourceCalendar, self).write(vals)
        if vals.get('attendance_ids') or vals.get('global_leave_ids'):
            companies = self.env['res.company'].sudo().search([('resource_calendar_id', 'in', self.ids)])
            tasks = self.env['project.task'].search(
                ['|', ('company_id', '=', False), ('company_id', 'in', companies.ids)])

            # 1. Check if the start date of the first tasks is on a holiday. If so, recompute it.
            first_tasks = tasks.filtered(lambda t: t.first_task)
            for task in first_tasks:
                holidays = task.get_holidays(task.date_start)
                if task.date_start and task.date_start.date() in holidays:
                    task.write({'date_start': task.get_forward_next_date(task.date_start, 1)})

            # 2. Check if the latest start date of the milestone tasks (scheduling mode = Must Start On) is on a holiday. If so, recompute it.
            milestone_tasks = tasks.filtered(lambda t: t.milestone)
            for task in milestone_tasks:
                holidays = task.get_holidays(task.l_start_date)
                if task.l_start_date and task.l_start_date.date() in holidays:
                    task.write({'l_start_date': task.get_forward_next_date(task.l_start_date, 1)})

            # 3. Check if the latest end date of the milestone tasks (scheduling mode = Must End On) is on a holiday. If so, recompute it.
            for task in milestone_tasks:
                holidays = task.get_holidays(task.l_start_date)
                if task.l_end_date and task.l_end_date.date() in holidays:
                    task.write({'l_end_date': task.get_forward_l_end_date(task.l_start_date)})

            tasks._compute_holiday_days()
        return res
