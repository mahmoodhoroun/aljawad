from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    show_in_outstanding = fields.Boolean(string='Show in Outstanding Credits/Debits', default=True,
                                        help='If unchecked, this entry will not appear in Outstanding Credits/Debits widget')
    
    phone_number_sale_order = fields.Char(string='Phone Number')
    
    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue
                if line.move_id.show_in_outstanding:
                    payments_widget_vals['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount,
                        'currency_id': move.currency_id.id,
                        'id': line.id,
                        'move_id': line.move_id.id,
                        'date': fields.Date.to_string(line.date),
                        'account_payment_id': line.payment_id.id,
                    })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True
    

    def button_create_reverse_entry(self):
        """
        This function creates reverse journal entries for selected invoices.
        It directly creates new journal entries with reversed debit and credit amounts.
        Works with single or multiple records.
        """
        # Filter only posted entries
        posted_moves = self.filtered(lambda m: m.state == 'posted')
        if not posted_moves:
            raise UserError(_('You can only reverse posted entries.'))
        
        created_count = 0
        for record in posted_moves:
            # Get the original entry lines
            original_entry = record.line_ids

            # Prepare reversed lines
            reverse_lines = []
            for line in original_entry:
                vals = {
                    'account_id': line.account_id.id,
                    'name': 'Reverse of: ' + (line.name or ''),
                    'debit': line.credit,
                    'credit': line.debit,
                    'partner_id': line.partner_id.id,
                    'analytic_distribution': line.analytic_distribution if hasattr(line, 'analytic_distribution') else False,
                    'tax_ids': [(6, 0, line.tax_ids.ids)] if hasattr(line, 'tax_ids') and line.tax_ids else False,
                    'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)] if hasattr(line, 'tax_tag_ids') and line.tax_tag_ids else False,
                }
                
                # Only add tax_repartition_line_id if it exists on the line
                if hasattr(line, 'tax_repartition_line_id') and line.tax_repartition_line_id:
                    vals['tax_repartition_line_id'] = line.tax_repartition_line_id.id
                    
                reverse_lines.append((0, 0, vals))

            # Create the reverse journal entry
            reverse_move = self.env['account.move'].create({
                'journal_id': record.journal_id.id,
                'date': record.invoice_date,
                'ref': 'Auto-Reverse of %s' % record.name,
                'move_type': 'entry',
                'line_ids': reverse_lines,
                'show_in_outstanding': False,  # Set to False to hide from Outstanding Credits/Debits
            })
            
            # Post the reverse entry
            reverse_move.action_post()
            created_count += 1
                
        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%d reverse journal entries created successfully') % created_count,
                'type': 'success',
                'sticky': False,
            }
        }

