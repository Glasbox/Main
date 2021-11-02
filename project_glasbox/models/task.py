import json
from datetime import timedelta, datetime, date
from odoo.exceptions import ValidationError, UserError
from odoo import models, fields, api
import pytz

class DependingTasks(models.Model):
    _name = "project.depending.tasks"
    _description = "Tasks Dependency (m2m)"

    task_id = fields.Many2one('project.task', required=True)
    project_id = fields.Many2one('project.project', string='Project')
    depending_task_id = fields.Many2one('project.task', required=True)
    relation_type = fields.Char('Relation', default="Finish To Start")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('done', 'Done')], default='draft')

class TaskDependency(models.Model):
    _inherit = "project.task"

    planned_duration = fields.Integer('Duration', default=1)
    buffer_time = fields.Integer('Buffer Time')
    task_delay = fields.Integer('Task Delay', compute='_compute_delay', store=True)
    accumulated_delay = fields.Integer('Accumulated Delay', compute='_compute_accumulated_delay', store=True)
    on_hold = fields.Integer("On Hold")
    dependency_task_ids = fields.One2many('project.depending.tasks', 'depending_task_id')
    links_serialized_json = fields.Char('Serialized Links JSON', compute="compute_links_json")
    date_start = fields.Date('Starting Date', compute='_compute_start_date', store=True)
    date_end = fields.Date('Ending Date', readonly=True, compute='_compute_end_date', store=True)
    completion_date = fields.Date('Completion Date')
    milestone = fields.Boolean(string='Mark as Milestone', default=False)
    first_task = fields.Boolean(string='First Task', default=False)
    l_start_date = fields.Date('Latest Start Date',compute='_compute_l_start_end_date', store=True)
    l_end_date = fields.Date('Latest End Date', compute='_compute_l_start_end_date', store=True)
    duration_mode = fields.Char(readonly=True)
    delay_due_to = fields.Char("Delay Due To")
    check_completion_date = fields.Boolean('Check Completion Date', compute="_compute_check_com_date", default=False)
    check_l_end_date = fields.Boolean('Check Latest End Date', compute="_compute_check_l_end_date", default=False)
    check_c_date = fields.Boolean('Check Whether the Completion Date is set or not', compute="_compute_c_date")
    scheduling_mode = fields.Selection([
        ("0", "Must Start On"),
        ("1", "Must Finish On"),
    ], "Scheduling Mode")

    def get_calendar(self):
        return self.env.company.resource_calendar_id

    def get_global_ids(self):
        return self.get_calendar().global_leave_ids

    def count_tasks(self):
        return len(self.dependency_task_ids.task_id)

    def get_work_days(self):
        '''
            Method for getting company's work_days(business_days) according to company's calendar.
        '''
        for r in self:
            resource_calendar = r.get_calendar()
            sum_hours = sum((attendance.hour_to - attendance.hour_from) for attendance in resource_calendar.attendance_ids)
            hour = resource_calendar.hours_per_day
            # tz = resource_calendar.tz
            return (sum_hours / hour)

    def get_holidays(self, start_date):
        '''
            Method for getting company's holiday's according to company's calendar and only one date.
            You will get holiday's date in list.
        '''
        for r in self:
            if r.l_end_date:
                leaves = r.get_global_ids().filtered(lambda d: start_date and d.date_from.date() < start_date)
            else:
                leaves = r.get_global_ids().filtered(lambda d: start_date and d.date_from.date() > start_date)
            lst_days = []
            for leave in leaves:
                l_days = [leave.date_from.date()+timedelta(days=x) for x in range((leave.date_to.date()-leave.date_from.date()+timedelta(days=1)).days)]
                for days  in l_days:
                    lst_days.append(days)
            return lst_days
    
    def get_holidays_between_dates(self, start_date, end_date):
        '''
            Method for getting holiday's between two dates according to comapny's calendar.
            You will get holiday's date in list
        '''
        for r in self:
            work_days = r.get_work_days()
            daydiff = start_date.weekday() - end_date.weekday()
            working_days = ((start_date-end_date).days - daydiff) / 7 * work_days + min(daydiff,work_days) - (max(start_date.weekday() - 4, 0) % work_days)

            leaves = r.get_global_ids().filtered(lambda d: d.date_from.date() > start_date)
            lst_days = []
            for leave in leaves:
                l_days = [leave.date_from.date()+timedelta(days=x) for x in range((leave.date_to.date()-leave.date_from.date()+timedelta(days=1)).days)]
                # lst_days.append(days for days in l_days if start_date <= days <= end_date)
                for days  in l_days:
                    if  start_date <= days <= end_date:
                        lst_days.append(days)
            return (working_days - len(lst_days) if working_days > 0 else len(lst_days) + working_days)

    def get_forward_next_date(self, start_date):
        for r in self:
            work_days = r.get_work_days()
            duration = 0
            # if self.planned_duration or self.on_hold or self.buffer_time:
            if r.milestone == True and r.l_start_date:
                duration = r.planned_duration
            else:
                duration = r.planned_duration + r.on_hold + r.buffer_time
            if start_date:
                next_date = start_date + timedelta(days=-1)
                holidays = r.get_holidays(start_date)
                while duration > 0:
                    next_date += timedelta(days=1)
                    weekday = next_date.weekday()
                    # skip non-working_days
                    if weekday >= work_days:
                        continue
                    # skip holiday
                    if next_date in holidays:
                        continue
                    duration -= 1
                return r.date_in_holiday(next_date)

    def get_backward_next_date(self,previous_date):
        for r in self:
            work_days = r.get_work_days()
            duration = r.planned_duration - 1
            holidays = r.get_holidays(previous_date)
            if previous_date:
                while duration > 0:
                    previous_date -= timedelta(days=1)
                    weekday = previous_date.weekday()
                    # skip non-working days
                    if weekday >= work_days:
                        continue
                    # skip holiday
                    if previous_date in holidays:
                        continue
                    duration -= 1
                return previous_date

    def check_date_weekend(self, start_date):
        '''
            Method for to check whether the 'date' is in weekend or not.
            If the date is in weekend then we will update that date according to company's workday.
            If date is not in weekend then we will update that date through one day.
        '''
        for r in self:
            weekdays = 7
            work_days = r.get_work_days()
            no_of_days = weekdays - work_days

            if start_date and start_date.weekday() >= work_days:
                start_date = start_date + timedelta(days=no_of_days)
            elif start_date and start_date.weekday() < work_days:
                start_date = start_date + timedelta(days=1)
        
            return start_date

    def date_in_holiday(self, start_date):
        '''
            Method for to check 'date' is in holiday or not.
            If 'date' is in holiday then we will increment date by one day and check that 'date' is in weekend or not.
            If 'date' is not in holiday then we will increment date through one day and check that 'date' is in weekend or not. 
        '''
        for r in self:
            work_days = r.get_work_days()
            holidays = r.get_holidays(start_date)
            if start_date not in holidays:
                new_start_date = r.check_date_weekend(start_date)

            for start_date in holidays:
                start_date += timedelta(days=1)
                new_start_date = r.check_date_weekend(start_date)

            return new_start_date

    def _send_mail_template(self):
        for r in self:
            '''
                Method for sending mail to the assigned user of A3 task, when it's dependent tasks 
                A1's completion date is set and A2's completion date is not set.
                Whenever, A2's completion date is set, mail will be automatically sent to the A3 Task's
                assigned user.
            '''
            template = r.env.ref('project_glasbox.task_completion_email_template')
            tasks = r.env['project.task'].search([('dependency_task_ids.task_id', 'in', r.ids)])
            tasks.message_post_with_template(template_id=template.id)
   
    def write(self, vals):
        # OVERRIDE to write method
        '''
            If the A1 completion date is set but the A2 completion date is not set,
            Until A2's completion date is set, A3 starting date will get updated according to 
            A2's completion date (because A2 is the latest completion date then A1)
        '''
        for r in self:
            res = super(TaskDependency, r).write(vals)
            task_count = r.count_tasks()
            # r._dependent_l_start_end_date()
            if 'completion_date' in vals:
                date_start = datetime.strptime(vals['completion_date'],"%Y-%m-%d") + timedelta(days=1)
                tasks = r.env['project.task'].search([('dependency_task_ids.task_id', 'in', r.ids)])
                if task_count == 0:
                    tasks.write({
                        'date_start': False,
                        'date_end': False
                        })
                tasks.write({'date_start': date_start})
                r._send_mail_template()

            return res

    @api.onchange('completion_date')
    def onchange_completion_date(self):
        '''
            The Completion date can only be today’s date! 
            Nobody can set yesterday's or next week’s date as the completion date.
        '''
        ctx = self.env.context
        if ctx.get('c_date'):
            self.completion_date = datetime.now()

    @api.onchange('dependency_task_ids')
    def onchange_changes(self):
        for r in self:
            task_count = r.count_tasks()
            if r.milestone == True and r.dependency_task_ids:
                # list of all the 'l_start_date' of the each dependent task
                l_start_date_lst = r.dependency_task_ids.task_id.mapped('l_start_date')
                # list of all the 'l_end_date' of the each dependent task
                l_end_date_lst = r.dependency_task_ids.task_id.mapped('l_end_date')
                '''
                    For none milestone task, 'l_start_date' will be calculated when the milestone tasks’ Latest start/end date got inserted. 
                    Use the current task calculated Latest end date -  current task Duration (but not buffer time) - current task On hold (if any). 
                    Read-only field for non-milestone tasks.
                '''
                l_start_cal = r.l_end_date - timedelta(r.planned_duration) - timedelta(r.on_hold)
                '''
                    For none milestone task, 'l_end_date' is calculate with the next tasks’ latest start date minus one business day. 
                    This will be the read-only field.
                '''
                l_end_cal = r.l_start_date - timedelta(days=1)
                for task in r.dependency_task_ids:
                    if task_count == 0:
                        task.task_id.l_start_date =  False
                        task.task_id.l_end_date = False
                    elif task.task_id.milestone == False and task.task_id.l_start_date == False and task.task_id.l_end_date == False:
                        task.task_id.l_start_date = r.date_in_holiday(l_start_cal)
                        task.task_id.l_end_date = r.date_in_holiday(l_end_cal)

    @api.depends('completion_date')
    def _compute_c_date(self):
        for task in self:
            if task.completion_date == False:
                task.check_c_date = False 
            else:
                task.check_c_date = True

    @api.depends('completion_date','date_end')
    def _compute_check_com_date(self):
        for task in self:
            if task.completion_date == False or task.date_end == False:
                task.check_completion_date = False
            else:
                task.check_completion_date = task.completion_date <= task.date_end

    @api.depends('completion_date', 'l_end_date')
    def _compute_check_l_end_date(self):
        for task in self:
            if task.completion_date == False or task.l_end_date == False:
                task.check_l_end_date = False
            else:
                task.check_l_end_date = task.completion_date >= task.l_end_date

    @api.depends('completion_date','date_end')
    def _compute_delay(self):
        '''
            Method For calculating the 'task_delay' based on the 'completion_date' and 'date_end'.
            task_delay = completion_date - date_end
            Here, you will get 'negative delay' if task finished if the task finished earlier than planned.
        '''
        # self.ensure_one()
        for r in self:
            if r.date_end and r.completion_date:
                # start_date = r.completion_date 
                # end_date = r.date_end
                r.task_delay = r.get_holidays_between_dates(r.completion_date, r.date_end)

    @api.depends('dependency_task_ids.task_id.completion_date')
    def _compute_accumulated_delay(self):
        for r in self:
            task_count = r.count_tasks()
            # if task_count = 0 it means that no task is set as a 'dependent task'
            if task_count == 0:
                if r.dependency_task_ids:
                    r.accumulated_delay = 0 # set 'accumulated_delay' is 0 if no dependent task is set
                else:
                    r.accumulated_delay = r.accumulated_delay
            else:
                '''
                    Only fill in accumulated delay when all previous dependent tasks have a completion date.
                '''
                # list of all the 'completion_date' of the each dependent task
                completion_date_lst = r.dependency_task_ids.task_id.mapped('completion_date')
                if False in completion_date_lst:
                    r.accumulated_delay = 0
                else:
                    '''
                        If current task is not 'first_task' and it has dependent tasks and 'taks_count' is 1 and the dependent task is 'first_task' 
                        then set 'accumulated_delay' = dependent task's 'task_delay' + current task's task_delay
                    '''
                    if task_count == 1 and r.dependency_task_ids.task_id['first_task'] == True:
                        r.accumulated_delay = r.dependency_task_ids.task_id['task_delay'] + r.task_delay
                    else:
                        delay_lst = r.dependency_task_ids.task_id.mapped('accumulated_delay')
                        r.accumulated_delay = max(sorted(delay_lst)) + r.task_delay

    @api.depends('dependency_task_ids.task_id.completion_date')
    def _compute_start_date(self):
        for r in self:
            task_count = r.count_tasks()
            if task_count == 0:
                if r.dependency_task_ids:
                    r.date_start = False
                    r.date_end = False
                elif r.date_start:
                    r.date_start = r.date_start # if task has no dependent tasks then it will use current task's date_start
            else:
                if r.first_task != True and r.dependency_task_ids:
                    '''
                        If task_count = 1 and it has only one dependent task and that dependent task has 'completion_date' is set 
                        then current task's 'date_start' = previous task's completion_date + 1.
                    '''
                    # list of all the 'completion_date' of the each dependent task
                    completion_date_lst = r.dependency_task_ids.task_id.mapped('completion_date')
                    end_date_lst = r.dependency_task_ids.task_id.mapped('date_end')
                    first_element = completion_date_lst[0]
                    if task_count == 1 and len(completion_date_lst) == 1 and completion_date_lst[0] != False:
                        r.date_start = r.date_in_holiday(first_element)
                    elif False in completion_date_lst:
                        '''
                            If we have only one value in 'completion_date_lst' and the value is False
                            then current task's 'date_start' is previous task's 'end_date' + 1
                        '''
                        if len(completion_date_lst) == 1 and completion_date_lst[0] == False:
                            r.date_start = r.date_in_holiday(r.dependency_task_ids.task_id.date_end)
                        else:
                            '''
                                If A1 completion date is set but A2 completion date is not set, 
                                then use A1 completion date +1 business day as A3 starting date.
                            '''
                            for i in range(len(completion_date_lst)):
                                previous_el = completion_date_lst[i-1]
                                if completion_date_lst[i] == False:
                                    # finding the number of times 'False' we are getting in list
                                    occurrences = completion_date_lst.count(False)
                                    if occurrences == 1:
                                        if previous_el and previous_el != False:
                                            r.date_start = r.date_in_holiday(previous_el)
                                        elif previous_el:
                                            # if occurrences are > 1 then, we will take max date from completion_date list
                                            max_comp_date = max(sorted(completion_date_lst))
                                            r.date_start = r.date_in_holiday(max_comp_date)
                                    else:
                                        r.date_start = r.date_in_holiday(previous_el)
                    else:
                        for date_start in completion_date_lst:
                            if date_start != first_element and False not in completion_date_lst:
                                '''
                                    If 'first_element' of 'completion_date' is not equal to 'date' 
                                    then 'date_start' of the current task will be calculated from the previous task 
                                    (take all the dependent task and take 'max_date' from all the dependent task) completion date 
                                    (use ending date if completion date is not set) + 1
                                '''
                                max_date_start = max(sorted(completion_date_lst))
                                r.date_start = r.date_in_holiday(max_date_start)
                            elif date_start == False and False not in end_date_lst and len(completion_date_lst) == 0:
                                max_end_date = max(sorted(end_date_lst))
                                r.date_start = r.date_in_holiday(max_end_date)
                            else:
                                '''
                                    If 'completion_date' of the previous tasks are same in the 'date_lst' then
                                    we simply set set 'date_start' as a 'first_element' + 1
                                '''
                                r.date_start = r.date_in_holiday(first_element)

    @api.depends('planned_duration', 'buffer_time', 'on_hold', 'date_start')
    def _compute_end_date(self):
        '''
            Method for to set 'date_end' dynamically (applied forward calculation) according to 'date_start', 'planned_duration', 'buffer_time' and 'on_hold'.
            
            Here, the calculation of 'date_end' is as follows:-
            date_end = date_start + planned_duration + buffer_time + on_hold
        '''
        for r in self:
            start_date = r.date_start
            if r.first_task == True or start_date:
                r.date_end = r.get_forward_next_date(start_date)
                if r.date_end:
                    r.date_end = r.date_end

    @api.depends('l_end_date','l_start_date','planned_duration','milestone','scheduling_mode')
    def _compute_l_start_end_date(self):
        '''
            Method for to set 'l_start_date' dynamically (applied backward calculation) according to
            'l_end_date' and 'planned_duration'

            Here, the calculation of 'l_start_date' is as follows:-
            l_start_date = l_end_date - planned_duration

            Here, the calculation of 'l_end_date' is as follows:-
            l_end_date = l_date_start + planned_duration
        '''
        for r in self:
            if r.milestone == True and r.scheduling_mode == '1' and r.l_end_date:
                l_start = r.get_backward_next_date(r.l_end_date)
                r.l_start_date = r.date_in_holiday(l_start)
            elif r.milestone == True and r.scheduling_mode == '0' and r.l_start_date:
                l_end = r.get_forward_next_date(r.l_start_date)
                r.l_end_date = r.date_in_holiday(l_end)
