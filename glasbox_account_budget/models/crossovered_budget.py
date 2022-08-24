# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    date_from = fields.Date('Start Date', required=False, states={'done': [('readonly', True)]})
    date_to = fields.Date('End Date', required=False, states={'done': [('readonly', True)]})

class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    date_from = fields.Date('Start Date', required=False)
    date_to = fields.Date('End Date', required=False)
    sale_ids = fields.Many2many('sale.order', string="Sale Orders")
    purchase_ids = fields.Many2many('purchase.order', string="Purchase Orders")
    planned_amount = fields.Monetary(
        'Planned Amount', store=True, readonly=True, default=0,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.",
        compute="_compute_planned_amount")

    @api.depends('sale_ids','purchase_ids','sale_ids.amount_untaxed','purchase_ids.amount_untaxed')
    def _compute_planned_amount(self):
        for line in self:
            line.planned_amount = 0
            for sale in line.sale_ids:
                line.planned_amount += sale.amount_untaxed
            for purchase in line.purchase_ids:
                line.planned_amount -= purchase.amount_untaxed

    @api.depends('planned_amount','practical_amount')
    def _compute_theoritical_amount(self):
        '''
        PSUS custom modifications - overriding base method:
            - modify @api.depends parameters to use planned_amount
            and practical_amount instead of date_from and date_to
            - theoritical_amount value is computed from using
            planned_amount and the practical_amount; it does not
            take take dates into consideration

        '''
        for line in self:
            line.theoritical_amount = line.planned_amount - line.practical_amount

    @api.depends('planned_amount','practical_amount')
    def _compute_percentage(self):
        '''
        PSUS custom modifications - overriding base method:
            - the percentage does not use theoritical_amount
            as a condition
        '''
        for line in self:
            if line.planned_amount != 0.00:
                line.percentage = line.practical_amount/line.planned_amount 
            else:
                line.percentage = 0.00

    def action_open_budget_entries(self):
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
            action['domain'] = [('account_id', '=', self.analytic_account_id.id),
                                ]
            if self.general_budget_id:
                action['domain'] += [('general_account_id', 'in', self.general_budget_id.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            action['domain'] = [('account_id', 'in', self.general_budget_id.account_ids.ids),
                                ]
        return action

    def _compute_practical_amount(self):
        '''
        PSUS custom modifications - overriding base method:
            - practical_amount computation no longer uses the
            Start Date and the End Date in the domain
        '''
        for line in self:
            acc_ids = line.general_budget_id.account_ids.ids
            if line.analytic_account_id.id:
                analytic_line_obj = self.env['account.analytic.line']
                domain = [('account_id', '=', line.analytic_account_id.id),
                          ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]

                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause
                self.env.cr.execute(select, where_clause_params)
                line.practical_amount = self.env.cr.fetchone()[0] or 0.0
            else:
                line.practical_amount = 0.0