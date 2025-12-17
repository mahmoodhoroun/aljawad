from odoo import api, models, _


class ReportTax(models.AbstractModel):
    _inherit = 'account.account_common_report_view'
    
    def _sql_from_amls_lines(self):
        sql = """SELECT "account_move_line".tax_line_id, "account_move_line".name,
                "account_move_line".credit, "account_move_line".debit, "account_move_line".date,
                rp.name as partner_name, rp.vat
                FROM %s 
                LEFT JOIN res_partner rp ON (rp.id = "account_move_line".partner_id)
                WHERE %s AND "account_move_line".tax_line_id is not NULL"""
        return sql

    def _compute_from_amls(self, options, taxes):
        #compute the tax amount
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)

        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['tax'] = abs(result[1])

        
        #compute the net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in taxes:
                taxes[result[0]]['net'] = abs(result[1])

        new_sql = self._sql_from_amls_lines()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = new_sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.fetchall()
        for k, *v in results:
            if k in taxes:
                taxes[k]['vals'].append(v)

    @api.model
    def get_lines(self, options):
        taxes = {}
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use, 'vals':[]}
            else:
                taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use, 'vals': []}
        print(options)
        self.with_context(date_from=options['date_from'], date_to=options['date_to'],
                          state=options['target_move'],
                          strict_range=True)._compute_from_amls(options, taxes)
        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax in taxes.values():
            if tax['tax']:
                groups[tax['type']].append(tax)
        return groups