# -*- coding: utf-8 -*-
from datetime import timedelta, datetime, date
import pytz
from pytz import timezone, UTC
from odoo.exceptions import ValidationError, UserError
from odoo import models, fields, api, _

class Company(models.Model):
    _inherit = "res.company"

    def write(self, vals):
        res = super(Company, self).write(vals)
        if vals.get('resource_calendar_id'):
            tasks = self.env['project.task'].search(['|', ('company_id', '=', False), ('company_id', '=', self.id)])

            # Check if the start date of the first tasks is on a holiday. If so, recompute it.
            first_tasks = tasks.filtered(lambda t: t.first_task)
            for task in first_tasks:
                holidays = task.get_holidays(task.date_start)
                if task.date_start and task.date_start.date() in holidays:
                    task.write({'date_start': task.get_next_business_day(task.date_start)})
            tasks._compute_holiday_days()
        return res


# class Project(models.Model):
#     _inherit = "project.project"

#     @api.returns('self', lambda value: value.id)
#     def copy(self, default=None):
#         """
#         Logic for copying all the dependency tasks with new updated 'project_id'
#         while duplicating whole the project.
#         """
#         # search old list self.task_ids = old_tasks
#         old_tasks = self.task_ids
#         # then super call
#         project = super(Project, self).copy(default)
#         #new tasks
#         new_tasks = project.mapped('task_ids')
#         # for task in new_tasks:

#         for task in new_tasks:
#             old = old_tasks.filtered(lambda x: x.name == task.name) # should only return one task
#             dependent_tasks = []
#             # logic for setting current project on dependency_task's project_id
# #            for d_task in old.dependency_task_ids:
#             for d_task in old.depend_on_ids:
# #               dependent_tasks = new_tasks.filtered(lambda x: x.name == d_task.task_id.name).ids 
#                 dependent_tasks = new_tasks.filtered(lambda x: x.name == d_task.name).ids
#                 # task.write({
#                 #     'dependency_task_ids': [(0, 0, {'task_id': task_id}) for task_id in dependent_tasks]
#                 # })
#                 task.write({'depend_on_ids': list(dependent_tasks)})
#         return project

# class DependingTasks(models.Model):
#     _name = "project.depending.tasks"
#     _description = "Tasks Dependency (m2m)"

#     task_id = fields.Many2one('project.task', store=True, index=True)
#     project_id = fields.Many2one('project.project', string='Project', related='task_id.project_id', store=True, index=True)
#     depending_task_id = fields.Many2one('project.task', string='Task', store=True, index=True)
#     relation_type = fields.Char('Relation', default="Finish To Start", store=True, index=True)


