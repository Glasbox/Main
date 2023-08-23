from odoo import models, api
from odoo.osv import expression


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"


    @api.model
    def _search_message_partner_ids(self, operator, operand):
        e = expression.expression([
            ('res_model', '=', self._name),
            ('partner_id', operator, operand)], self.env['mail.followers'])
        from_clause, where_clause, where_params = e.query.get_sql()
        query = f"""
            SELECT res_id FROM {from_clause} WHERE {where_clause}
        """
        self._flush_search([])
        self.env.cr.execute(query, where_params)
        ids = self.env.cr.fetchall()
        return [('id', 'in', [vals[0] for vals in ids])]