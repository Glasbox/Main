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
        result = super(PurchaseOrder, self).write(vals)
        if self.state == 'purchase' and any(item in ['account_id', 'analytic_account_id'] for item in vals.keys()):
            accountid = self.account_id.id
            analytic_account_id = self.analytic_account_id
            budget_positions = self.env['account.budget.post'].search([('account_ids', 'in', [accountid])])
            lines = self.env['crossovered.budget.lines'].search(
                [('analytic_account_id', '=', analytic_account_id.id), ('general_budget_id', 'in', budget_positions.ids)])
            old_lines = self.env['crossovered.budget.lines'].search([('purchase_ids', 'in', [self.id])])
            for line in old_lines:
                line.write({'purchase_ids': [(3, self.id, 0)]})
            for line in lines:
                line.write({'purchase_ids': [(4, self.id, 0)]})
        return result