class TaskDependency(models.Model):
    _inherit = "project.task"

    planned_duration = fields.Integer(string='Duration', default=1, copy=True)
    buffer_time = fields.Integer(string='Buffer Time', copy=True)
    task_delay = fields.Integer(string='Task Delay', compute='_compute_delay', store=True, copy=True)
    accumulated_delay = fields.Integer(string='Accumulated Delay', compute='_compute_accumulated_delay', store=True, copy=True, recursive=True)
    on_hold = fields.Integer(string="On Hold", store=True, copy=True)
    # dependency_task_ids = fields.One2many('project.depending.tasks', 'depending_task_id', string="Dependent Task", copy=False, store=True)
    # dependent_task_ids = fields.One2many('project.depending.tasks', 'task_id', string="Following Task", copy=False, store=True)
    date_start = fields.Datetime(string='Starting Date', compute='_compute_start_date', store=True, copy=True)
    date_end = fields.Datetime(string='Ending Date', readonly=True, compute='_compute_end_date', store=True, copy=True)
    completion_date = fields.Datetime(string='Completion Date', store=True, copy=True)
    check_end_or_comp_date = fields.Datetime(string='Checking End or Completion Date', compute='_compute_end_comp', store=True, copy=True)
    milestone = fields.Boolean(string='Mark as Milestone', default=False, store=True, copy=True)
    first_task = fields.Boolean(string='First Task', default=False, store=True, copy=True)
    l_start_date = fields.Datetime(string='Latest Start Date', compute='_compute_l_start_date', inverse='_set_l_start_date', store=True, copy=True)
    l_end_date = fields.Datetime(string='Latest End Date', compute='_compute_l_end_date', inverse='_set_l_end_date', store=True, copy=True)
    duration_mode = fields.Char(readonly=True, store=True, copy=True)
    delay_due_to_date = fields.Datetime(string="Delay Due To", copy=True)
    check_delay = fields.Boolean(string="Check Delay", compute="_compute_check_delay", store=True, copy=True)
    check_c_date = fields.Boolean(string='Check Whether the Completion Date is set or not', compute="_compute_c_date", store=True, copy=True)
    check_overdue = fields.Boolean(string='Check OverDue', compute="_check_completion_date", store=True, copy=True)
    check_milestone = fields.Boolean(string="Check Milestone", compute="_compute_milestone", store=True, copy=True)
    check_ahead_schedule = fields.Boolean(string="Check Ahead Of Schedule", compute="_compute_ahead", store=True, copy=True)
    check_hold = fields.Boolean(string="Check On Hold", compute="_check_hold", store=True, copy=True)
    scheduling_mode = fields.Selection([
        ("0", "Must Start On"),
        ("1", "Must Finish On"),
    ], string="Scheduling Mode", copy=True)
    holiday_days = fields.Boolean(compute="_compute_holiday_days")
    # CHANGE REQ - 2952592 - MARW BEGIN
    # multi_child_ids = fields.Many2many('project.task', relation="glasbox_tasks_rel", column1="parent_id",
    #     column2="child_id", string="Children", tracking=True, copy=False,
    #     domain="[('project_id', '!=', False), ('id', '!=', id)]")
    # depend_on_ids = fields.Many2many('project.task', relation="glasbox_tasks_rel", column1="child_id",
    #     column2="parent_id", string="Parent Tasks", copy=False,
    #     domain="[('project_id', '!=', False), ('id', '!=', id)]")
    parents_ids = fields.One2many('project.task', 'follower_id', string="DEPENDENT TASKs", store=True)
    follower_id = fields.Many2one('project.task', string='Follower Task', store=True, default=False )
    stage_id = fields.Many2one('project.task.type', string='Stage', compute='_compute_stage_id',
        store=True, readonly=False, ondelete='restrict', tracking=True, index=True,
        default='_get_default_stage_id', group_expand='_read_group_stage_ids',
        domain="[('project_ids', '=', project_id)]", copy=True, task_dependency_tracking=True)
    check_before_start = fields.Boolean(string='Check Completion Before Start Date', store=True, copy=True)
    task_url = fields.Char('Task URL', compute='_get_task_url', help='The full URL to access the task through the website.')

    def _get_default_stage_id(self):
        return super()._get_default_stage_id()
    
    def _compute_stage_id(self):
        super()._compute_stage_id()

    def _get_task_url(self):
        for record in self:
            record.task_url = f"https://www.odoo.com/web#id={record.id}&model=project.task&view_type=form"
    # CHANGE REQ - 2952592 - MARW END

    def update_planned_dates(self):
        for record in self.filtered(lambda task: task.date_start):
            end = record.completion_date if record.check_delay else record.date_end
            start, stop = self._calculate_planned_dates(record.date_start, end, calendar= self.env.company.resource_calendar_id)
            record.write({
                    'planned_date_begin': start,
                    'planned_date_end': stop,
                })


    @api.onchange('completion_date')
    def onchange_completion_date(self):
        """
        The Completion date is always defaulted to today's date.
        Nobody can set yesterday's or next week’s date as the completion date.
        """
        ctx = self.env.context
        offset = self.get_usertz_offset()
        for record in self:
            if ctx.get('c_date') and record.completion_date:
                # FIX ISSUE WHEN JUMPING TO NEXT DAY!!
                # get now in GMT -> convert to local time to ensure correct day -> set time to 4pm -> convert time back to GMT 
                comp_date = (datetime.now() + (timedelta(hours=offset))).replace(hour=16,minute=0,second=0) - (timedelta(hours=offset)) 
                record.completion_date = comp_date #datetime.now().replace(hour=(16),minute=0,second=0) - (timedelta(hours=offset)) 
                # record._check_date_in_holiday(record.completion_date)
    # CHANGE REQ - 2952592 - MARW BEGIN
                if record.check_before_start:
                    record.planned_duration = 1
                    record.date_start = (record.completion_date) 

