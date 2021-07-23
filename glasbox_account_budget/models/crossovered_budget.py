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
        'Planned Amount', required=True, store=True, readonly=False,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.",
        compute="_compute_planned_amount")

    @api.depends('sale_ids','purchase_ids','sale_ids.amount_untaxed','purchase_ids.amount_untaxed')
    def _compute_planned_amount(self):
        for line in self:
            line.planned_amount = 0
            for sale in line.sale_ids:
                line.planned_amount += sale.amount_untaxed
            for purchase in line.purchase_ids:
                line.planned_amount += purchase.amount_untaxed

    @api.depends('planned_amount','practical_amount')
    def _compute_theoritical_amount(self):
        for line in self:
            line.theoritical_amount = line.planned_amount - line.practical_amount

    @api.depends('planned_amount','practical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.planned_amount != 0.00:
                line.percentage = line.practical_amount/line.planned_amount 
            else:
                line.percentage = 0.00

    def _compute_practical_amount(self):
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

            else:
                aml_obj = self.env['account.move.line']
                domain = [('account_id', 'in',
                           line.general_budget_id.account_ids.ids),
                          ('move_id.state', '=', 'posted')
                          ]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)
            line.practical_amount = self.env.cr.fetchone()[0] or 0.0
