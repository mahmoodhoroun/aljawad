import string
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SalesCommission(models.Model):
    _name = 'sales.commission'
    _description = 'Sales Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _rec_name = 'commission_number'
    _order = 'commission_number desc'

    commission_number = fields.Char(string='Commission Number', required=True, copy=False, readonly=True, default=lambda self: ('New'))
    commission_date = fields.Date(string='Commission Date', required=True, default=fields.Date.context_today)
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    partner_id = fields.Many2one('res.partner', string='Partner')
    quotation_id = fields.Many2one('sale.order', string='Quotation Number')
    invoice_id = fields.Many2one('account.move', string='Invoice Number', domain=[('move_type', '=', 'out_invoice')])
    # part_number = fields.Char(string='Part Number', compute='_compute_part_number', store=True)
    total = fields.Float(string='Total With Tax', compute='_compute_total', store=True)
    total_before_tax = fields.Float(string='Total Before Tax', compute='_compute_total_before_tax', store=True)
    paid = fields.Float(string='Paid')
    # not_paid = fields.Float(string='Not Paid', compute='_compute_not_paid', store=True)
    commission_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('rate', 'Rate after Tax (%)'),
        ('rate_before', 'Rate before Tax (%)')
    ], string='Commission Type', default='fixed', required=True)
    commission_rate = fields.Float(string='Commission Rate (%)')
    fixed_amount = fields.Float(string='Fixed Amount')
    commission_value = fields.Float(string='Commission Value', compute='_compute_commission_value', store=True, readonly=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        # ('not_paid', 'Not Paid'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', required=True, copy=False)
    
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    move_count = fields.Integer(string='Journal Entries', compute='_compute_move_count')
    customer_salesperson = fields.Many2one('res.partner', string='Purchasing Person', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    def _compute_move_count(self):
        for record in self:
            moves = self.env['account.move'].search([('commission_id', '=', record.id)])
            record.move_count = len(moves)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('commission_number', ('New')) == ('New'):
                vals['commission_number'] = self.env['ir.sequence'].next_by_code('sales.commission') or ('New')
            # Set commission_date to today if not provided
            if not vals.get('commission_date'):
                vals['commission_date'] = fields.Date.context_today(self)
            # Always set initial status as draft
            vals['status'] = 'draft'
        return super(SalesCommission, self).create(vals_list)

    @api.depends('invoice_id', 'total')
    def _compute_total(self):
        for record in self:
            if record.invoice_id:
                record.total = record.invoice_id.amount_total
            else:
                record.total = 0.0
    
    @api.depends('invoice_id', 'total')
    def _compute_total_before_tax(self):
        for record in self:
            if record.invoice_id:
                record.total_before_tax = record.invoice_id.amount_untaxed
            else:
                record.total_before_tax = 0.0

    # @api.depends('quotation_id')
    # def _compute_part_number(self):
    #     for record in self:
    #         record.part_number = record.quotation_id.lot_number

    @api.depends('total', 'commission_rate', 'fixed_amount', 'commission_type')
    def _compute_commission_value(self):
        for record in self:
            if record.commission_type == 'fixed':
                record.commission_value = record.fixed_amount
            elif record.commission_type == 'rate':
                record.commission_value = (record.total * record.commission_rate) / 100
            elif record.commission_type == 'rate_before':
                record.commission_value = (record.total_before_tax * record.commission_rate) / 100

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected commissions.
        :return: An action opening the account.payment.register wizard.
        '''
        company = self.env.company
        if not company.commission_payable_account_id:
            raise UserError(_('Please configure commission payable account in settings first!'))

        return {
            'name': 'Register Payment',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'sales.commission',
                'active_ids': self.ids,
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': self[0].customer_salesperson.id,
                'default_amount': sum(self.mapped('commission_value')),
                # Use commission payable account as source account
                'default_source_account_id': company.commission_payable_account_id.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def create_journal_entry(self):
        """Create journal entry for commission"""
        self.ensure_one()
        company = self.env.company

        if not company.commission_account_id or not company.commission_payable_account_id or not company.commission_journal_id:
            raise UserError(_('Please configure commission accounts in settings first!'))

        move_vals = {
            'ref': _('Commission for %s') % self.commission_number,
            'move_type': 'entry',
            'journal_id': company.commission_journal_id.id,
            # 'journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'partner_id': self.customer_salesperson.id,
            'date': fields.Date.context_today(self),
            'line_ids': [
                (0, 0, {
                    'name': _('Commission Expense'),
                    'debit': self.commission_value,
                    'credit': 0.0,
                    'account_id': company.commission_account_id.id,
                    'partner_id': self.customer_salesperson.id,
                }),
                (0, 0, {
                    'name': _('Commission Payable'),
                    'debit': 0.0,
                    'credit': self.commission_value,
                    'account_id': company.commission_payable_account_id.id,
                    'partner_id': self.customer_salesperson.id,
                })
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.commission_id = self.id
        move.action_post()

        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current'
        }

    def action_confirm(self):
        for record in self:
            if record.status == 'draft':
                # First create the journal entry
                record.create_journal_entry()
                # Then mark as confirmed
                record.write({'status': 'confirmed'})

    def action_view_moves(self):
        self.ensure_one()
        moves = self.env['account.move'].search([('commission_id', '=', self.id)])
        action = {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }
        if len(moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves.id,
            })
        return action

    def reset_to_draft(self):
        for record in self:
            moves = self.env['account.move'].search([('commission_id', '=', self.id)])
            for move_id in moves:
                move_id.button_cancel()
                move_id.unlink()
            record.status = 'draft'

    def update_company_from_sale_order(self):
        """Update company_id from related sale order for selected commissions"""
        updated_count = 0
        skipped_count = 0
        
        for record in self:
            if record.quotation_id and record.quotation_id.company_id:
                # Update company from sale order
                old_company = record.company_id.name if record.company_id else 'None'
                new_company = record.quotation_id.company_id.name
                
                record.company_id = record.quotation_id.company_id.id
                updated_count += 1
                
                # Log the update
                record.message_post(
                    body=_('Company updated from "%s" to "%s" based on Sale Order %s') % (
                        old_company, new_company, record.quotation_id.name
                    )
                )
            else:
                skipped_count += 1
        
        # Show notification message
        if updated_count > 0:
            message = _('%d commission(s) updated successfully.') % updated_count
            if skipped_count > 0:
                message += _(' %d commission(s) skipped (no sale order or company).') % skipped_count
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Company Update Complete'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Updates'),
                    'message': _('No commissions were updated. Make sure selected commissions have related sale orders with companies.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        