#                for child in record.dependent_task_ids.depending_task_id.ids:
                for child in record.dependent_ids.ids:
                    task = self.env['project.task'].search([('id','=', child)])
                    task.write({'date_start': (self.get_next_business_day(record.completion_date.replace(hour=7, minute=0) - timedelta(hours=offset))) })
                    task.write({'date_end': (self.get_forward_next_date((record.completion_date.replace(hour=16, minute=0) - timedelta(hours=offset)), task.planned_duration - 1))})
    # CHANGE REQ - 2952592 - MARW END

    #OVERWRITE
    def write(self, vals):
        res = super().write(vals)
        for record in self:
            # Update record's dependencies latest start/end dates
            if 'l_start_date' in vals and vals['l_start_date']:
                record._l_start_date()
                record._l_end_date()
            if 'l_end_date' in vals and vals['l_end_date']:
                record._l_end_date()
            if 'completion_date' in vals and vals['completion_date']:
                record._send_mail_template()
        return res


    def _l_start_date(self):
        """
        This method gets called when the record is updated/written and updates all of its dependencies latest start dates.

        For non-milestone task, 'l_start_date' will be calculated when the milestone tasks’ Latest start/end date gets inserted.
        Use the current task calculated Latest end date - current task Duration (but not buffer time) - current task On hold (if any).
        Read-only field for non-milestone tasks.
        """
        for record in self:
#            if record.dependency_task_ids and record.l_start_date:
            if record.depend_on_ids and record.l_start_date:
#                for task in record.dependency_task_ids:
                for task in record.depend_on_ids:
                    duration = timedelta(task.task_id.planned_duration) - timedelta(task.task_id.on_hold)
                    task.task_id.write({'l_start_date': task.task_id.get_backward_next_date(task.task_id.l_end_date, duration.days)})

    def _l_end_date(self):
        """
        This method gets called when the record is updated/written and updates all of its dependencies latest end dates.

        For non-milestone task, 'l_end_date' is calculate with the next tasks’ latest start date minus one business day.
        This will be the read-only field.
        """
        for record in self:
#            if record.dependency_task_ids and record.l_start_date:
            if record.depend_on_ids and record.l_start_date:            
#                for task in record.dependency_task_ids:
                for task in record.depend_on_ids:
                    task.task_id.write({'l_end_date': task.task_id.get_previous_business_day(record.l_start_date)})


    def _compute_holiday_days(self):
        """Recompute holiday days for tasks that have a start date, an end date, and are not completed yet"""
        for record in self:
            holidays = 0
            if record.date_start and not record.completion_date:
                duration = record.planned_duration + record.on_hold + record.buffer_time
                computed_end = record.get_forward_next_date(record.date_start, duration)
                if computed_end and record.l_end_date:
                    end_date = min(computed_end, record.l_end_date)
                else:
                    end_date = computed_end or record.l_end_date
                holidays = record.get_int_holidays_between_dates(record.date_start, end_date)

            record.holiday_days = holidays


    def _send_mail_template(self):
        """
        Sends email to the assigned user of A3 task, when it's dependent tasks
        A1's completion date is set and A2's completion date is not set.
        Whenever, A2's completion date is set, mail will be automatically sent to the A3 Task's
        assigned user.
        """
        for record in self:
            template = record.env.ref('project_glasbox.task_completion_email_template_glasbox')
