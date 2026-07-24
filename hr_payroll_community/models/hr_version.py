# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class HrContract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.version'

    struct_id = fields.Many2one('hr.payroll.structure',
                                string='Salary Structure',
                                help="Choose Payroll Structure")
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
    basic_salary = fields.Monetary(string='Basic Salary', tracking=True,
                                   help="Basic salary component.")
    hra = fields.Monetary(string='HRA', tracking=True,
                          help="House rent allowance.")
    travel_allowance = fields.Monetary(string="Travel Allowance",
                                       help="Travel allowance")
    da = fields.Monetary(string="DA", help="Dearness allowance")
    meal_allowance = fields.Monetary(string="Meal Allowance",
                                     help="Meal allowance")
    medical_allowance = fields.Monetary(string="Medical Allowance",
                                        help="Medical allowance")
    other_allowance = fields.Monetary(string="Other Allowance",
                                      help="Other allowances")
    fixed_allowance = fields.Monetary(string="Fixed Allowance", tracking=True,
                                      help="Fixed allowance component.")
    pay_by_attendance = fields.Boolean(string="Pay by Attendance", default=True, tracking=True,
                                       help="If enabled, payslips include overtime pay and shortage deductions based on attendance. If disabled (Fixed Wage), overtime and shortage adjustments evaluate to 0.00.")

    # Breakdown Percentages
    basic_salary_percent = fields.Float(string='Basic %', compute='_compute_breakdown_percentages', digits=(16, 2))
    hra_percent = fields.Float(string='HRA %', compute='_compute_breakdown_percentages', digits=(16, 2))
    da_percent = fields.Float(string='DA %', compute='_compute_breakdown_percentages', digits=(16, 2))
    travel_allowance_percent = fields.Float(string='Travel %', compute='_compute_breakdown_percentages', digits=(16, 2))
    meal_allowance_percent = fields.Float(string='Meal %', compute='_compute_breakdown_percentages', digits=(16, 2))
    medical_allowance_percent = fields.Float(string='Medical %', compute='_compute_breakdown_percentages', digits=(16, 2))
    other_allowance_percent = fields.Float(string='Other %', compute='_compute_breakdown_percentages', digits=(16, 2))
    fixed_allowance_percent = fields.Float(string='Fixed %', compute='_compute_breakdown_percentages', digits=(16, 2))

    # Breakdown Validation Totals
    breakdown_total = fields.Monetary(string='Total Breakdown', compute='_compute_breakdown_totals')
    breakdown_diff = fields.Monetary(string='Difference', compute='_compute_breakdown_totals')
    breakdown_is_equal = fields.Boolean(string='Is Valid Breakdown', compute='_compute_breakdown_totals')

    @api.depends('wage', 'basic_salary', 'hra', 'da', 'travel_allowance',
                 'meal_allowance', 'medical_allowance', 'other_allowance', 'fixed_allowance')
    def _compute_breakdown_percentages(self):
        for rec in self:
            total = rec.wage or 0.0
            if total > 0.0:
                rec.basic_salary_percent = ((rec.basic_salary or 0.0) / total) * 100.0
                rec.hra_percent = ((rec.hra or 0.0) / total) * 100.0
                rec.da_percent = ((rec.da or 0.0) / total) * 100.0
                rec.travel_allowance_percent = ((rec.travel_allowance or 0.0) / total) * 100.0
                rec.meal_allowance_percent = ((rec.meal_allowance or 0.0) / total) * 100.0
                rec.medical_allowance_percent = ((rec.medical_allowance or 0.0) / total) * 100.0
                rec.other_allowance_percent = ((rec.other_allowance or 0.0) / total) * 100.0
                rec.fixed_allowance_percent = ((rec.fixed_allowance or 0.0) / total) * 100.0
            else:
                rec.basic_salary_percent = 0.0
                rec.hra_percent = 0.0
                rec.da_percent = 0.0
                rec.travel_allowance_percent = 0.0
                rec.meal_allowance_percent = 0.0
                rec.medical_allowance_percent = 0.0
                rec.other_allowance_percent = 0.0
                rec.fixed_allowance_percent = 0.0

    @api.depends('wage', 'basic_salary', 'hra', 'da', 'travel_allowance',
                 'meal_allowance', 'medical_allowance', 'other_allowance', 'fixed_allowance')
    def _compute_breakdown_totals(self):
        for rec in self:
            total_sum = ((rec.basic_salary or 0.0) + (rec.hra or 0.0) + (rec.da or 0.0) +
                         (rec.travel_allowance or 0.0) + (rec.meal_allowance or 0.0) +
                         (rec.medical_allowance or 0.0) + (rec.other_allowance or 0.0) +
                         (rec.fixed_allowance or 0.0))
            rec.breakdown_total = total_sum
            rec.breakdown_diff = total_sum - (rec.wage or 0.0)
            rec.breakdown_is_equal = abs(rec.breakdown_diff) < 0.01

    @api.model
    def _get_whitelist_fields_from_template(self):
        res = super()._get_whitelist_fields_from_template()
        custom_fields = [
            'basic_salary',
            'hra',
            'da',
            'travel_allowance',
            'meal_allowance',
            'medical_allowance',
            'other_allowance',
            'fixed_allowance',
            'pay_by_attendance',
        ]
        for field in custom_fields:
            if field not in res:
                res.append(field)
        return res

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        if self.contract_template_id:
            tmpl = self.contract_template_id
            self.wage = tmpl.wage
            self.basic_salary = tmpl.basic_salary
            self.hra = tmpl.hra
            self.da = tmpl.da
            self.travel_allowance = tmpl.travel_allowance
            self.meal_allowance = tmpl.meal_allowance
            self.medical_allowance = tmpl.medical_allowance
            self.other_allowance = tmpl.other_allowance
            self.fixed_allowance = tmpl.fixed_allowance
            self.pay_by_attendance = tmpl.pay_by_attendance
            if hasattr(tmpl, 'struct_id') and tmpl.struct_id:
                self.struct_id = tmpl.struct_id

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by
        hierarchy (parent=False first,then first level children and so on)
        and without duplicate
        """
        structures = self.mapped('struct_id')
        # structures = self.mapped('contract_template_id.struct_id')

        if not structures:
            return []
        # YTI TODO return browse records
        return list(set(structures._get_parent_structure().ids))

    def get_attribute(self, code, attribute):
        """Function for return code for Contract"""
        return self.env['hr.contract.advantage.template'].search(
                [('code', '=', code)],
                limit=1)[attribute]

    def set_attribute_value(self, code, active):
        """Function for set code for Contract"""
        for contract in self:
            if active:
                value = self.env['hr.contract.advantage.template'].search(
                    [('code', '=', code)], limit=1).default_value
                contract[code] = value
            else:
                contract[code] = 0.0
