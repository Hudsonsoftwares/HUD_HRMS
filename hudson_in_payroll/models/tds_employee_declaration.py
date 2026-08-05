# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class TdsEmployeeDeclaration(models.Model):
    """
    TDS Employee Tax Declaration Header Model.
    Captures annual employee tax investment proofs and Section 10 / Chapter VI-A statutory exemption declarations.
    Enforces multi-stage approval workflow (Draft -> Submitted -> Under Review -> Approved / Rejected).
    Only APPROVED declarations are consumed by downstream TDS calculation engines.
    """
    _name = 'tds.employee.declaration'
    _description = 'Employee Annual Tax Declaration Header'
    _order = 'financial_year_id desc, employee_id, id'
    _sql_constraints = [
        ('emp_fy_decl_uniq', 'unique(employee_id, financial_year_id)',
         'An employee can have only one Tax Declaration header per Financial Year!')
    ]

    name = fields.Char(
        string="Declaration Reference",
        compute='_compute_name',
        store=True,
        help="Automated declaration title."
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        ondelete='cascade',
        help="Target employee submitting tax declaration."
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        related='employee_id.company_id',
        store=True,
        readonly=True
    )
    @api.model
    def _default_financial_year_id(self):
        company = self.env.company
        if company and company.hds_in_default_tax_year:
            return company.hds_in_default_tax_year.id
        today = fields.Date.today()
        fy = self.env['tds.financial.year'].search([
            ('start_date', '<=', today),
            ('end_date', '>=', today),
            ('active', '=', True),
            ('is_closed', '=', False)
        ], limit=1)
        return fy.id if fy else False

    financial_year_id = fields.Many2one(
        'tds.financial.year',
        string="Financial Year",
        required=True,
        default=_default_financial_year_id,
        ondelete='restrict',
        help="Target Financial Year for investment declarations."
    )

    tax_regime_id = fields.Many2one(
        'tds.tax.regime',
        string="Applied Tax Regime",
        compute='_compute_tax_regime_id',
        store=True,
        readonly=True,
        help="Active Tax Regime for this employee in the selected Financial Year."
    )
    regime_code = fields.Selection(
        related='tax_regime_id.code',
        string="Regime Code",
        store=True,
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="Declaration Status", default='draft', required=True, tracking=True)

    submission_date = fields.Date(
        string="Submission Date",
        readonly=True,
        help="Date when employee submitted declaration."
    )
    approval_date = fields.Date(
        string="Approval Date",
        readonly=True,
        help="Date when Payroll Manager approved declaration."
    )
    approved_by_id = fields.Many2one(
        'res.users',
        string="Approved By",
        readonly=True,
        help="Payroll Officer/Manager who approved declaration."
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        help="Detailed reason for declaration rejection."
    )

    total_declared_amount = fields.Monetary(
        string="Total Declared Amount (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help="Sum of all declared investment amounts across lines."
    )
    total_approved_amount = fields.Monetary(
        string="Total Approved Amount (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help="Sum of all approved statutory exemption amounts across lines."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        readonly=True
    )

    declaration_line_ids = fields.One2many(
        'tds.employee.declaration.line',
        'declaration_id',
        string="Declaration Items",
        copy=True
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tds_declaration_ir_attachment_rel',
        'declaration_id',
        'attachment_id',
        string="Supporting Proof Documents",
        help="Uploaded investment receipts, rent receipts, insurance statements, and tax certificates."
    )
    active = fields.Boolean(
        string="Active",
        default=True
    )

    @api.depends('employee_id.name', 'financial_year_id.name', 'regime_code')
    def _compute_name(self):
        for rec in self:
            emp = rec.employee_id.name if rec.employee_id else 'Employee'
            fy = rec.financial_year_id.name if rec.financial_year_id else 'FY'
            reg = (rec.regime_code or 'regime').upper()
            rec.name = f"Tax Declaration - {emp} [{fy}] ({reg})"

    @api.depends('employee_id', 'financial_year_id')
    def _compute_tax_regime_id(self):
        """
        Dynamically resolves active tax regime from tds.employee.tax.regime history for employee + FY.
        Defaults to company default regime if explicit selection not found.
        """
        for rec in self:
            if rec.employee_id and rec.financial_year_id:
                reg_record = self.env['tds.employee.tax.regime'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('financial_year_id', '=', rec.financial_year_id.id),
                ], limit=1)
                if reg_record:
                    rec.tax_regime_id = reg_record.regime_id
                    continue

            # Fallback to default regime master
            default_reg = self.env['tds.tax.regime'].search([('is_default', '=', True)], limit=1)
            rec.tax_regime_id = default_reg.id if default_reg else False

    @api.depends('declaration_line_ids.declared_amount', 'declaration_line_ids.approved_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_declared_amount = sum(line.declared_amount for line in rec.declaration_line_ids)
            rec.total_approved_amount = sum(line.approved_amount for line in rec.declaration_line_ids)

    def action_validate_declaration_rules(self):
        """
        Invokes EmployeeTaxDeclarationValidationService to perform regime-aware line item validations.
        """
        for rec in self:
            from ..services.tds.employee_tax_declaration_validation_service import EmployeeTaxDeclarationValidationService
            val_svc = EmployeeTaxDeclarationValidationService(self.env)
            val_svc.validate_declaration(rec)

    def action_submit(self):
        """Transition from Draft to Submitted."""
        for rec in self:
            if not rec.declaration_line_ids:
                raise ValidationError(_("Cannot submit an empty tax declaration with no line items."))
            rec.action_validate_declaration_rules()
            rec.write({
                'state': 'submitted',
                'submission_date': fields.Date.today(),
            })

    def action_review(self):
        """Transition from Submitted to Under Review."""
        self.write({'state': 'under_review'})

    def action_approve(self):
        """Transition to Approved."""
        for rec in self:
            rec.action_validate_declaration_rules()
            rec.write({
                'state': 'approved',
                'approval_date': fields.Date.today(),
                'approved_by_id': self.env.user.id,
            })
            # Log audit entry
            if 'hds.in.payroll.audit' in self.env:
                self.env['hds.in.payroll.audit'].create({
                    'name': f"Tax Declaration Approved: {rec.name}",
                    'employee_id': rec.employee_id.id,
                    'company_id': rec.company_id.id,
                    'audit_type': 'status_change',
                    'action_taken': f"Tax Declaration for FY {rec.financial_year_id.name} Approved.",
                    'remarks': f"Total Declared: ₹{rec.total_declared_amount:,.2f}, Total Approved: ₹{rec.total_approved_amount:,.2f}.",
                })

    def action_reject(self):
        """Transition to Rejected."""
        for rec in self:
            if not rec.rejection_reason:
                raise ValidationError(_("Please provide a Rejection Reason before rejecting the declaration."))
            rec.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        """Reset back to Draft state."""
        self.write({'state': 'draft'})