#            tasks = record.env['project.task'].search([('dependency_task_ids.task_id', 'in', record.ids)]) CHECK FOR ISSUES !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            tasks = record.env['project.task'].search([('depend_on_ids', 'in', record.ids)])
            tasks.message_post_with_template(template_id=template.id)

    def _convert_utc_to_calendar_tz(self, date_naive):
        """
        Converts and returns the datetime converted from standard UTC (no explicit timezone) to the calendar timezone.
        :param date_naive: Datetime with no timezone information. Corresponds to server stored datetime in UTC.
        :return: Datetime with the associated timezone that was specified in the main working calendar.
        """
        self.ensure_one()
        calendar_tz = timezone(self.get_calendar().tz)
        date_utc = UTC.localize(date_naive)
        date_user_tz = date_utc.astimezone(timezone(self.env.user.tz))
        date_cal_tz = date_user_tz.replace(tzinfo=calendar_tz)
        return date_cal_tz

    def _check_date_in_holiday(self, target_date):
        self.ensure_one()
        resource_calendar = self.get_calendar()
        day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
        holidays = self.get_holidays(target_date)
        target_date = self._convert_utc_to_calendar_tz(target_date)

        if target_date and str(target_date.weekday()) not in day_of_week:
            raise UserError(_('You can not set a date which is not in your Working days! Kindly check your Company Calendar!'))
        if target_date and target_date.date() in holidays:
            raise UserError(_('You can not set a date which is a Holiday! Kindly check your Company Calendar!'))

    def _is_business_day(self, target_date):
        """
        Returns True if the input date is not a holiday or is not a weekend.
        The target date is converted to the official calendar timezone for the comparison.
        """
        self.ensure_one()
        resource_calendar = self.get_calendar()
        day_of_week = resource_calendar.attendance_ids.mapped('dayofweek')
        holidays = self.get_holidays(target_date)
        target_date = self._convert_utc_to_calendar_tz(target_date)
        return str(target_date.weekday()) in day_of_week and target_date.date() not in holidays


    def get_calendar(self):
        return self.env.company.resource_calendar_id

    def get_global_ids(self):
        return self.get_calendar().global_leave_ids

    def dependency_count(self):
