# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import date
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly',
    help="Defines the frequency of the wage payment.")
    resource_calendar_id = fields.Many2one(required=True, help="Employee's working schedule.")
    
    # Service duration fields
    service_years = fields.Integer(string="Years of Service", 
                                   compute="_compute_service_duration", 
                                   store=False,
                                   help="Number of years worked based on contract start date")
    service_months = fields.Integer(string="Months of Service", 
                                    compute="_compute_service_duration", 
                                    store=False,
                                    help="Number of months worked based on contract start date")

    @api.depends('date_start')
    def _compute_service_duration(self):
        """Compute the years and months of service based on contract start date"""
        for contract in self:
            if contract.date_start:
                today = date.today()
                start_date = contract.date_start
                
                # Calculate the difference using relativedelta
                diff = relativedelta(today, start_date)
                
                contract.service_years = diff.years
                contract.service_months = diff.months
            else:
                contract.service_years = 0
                contract.service_months = 0

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by hierachy (parent=False first,
                 then first level children and so on) and without duplicata
        """
        structures = self.mapped('struct_id')
        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        return self.env['hr.contract.advantage.template'].search([('code', '=', code)], limit=1)[attribute]

    def set_attribute_value(self, code, active):
        for contract in self:
            if active:
                value = self.env['hr.contract.advantage.template'].search([('code', '=', code)], limit=1).default_value
                contract[code] = value
            else:
                contract[code] = 0.0


class HrContractAdvandageTemplate(models.Model):
    _name = 'hr.contract.advantage.template'
    _description = "Employee's Advantage on Contract"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    lower_bound = fields.Float('Lower Bound', help="Lower bound authorized by the employer for this advantage")
    upper_bound = fields.Float('Upper Bound', help="Upper bound authorized by the employer for this advantage")
    default_value = fields.Float('Default value for this advantage')
