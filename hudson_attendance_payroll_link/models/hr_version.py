# -*- coding: utf-8 -*-
from odoo import api, fields, models

class HrVersion(models.Model):
    _inherit = 'hr.version'

    standard_working_days_per_month = fields.Float(
        string='Standard Working Days per Month',
        default=26.0,
        help="Number of working days in a month for hourly rate calculation."
    )
    standard_hours_per_day = fields.Float(
        string='Standard Hours per Day',
        default=8.0,
        help="Number of hours in a standard working day."
    )
    overtime_multiplier = fields.Float(
        string='Overtime Multiplier',
        default=1.0,
        help="Overtime rate multiplier applied to the standard hourly rate."
    )
    hourly_rate = fields.Float(
        string='Computed Hourly Rate',
        compute='_compute_hourly_rate',
        store=True,
        help="Computed standard hourly rate: Monthly Salary / (Working Days * Hours per Day)"
    )
    overtime_hourly_rate = fields.Float(
        string='Computed Overtime Hourly Rate',
        compute='_compute_overtime_hourly_rate',
        store=True,
        help="Computed overtime hourly rate: Standard Hourly Rate * Overtime Multiplier"
    )

    # Writable rate fields with conditional computation
    overtime_rate_per_hour = fields.Float(
        compute='_compute_overtime_rate_per_hour',
        store=True,
        readonly=False,
        string='Overtime Rate (per hour)'
    )
    shortage_deduction_rate_per_hour = fields.Float(
        compute='_compute_shortage_deduction_rate_per_hour',
        store=True,
        readonly=False,
        string='Shortage Deduction Rate (per hour)'
    )

    # Boolean tracking fields for manual overrides
    overtime_rate_manually_set = fields.Boolean(
        string='Overtime Rate Manually Set',
        default=False,
        store=True,
    )
    shortage_rate_manually_set = fields.Boolean(
        string='Shortage Rate Manually Set',
        default=False,
        store=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super(HrVersion, self).default_get(fields_list)
        company = self.env.company
        if 'standard_working_days_per_month' in fields_list and 'standard_working_days_per_month' not in res:
            res['standard_working_days_per_month'] = company.standard_working_days_per_month or 26.0
        if 'standard_hours_per_day' in fields_list and 'standard_hours_per_day' not in res:
            res['standard_hours_per_day'] = company.standard_hours_per_day or 8.0
        if 'overtime_multiplier' in fields_list and 'overtime_multiplier' not in res:
            res['overtime_multiplier'] = company.overtime_multiplier or 1.0
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            wage = vals.get('wage', 0.0)
            
            # Fetch divisor values from vals or default to company-level defaults
            days = vals.get('standard_working_days_per_month')
            if days is None:
                days = self.env.company.standard_working_days_per_month or 26.0
            hours = vals.get('standard_hours_per_day')
            if hours is None:
                hours = self.env.company.standard_hours_per_day or 8.0
            mult = vals.get('overtime_multiplier')
            if mult is None:
                mult = self.env.company.overtime_multiplier or 1.0
                
            divisor = days * hours
            hourly = wage / divisor if divisor else 0.0
            
            # Determine if overtime rate is custom
            if 'overtime_rate_per_hour' in vals and vals.get('overtime_rate_per_hour') != 0.0:
                if abs(vals['overtime_rate_per_hour'] - (hourly * mult)) > 0.01:
                    vals['overtime_rate_manually_set'] = True
            else:
                vals['overtime_rate_per_hour'] = hourly * mult
                vals['overtime_rate_manually_set'] = False

            # Determine if shortage rate is custom
            if 'shortage_deduction_rate_per_hour' in vals and vals.get('shortage_deduction_rate_per_hour') != 0.0:
                if abs(vals['shortage_deduction_rate_per_hour'] - hourly) > 0.01:
                    vals['shortage_rate_manually_set'] = True
            else:
                vals['shortage_deduction_rate_per_hour'] = hourly
                vals['shortage_rate_manually_set'] = False
                
        return super(HrVersion, self).create(vals_list)

    def write(self, vals):
        for rec in self:
            local_vals = vals.copy()
            
            wage = local_vals.get('wage', rec.wage)
            days = local_vals.get('standard_working_days_per_month', rec.standard_working_days_per_month)
            hours = local_vals.get('standard_hours_per_day', rec.standard_hours_per_day)
            mult = local_vals.get('overtime_multiplier', rec.overtime_multiplier)
            
            divisor = days * hours
            computed_hourly = wage / divisor if divisor else 0.0
            
            # Check for manual edits to Overtime Rate
            if 'overtime_rate_per_hour' in local_vals:
                expected_ot = computed_hourly * mult
                if abs(local_vals['overtime_rate_per_hour'] - expected_ot) > 0.01:
                    local_vals['overtime_rate_manually_set'] = True
                else:
                    local_vals['overtime_rate_manually_set'] = False
            elif any(k in local_vals for k in ['wage', 'standard_working_days_per_month', 'standard_hours_per_day', 'overtime_multiplier']):
                # Auto-update if config changes and NOT custom
                if not rec.overtime_rate_manually_set:
                    local_vals['overtime_rate_per_hour'] = computed_hourly * mult

            # Check for manual edits to Shortage Rate
            if 'shortage_deduction_rate_per_hour' in local_vals:
                if abs(local_vals['shortage_deduction_rate_per_hour'] - computed_hourly) > 0.01:
                    local_vals['shortage_rate_manually_set'] = True
                else:
                    local_vals['shortage_rate_manually_set'] = False
            elif any(k in local_vals for k in ['wage', 'standard_working_days_per_month', 'standard_hours_per_day']):
                # Auto-update if config changes and NOT custom
                if not rec.shortage_rate_manually_set:
                    local_vals['shortage_deduction_rate_per_hour'] = computed_hourly
                    
            super(HrVersion, rec).write(local_vals)
        return True

    @api.depends('wage', 'standard_working_days_per_month', 'standard_hours_per_day')
    def _compute_hourly_rate(self):
        for rec in self:
            divisor = rec.standard_working_days_per_month * rec.standard_hours_per_day
            rec.hourly_rate = rec.wage / divisor if divisor else 0.0

    @api.depends('hourly_rate', 'overtime_multiplier')
    def _compute_overtime_hourly_rate(self):
        for rec in self:
            rec.overtime_hourly_rate = rec.hourly_rate * rec.overtime_multiplier

    @api.depends('overtime_hourly_rate', 'overtime_rate_manually_set')
    def _compute_overtime_rate_per_hour(self):
        for rec in self:
            if not rec.overtime_rate_manually_set:
                rec.overtime_rate_per_hour = rec.overtime_hourly_rate
            else:
                rec.overtime_rate_per_hour = rec.overtime_rate_per_hour or 0.0

    @api.depends('hourly_rate', 'shortage_rate_manually_set')
    def _compute_shortage_deduction_rate_per_hour(self):
        for rec in self:
            if not rec.shortage_rate_manually_set:
                rec.shortage_deduction_rate_per_hour = rec.hourly_rate
            else:
                rec.shortage_deduction_rate_per_hour = rec.shortage_deduction_rate_per_hour or 0.0

    @api.onchange('overtime_rate_per_hour')
    def _onchange_overtime_rate_per_hour(self):
        for rec in self:
            if rec.overtime_hourly_rate and abs(rec.overtime_rate_per_hour - rec.overtime_hourly_rate) > 0.01:
                rec.overtime_rate_manually_set = True

    @api.onchange('shortage_deduction_rate_per_hour')
    def _onchange_shortage_deduction_rate_per_hour(self):
        for rec in self:
            if rec.hourly_rate and abs(rec.shortage_deduction_rate_per_hour - rec.hourly_rate) > 0.01:
                rec.shortage_rate_manually_set = True

    @api.onchange('wage', 'standard_working_days_per_month', 'standard_hours_per_day', 'overtime_multiplier')
    def _onchange_hourly_rate_config(self):
        for rec in self:
            divisor = rec.standard_working_days_per_month * rec.standard_hours_per_day
            computed_hourly = rec.wage / divisor if divisor else 0.0
            rec.hourly_rate = computed_hourly
            rec.overtime_hourly_rate = computed_hourly * rec.overtime_multiplier
            
            if not rec.overtime_rate_manually_set:
                rec.overtime_rate_per_hour = computed_hourly * rec.overtime_multiplier
            if not rec.shortage_rate_manually_set:
                rec.shortage_deduction_rate_per_hour = computed_hourly

    def action_reset_to_computed_rates(self):
        for rec in self:
            divisor = rec.standard_working_days_per_month * rec.standard_hours_per_day
            computed_hourly = rec.wage / divisor if divisor else 0.0
            rec.write({
                'overtime_rate_manually_set': False,
                'shortage_rate_manually_set': False,
                'overtime_rate_per_hour': computed_hourly * rec.overtime_multiplier,
                'shortage_deduction_rate_per_hour': computed_hourly,
            })