#        return len(self.dependency_task_ids.mapped('task_id'))
        return len(self.depend_on_ids)

    def get_holidays(self, start_date):
        """
        Method for getting company's holiday's according to company's calendar and only one date.
        return: List of holiday dates
        """
        for record in self:
            leaves = record.get_global_ids()
            lst_days = []
            for leave in leaves:
                date_to = record._convert_utc_to_calendar_tz(leave.date_to)
                date_from = record._convert_utc_to_calendar_tz(leave.date_from)

                leave_duration = (date_to.date() - date_from.date() + timedelta(days=1)).days
                l_days = [date_from.date() + timedelta(days=x) for x in range(leave_duration)]
                lst_days += l_days
            return lst_days

    def get_int_holidays_between_dates(self, start_date, end_date):
        """Returns an Int representing the number of holiday days between two dates according to company's calendar."""
        self.ensure_one()
        leaves = self.get_global_ids().filtered(lambda d: d.date_from.date() >= start_date.date() and
                                                          d.date_to.date() <= end_date.date())
        return len(leaves)


    def get_holidays_between_dates(self, start_date, end_date):
        """Returns an Int representing the number of business days between two dates.
        The number will be negative if end_date is earlier than start_date."""
        self.ensure_one()
        start_date_tz = self._convert_utc_to_calendar_tz(start_date)
        end_date_tz = self._convert_utc_to_calendar_tz(end_date)

        sign = 1
        if start_date_tz > end_date_tz:
            start_date, end_date = end_date, start_date  # swap the variables to start with the earliest day
            sign = -1

        duration = 0
        while start_date_tz.date() < end_date_tz.date():
            start_date_tz += timedelta(days=1)
            start_date += timedelta(days=1)
            if self._is_business_day(start_date):
                duration += 1

        return duration * sign


    def get_next_business_day(self, next_date):
        """
        Calculates and returns the following business day after a certain date accounting for weekends and holidays.
        """
        self.ensure_one()
        if next_date:
            next_date += timedelta(days=1)
            while not self._is_business_day(next_date):
                next_date += timedelta(days=1)
        return next_date

    def get_previous_business_day(self, next_date):
        """
        Calculates and returns the previous business day after a certain date accounting for weekends and holidays.
        """
        self.ensure_one()
        if next_date:
            next_date -= timedelta(days=1)
            while not self._is_business_day(next_date):
                next_date -= timedelta(days=1)
        return next_date


    def get_forward_next_date(self, next_date, duration):
        """Calculates and returns the 'end_date' according to any 'start_date' and a duration"""
        self.ensure_one()
        if next_date:
            # duration -= 1
            while duration > 0:
                next_date = self.get_next_business_day(next_date)
                duration -= 1
        return next_date

    def get_backward_next_date(self, next_date, duration):
        """Calculates and returns the 'start_date' according to any 'end_date' and a duration"""
        self.ensure_one()
        if next_date:
            duration -= 1
            while duration > 0:
                next_date = self.get_previous_business_day(next_date)
                duration -= 1
        return next_date


    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------


    @api.depends('completion_date', 'date_end')
    def _compute_end_comp(self):
        for task in self:
            if task.completion_date and task.date_end and task.completion_date > task.date_end:
                task.check_end_or_comp_date = task.completion_date
            else:
                task.check_end_or_comp_date = task.date_end

    @api.depends('completion_date')
    def _compute_c_date(self):
        for task in self:
            task.check_c_date = bool(task.completion_date)

    @api.depends('task_delay', 'check_c_date')
    def _compute_check_delay(self):
        for task in self:
            task.check_delay = task.task_delay > 0

    @api.depends('completion_date', 'l_end_date')
    def _check_completion_date(self):
        for task in self:
            task.check_overdue = bool(
                task.completion_date
                and task.l_end_date
                and task.completion_date > task.l_end_date
            )

    @api.depends('on_hold', 'check_c_date')
    def _check_hold(self):
        for task in self:
            task.check_hold = task.on_hold > 0

    @api.depends('milestone')
    def _compute_milestone(self):
        for task in self:
            task.check_milestone = bool(task.milestone)

    @api.depends('completion_date', 'date_end')
    def _compute_ahead(self):
        for task in self:
            if task.completion_date and task.date_end and task.completion_date < task.date_end:
                task.check_ahead_schedule = True
                # CHANGE REQ 2952592 -MARW START
                #task.planned_duration = (task.completion_date - task.date_start).days
                task.check_before_start = task.completion_date < task.date_start
            else:
                task.check_ahead_schedule = False
                task.check_before_start = False
                # CHANGE REQ 2952592 -MARW END
    @api.depends('completion_date', 'date_end')
    def _compute_delay(self):
        """
        Method For calculating the 'task_delay' based on the 'completion_date' and 'date_end'.
        task_delay = completion_date - date_end
        Here, you will get 'negative delay' if task finished earlier than planned.
        """
        for record in self:
            if record.date_end and record.completion_date:
                # print(record.date_end.date(),record.completion_date.date(),'lmo\n\n\n')
                # record.task_delay = (record.completion_date.date() - record.date_end.date()).days
                if record.completion_date > record.date_end:
                    record.task_delay = record.get_holidays_between_dates(record.date_end, record.completion_date)
                    # record.write({'planned_date_end': record.completion_date}) 
                    record.planned_date_end = record.completion_date
                else:
                    task_delay = record.get_holidays_between_dates(record.completion_date, record.date_end)
                    record.task_delay = task_delay * -1
            if not record.completion_date:
                record.task_delay = 0

#   @api.depends('dependency_task_ids.task_id.completion_date', 'dependency_task_ids.task_id.accumulated_delay','task_delay')
    @api.depends('depend_on_ids.completion_date', 'depend_on_ids.accumulated_delay', 'task_delay')
    def _compute_accumulated_delay(self):
        for record in self:
            if record.first_task or record.dependency_count() == 0:
                record.accumulated_delay = record.task_delay
            else:
                # Only fill in accumulated delay when all previous dependent tasks have a completion date.
#                incomplete_tasks = record.dependency_task_ids.mapped('task_id').filtered(lambda task: not task.completion_date)  CHEKKKKKKK FOR ISSUESSS !!!!!!!!!!!!!!!!!!
                incomplete_tasks = record.depend_on_ids.filtered(lambda task: not task.completion_date)
                # if incomplete_tasks:
                #     record.accumulated_delay = 0
                # else:
                    # If current task is not 'first_task' and it has dependent tasks
                    # then set 'accumulated_delay' = dependent tasks' max 'accumulated_delay' + current task's task_delay
#                delay_lst = record.dependency_task_ids.task_id.mapped('accumulated_delay')
                delay_lst = record.depend_on_ids.mapped('accumulated_delay')
                record.accumulated_delay = max(delay_lst) + record.task_delay


