# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HdsInBonus(models.Model):
    _name = 'hds.in.bonus'
    _description = 'Bonus Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string="Bonus Name",
        required=True,
        tracking=True,
        help="Description or title of the bonus document (e.g. Diwali Bonus 2026)."
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    bonus_type = fields.Selection([
        ('festival', 'Festival Bonus'),
        ('annual', 'Annual Bonus'),
        ('performance', 'Performance Bonus'),
        ('ex_gratia', 'Ex-gratia'),
        ('custom', 'Custom'),
    ], string="Bonus Type", required=True, default='festival', tracking=True)

    date_from = fields.Date(
        string="Period From",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help="Start date of the bonus payroll period."
    )
    date_to = fields.Date(
        string="Period To",
        required=True,
        default=lambda self: fields.Date.today(),
        help="End date of the bonus payroll period."
    )
    payment_date = fields.Date(
        string="Payment Date",
        required=True,
        default=fields.Date.today,
        tracking=True,
        help="Scheduled date for bonus payment."
    )
    payment_method = fields.Selection([
        ('monthly_payroll', 'Include in Monthly Payroll'),
        ('separate_payroll', 'Separate Bonus Payroll'),
    ], string="Payment Method", required=True, default='monthly_payroll', tracking=True)

    notes = fields.Text(string="Notes")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string="Status", default='draft', tracking=True, copy=False)

    # Employee Selection Criteria
    employee_selection_type = fields.Selection([
        ('employee', 'Individual Employee'),
        ('department', 'Department'),
        ('job', 'Job Position'),
        ('company', 'Company'),
        ('all', 'All Employees'),
    ], string="Target Employees", default='all', required=True)

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        domain="[('company_id', '=', company_id)]"
    )
    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        domain="[('company_id', '=', company_id)]"
    )
    job_id = fields.Many2one(
        'hr.job',
        string="Job Position",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    target_company_id = fields.Many2one(
        'res.company',
        string="Target Company",
        default=lambda self: self.env.company
    )

    # Bonus Calculation Criteria
    calculation_method = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage_basic', 'Percentage of Basic'),
        ('percentage_gross', 'Percentage of Gross'),
    ], string="Calculation Method", default='fixed', required=True)

    fixed_amount = fields.Monetary(
        string="Fixed Amount",
        currency_field='currency_id',
        default=0.0
    )
    percentage = fields.Float(
        string="Percentage (%)",
        default=0.0,
        help="Percentage to apply against Basic or Gross salary."
    )

    line_ids = fields.One2many(
        'hds.in.bonus.line',
        'bonus_id',
        string="Bonus Lines",
        copy=True
    )

    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string="Payslip Batch",
        readonly=True,
        copy=False,
        help="Linked Payslip Batch created when Separate Bonus Payroll is processed."
    )

    payslip_count = fields.Integer(
        string="Payslips Count",
        compute='_compute_payslip_count'
    )

    @api.depends('line_ids.payslip_id', 'payslip_run_id')
    def _compute_payslip_count(self):
        for record in self:
            payslips = record.line_ids.mapped('payslip_id')
            if record.payslip_run_id:
                payslips |= record.payslip_run_id.slip_ids
            record.payslip_count = len(payslips)

    def action_view_payslips(self):
        self.ensure_one()
        payslips = self.line_ids.mapped('payslip_id')
        if self.payslip_run_id:
            payslips |= self.payslip_run_id.slip_ids
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll_community.action_view_hr_payslip_form")
        if len(payslips) > 1:
            action['domain'] = [('id', 'in', payslips.ids)]
        elif len(payslips) == 1:
            form_view = [(self.env.ref('hr_payroll_community.hr_payslip_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [v for v in action['views'] if v[1] != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = payslips.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_generate_lines(self):
        """Automatically find eligible employees and create Bonus Lines."""
        self.ensure_one()
        if self.state not in ('draft', 'submitted'):
            raise UserError(_("You can only generate lines for Draft or Submitted bonus documents."))

        # Determine target employees
        domain = [('company_id', '=', self.company_id.id)]
        if self.employee_selection_type == 'employee':
            if not self.employee_id:
                raise UserError(_("Please select an employee."))
            domain = [('id', '=', self.employee_id.id)]
        elif self.employee_selection_type == 'department':
            if not self.department_id:
                raise UserError(_("Please select a department."))
            domain.append(('department_id', '=', self.department_id.id))
        elif self.employee_selection_type == 'job':
            if not self.job_id:
                raise UserError(_("Please select a job position."))
            domain.append(('job_id', '=', self.job_id.id))
        elif self.employee_selection_type == 'company':
            target_comp = self.target_company_id or self.company_id
            domain = [('company_id', '=', target_comp.id)]
        elif self.employee_selection_type == 'all':
            domain = [('company_id', '=', self.company_id.id)]

        employees = self.env['hr.employee'].search(domain)
        if not employees:
            raise UserError(_("No employees found matching the specified selection criteria."))

        # Recreate bonus lines
        self.line_ids.unlink()
        line_vals = []

        for emp in employees:
            # Find running contract
            contract = self.env['hr.version'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'open')
            ], limit=1)
            if not contract:
                contract = self.env['hr.version'].search([
                    ('employee_id', '=', emp.id)
                ], order='id desc', limit=1)

            amount = 0.0
            if self.calculation_method == 'fixed':
                amount = self.fixed_amount
            elif self.calculation_method == 'percentage_basic':
                base_basic = float(contract.basic_salary or contract.wage or 0.0) if contract else 0.0
                amount = round(base_basic * (self.percentage / 100.0), 2)
            elif self.calculation_method == 'percentage_gross':
                base_gross = float(contract.wage or 0.0) if contract else 0.0
                amount = round(base_gross * (self.percentage / 100.0), 2)

            line_vals.append({
                'bonus_id': self.id,
                'employee_id': emp.id,
                'contract_id': contract.id if contract else False,
                'amount': amount,
            })

        self.env['hds.in.bonus.line'].create(line_vals)
        return True

    # Workflow Actions
    def action_submit(self):
        for record in self:
            if not record.line_ids:
                record.action_generate_lines()
            record.write({'state': 'submitted'})
        return True

    def action_approve(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("Cannot approve a bonus document without bonus lines."))
            record.write({'state': 'approved'})
        return True

    def action_reject(self):
        for record in self:
            record.write({'state': 'cancelled'})
        return True

    def action_cancel(self):
        for record in self:
            if record.state in ('processed', 'paid'):
                raise UserError(_("You cannot cancel a processed or paid bonus."))
            record.write({'state': 'cancelled'})
        return True

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})
        return True

    def action_process_bonus(self):
        """Process Approved Bonus document into Payroll inputs or Separate Bonus Payslips."""
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Only Approved bonuses can be processed."))
            if not record.line_ids:
                raise UserError(_("No bonus lines found to process."))

            valid_lines = record.line_ids.filtered(lambda l: l.amount > 0.0)
            if not valid_lines:
                raise UserError(_("All bonus lines have 0 amount."))

            if record.payment_method == 'monthly_payroll':
                record._process_monthly_payroll(valid_lines)
            elif record.payment_method == 'separate_payroll':
                record._process_separate_payroll(valid_lines)

            record.write({'state': 'processed'})
        return True

    def _process_monthly_payroll(self, lines):
        """Option 1: Include in Monthly Payroll - generates/updates BONUS inputs on draft payslips."""
        for line in lines:
            if not line.contract_id:
                continue
            # Search existing draft payslip for employee within period
            payslips = self.env['hr.payslip'].search([
                ('employee_id', '=', line.employee_id.id),
                ('state', '=', 'draft'),
                ('date_from', '<=', self.payment_date),
                ('date_to', '>=', self.payment_date),
            ])
            for payslip in payslips:
                input_line = payslip.input_line_ids.filtered(lambda i: i.code == 'BONUS')
                if input_line:
                    input_line.write({'amount': line.amount, 'name': self.name})
                else:
                    self.env['hr.payslip.input'].create({
                        'name': self.name,
                        'code': 'BONUS',
                        'amount': line.amount,
                        'payslip_id': payslip.id,
                        'contract_id': line.contract_id.id,
                        'date_from': self.date_from,
                        'date_to': self.date_to,
                    })

    def _process_separate_payroll(self, lines):
        """Option 2: Separate Bonus Payroll - creates Payslip Batch and Bonus Payslips."""
        # 1. Get or fallback Bonus Salary Structure
        struct = self.company_id.hds_in_bonus_struct_id
        if not struct:
            struct = self.env.ref('hudson_in_payroll.hds_in_structure_bonus', raise_if_not_found=False)
        if not struct:
            struct = self.env['hr.payroll.structure'].search([('code', '=', 'BONUS_STRUCT')], limit=1)
        if not struct:
            raise UserError(_("No Bonus Payroll Structure configured in Payroll Settings or XML data."))

        # 2. Create Payslip Batch
        batch = self.env['hr.payslip.run'].create({
            'name': f"{self.name} - Bonus Payroll",
            'date_start': self.date_from,
            'date_end': self.date_to,
        })
        self.payslip_run_id = batch.id

        # 3. Create Payslips
        for line in lines:
            if not line.contract_id:
                continue
            payslip = self.env['hr.payslip'].create({
                'name': f"Bonus Slip - {line.employee_id.name}",
                'employee_id': line.employee_id.id,
                'contract_id': line.contract_id.id,
                'struct_id': struct.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'payslip_run_id': batch.id,
                'company_id': self.company_id.id,
                'input_line_ids': [(0, 0, {
                    'name': self.name,
                    'code': 'BONUS',
                    'amount': line.amount,
                    'contract_id': line.contract_id.id,
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                })]
            })
            line.payslip_id = payslip.id


class HdsInBonusLine(models.Model):
    _name = 'hds.in.bonus.line'
    _description = 'Bonus Document Line'
    _order = 'bonus_id, id'

    bonus_id = fields.Many2one(
        'hds.in.bonus',
        string="Bonus Document",
        required=True,
        ondelete='cascade',
        index=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True
    )
    contract_id = fields.Many2one(
        'hr.version',
        string="Contract"
    )
    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        string="Department",
        store=True
    )
    job_id = fields.Many2one(
        'hr.job',
        related='employee_id.job_id',
        string="Job Position",
        store=True
    )
    amount = fields.Monetary(
        string="Bonus Amount",
        currency_field='currency_id',
        required=True,
        default=0.0
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='bonus_id.currency_id',
        store=True,
        readonly=True
    )
    state = fields.Selection(
        related='bonus_id.state',
        string="Status",
        store=True
    )
    payslip_id = fields.Many2one(
        'hr.payslip',
        string="Payslip",
        readonly=True
    )
