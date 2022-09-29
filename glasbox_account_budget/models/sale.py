# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 'Analytic Account',
        readonly=True, copy=True, check_company=True,  # Unrequired company
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The analytic account related to a sales order.")
    account_id = fields.Many2one('account.account', states={'done': [('readonly', True)]})

    def action_confirm(self):
        res = super().action_confirm()
        if res:
            accountid = self.account_id
            analytic_account = self.analytic_account_id
            if accountid and analytic_account:
                budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', [accountid.id])])
                lines = self.env['crossovered.budget.lines'].search(
                    [('analytic_account_id', '=', analytic_account.id), ('general_budget_id', 'in', budget_positions.ids)])
                for line in lines:
                    line.write({'sale_ids': [(4, self.id, 0)]})
        return res

    def write(self, vals):
        #Some refactoring to consider recordsets and not only singletons
        result = super().write(vals)
        account_ids = []
        analytical_accounts_ids = []
        #Get all items for the search domains.
        for sale in self:
            if sale.state == 'sale':
                account_ids.append(sale.account_id.id) if sale.account_id.id not in account_ids else None
                analytical_accounts_ids.append(sale.analytic_account_id.id) if sale.analytic_account_id.id not in analytical_accounts_ids else None

        #Make only one search for all the records we want to touch.
        all_budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', account_ids)])
        all_budget_lines = self.env['crossovered.budget.lines'].search(
                [('analytic_account_id', 'in', analytical_accounts_ids), ('general_budget_id', 'in', all_budget_positions.ids)])
        all_old_lines = self.env['crossovered.budget.lines'].search([('sale_ids', 'in', self.ids)])

        #Iterate over the recordset to modify the propper values.
        for sale in self:
            if sale.state == 'sale':
                accountid = sale.account_id.id
                analytic_account_id = sale.analytic_account_id.id
                budget_positions = all_budget_positions.filtered(lambda position: accountid in position.account_ids.ids)
                lines = all_budget_lines.filtered(lambda budget_line: analytic_account_id in budget_line.analytic_account_id.ids and budget_line.general_budget_id.id in budget_positions.ids)
                old_lines = all_old_lines.filtered(lambda old_line: sale.id in old_line.sale_ids.ids)
                for line in old_lines:
                    line.write({'sale_ids': [(3, self.id, 0)]})
                for line in lines:
                    line.write({'sale_ids': [(4, self.id, 0)]})
        return result