#    @api.depends('dependency_task_ids.task_id.completion_date', 'dependency_task_ids.task_id.date_end')
    @api.depends('depend_on_ids', 'depend_on_ids.completion_date', 'depend_on_ids.date_end')
    def _compute_start_date(self):
        """
        Computes the start date of a task based on its dependencies. The start date will be one day after the date when the last dependency task finishes.
        If a dependency task has a completion date, then completion_date is the task's finish date.
        If a dependency task does not have a completion date but has an end date set, then date_end is the task's finish date.
        """
        offset = self.get_usertz_offset()
        for record in self:
#            if not record.first_task and record.dependency_task_ids:
            if not record.first_task and record.depend_on_ids:
                new_start_date = None
#                completion_dates = record.dependency_task_ids.filtered('task_id.completion_date').mapped('task_id.completion_date')  CHECKKKKKKKK !!!!!!!!!!!!!!!!!!!!11
                completion_dates = record.depend_on_ids.filtered('completion_date').mapped('completion_date')
#                end_dates = record.dependency_task_ids.filtered(lambda r: not r.task_id.completion_date and r.task_id.date_end).mapped('task_id.date_end')
                end_dates = record.depend_on_ids.filtered(lambda r: not r.completion_date and r.date_end).mapped('date_end')
                finish_dates = completion_dates + end_dates
                if finish_dates:
                    new_start_date = record.get_next_business_day(max(finish_dates))
                    # Only update date_start when the value changes to avoid triggering re-computation of end_date
                    if new_start_date != record.date_start:
                        new_start = new_start_date.replace(hour=(7), minute=0,second=0,)  - (timedelta(hours=offset)) 
                        record.write({'date_start': new_start}) # always set to 7am (offset by -5)
                        #record.date_start = new_start_date


    @api.depends('planned_duration', 'buffer_time', 'on_hold', 'date_start', 'holiday_days')
    def _compute_end_date(self):
        """
        Computes the end date of a task applying forward calculation.
        date_end = date_start + planned_duration + buffer_time + on_hold
        """
        offset = self.get_usertz_offset()
        for record in self:
            if record.date_start:
                new_start = record.date_start.replace(hour=(7), minute=0,second=0,)  - (timedelta(hours=offset)) 
                record.write({'date_start': new_start}) # always set to 7am (offset by -5)
                duration = (record.planned_duration + record.on_hold + record.buffer_time) - 1
                if duration == 0:
                    record.write({'date_end': new_start + timedelta(hours=9)})
                else:
                    new_end = record.get_forward_next_date(record.date_start, duration).replace(hour=(16),minute=0,second=0) - (timedelta(hours=offset))
                    record.write({'date_end': new_end})
                record.planned_date_begin = record.date_start
                if record.check_delay is False:
                    record.planned_date_end = record.date_end
                    record.update_planned_dates()


    @api.depends('l_end_date', 'planned_duration', 'milestone', 'scheduling_mode')
    def _compute_l_start_date(self):
        """
            Method for to set 'l_start_date' dynamically (applied backward calculation) according to
            'l_end_date' and 'planned_duration'

            Here, the calculation of 'l_start_date' is as follows:-
            l_start_date = l_end_date - planned_duration
        """
        for record in self:
            if record.l_end_date:
                record._check_date_in_holiday(record.l_end_date)
                record.l_start_date = record.get_backward_next_date(record.l_end_date, record.planned_duration)

    @api.depends('l_start_date', 'planned_duration', 'milestone', 'scheduling_mode')
    def _compute_l_end_date(self):
        """
            Method for to set 'l_end_date' dynamically (applied forward calculation) according to
            'l_end_date' and 'planned_duration'

            Here, the calculation of 'l_end_date' is as follows:-
            l_end_date = l_date_start + planned_duration
        """
        for record in self:
            if record.l_start_date:
                record._check_date_in_holiday(record.l_start_date)
                record.l_end_date = record.get_forward_next_date(record.l_start_date, record.planned_duration)

    def get_usertz_offset(self):
        #user_tz =timezone(self.env.context['tz'])
        user_tz =timezone(self.env.user.tz)
        return int(user_tz.utcoffset(datetime.now()).total_seconds()/ (60*60))

    def _set_l_start_date(self):
        pass

    def _set_l_end_date(self):
        pass
