# -*- coding: utf-8 -*-

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    analytic_account_id = fields.Many2one('account.analytic.account', states={'done': [('readonly', True)]})
    account_id = fields.Many2one('account.account', states={'done': [('readonly', True)]})

    def button_confirm(self):
        res = super().button_confirm()
        if res:
            accountid = self.account_id
            analytic_account = self.analytic_account_id
            if accountid and analytic_account:
                budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', [accountid.id])])
                lines = self.env['crossovered.budget.lines'].search(
                    [('analytic_account_id', '=', analytic_account.id), ('general_budget_id', 'in', budget_positions.ids)])
                for line in lines:
                    line.write({'purchase_ids': [(4, self.id, 0)]})
        return res

    def write(self, vals):
        #Some refactoring to consider recordsets and not only singletons
        result = super().write(vals)
        account_ids = []
        analytical_accounts_ids = []
        #Get all items for the search domains.
        for purchase in self:
            if purchase.state == 'purchase':
                account_ids.append(purchase.account_id.id) if purchase.account_id.id not in account_ids else None
                analytical_accounts_ids.append(purchase.analytic_account_id.id) if purchase.analytic_account_id.id not in analytical_accounts_ids else None

        #Make only one search for all the records we want to touch.
        all_budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', account_ids)])
        all_budget_lines = self.env['crossovered.budget.lines'].search(
                [('analytic_account_id', 'in', analytical_accounts_ids), ('general_budget_id', 'in', all_budget_positions.ids)])
        all_old_lines = self.env['crossovered.budget.lines'].search([('purchase_ids', 'in', self.ids)])
        print(all_budget_positions, all_budget_lines, all_old_lines)

        #Iterate over the recordset to modify the propper values.
        for purchase in self:
            if purchase.state == 'purchase':
                accountid = purchase.account_id.id
                analytic_account_id = purchase.analytic_account_id.id
                budget_positions = all_budget_positions.filtered(lambda position: accountid in position.account_ids.ids)
                lines = all_budget_lines.filtered(lambda budget_line: analytic_account_id in budget_line.analytic_account_id.ids and budget_line.general_budget_id.id in budget_positions.ids)
                old_lines = all_old_lines.filtered(lambda old_line: purchase.id in old_line.purchase_ids.ids)
                for line in old_lines:
                    line.write({'purchase_ids': [(3, self.id, 0)]})
                for line in lines:
                    line.write({'purchase_ids': [(4, self.id, 0)]})
        return result
