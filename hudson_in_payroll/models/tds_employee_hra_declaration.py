# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TdsEmployeeHraDeclaration(models.Model):
    """
    Dedicated House Rent Allowance (HRA / Section 10(13A)) Declaration Model.
    Provides a standalone form window matching the Housing Loan form layout for Rent Paid,
    Landlord Name, Landlord PAN, Landlord Address, and Metro/Non-Metro City status.
    """
    _name = 'tds.employee.hra.declaration'
    _description = 'House Rent Allowance (HRA) Declaration'
    _order = 'financial_year_id desc, employee_id, id'
    _sql_constraints = [
        ('emp_fy_hra_uniq', 'unique(employee_id, financial_year_id)',
         'An employee can have only one HRA Declaration per Financial Year!')
    ]

    name = fields.Char(
        string="Declaration Reference",
        compute='_compute_name',
        store=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True,
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        related='employee_id.company_id',
        store=True,
        readonly=True
    )
    financial_year_id = fields.Many2one(
        'tds.financial.year',
        string="Financial Year",
        required=True,
        ondelete='restrict'
    )
    tax_regime_id = fields.Many2one(
        'tds.tax.regime',
        string="Applied Tax Regime",
        compute='_compute_tax_regime_id',
        store=True,
        readonly=True
    )
    regime_code = fields.Selection(
        related='tax_regime_id.code',
        string="Regime Code",
        store=True,
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('declared', 'Declared'),
        ('submitted', 'Submitted'),
        ('proof_submitted', 'Proof Submitted'),
        ('proof_under_review', 'Proof Under Review'),
        ('proof_verified', 'Proof Verified'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="Declaration Status", default='draft', required=True, tracking=True)

    submission_date = fields.Date(string="Submission Date", readonly=True)
    approval_date = fields.Date(string="Approval Date", readonly=True)
    approved_by_id = fields.Many2one('res.users', string="Approved By", readonly=True)
    rejection_reason = fields.Text(string="Rejection Reason")

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    # -------------------------------------------------------------------------
    # HRA SPECIFIED FIELDS
    # -------------------------------------------------------------------------
    annual_rent_paid = fields.Monetary(
        string="Annual Rent Paid (₹)",
        currency_field='currency_id',
        default=0.0,
        required=True,
        help="Total annual rent paid by employee for residential accommodation."
    )
    monthly_rent_paid = fields.Monetary(
        string="Monthly Rent Equivalent (₹)",
        currency_field='currency_id',
        compute='_compute_monthly_rent',
        store=True
    )
    is_metro_city = fields.Boolean(
        string="Rented House in Metro City?",
        default=False,
        help="Check if house is located in Mumbai, Delhi, Kolkata, or Chennai (50% Basic salary statutory cap vs 40% non-metro)."
    )
    landlord_name = fields.Char(
        string="Landlord Full Name",
        help="Full legal name of the landlord."
    )
    landlord_pan = fields.Char(
        string="Landlord PAN Number",
        help="10-character PAN number of landlord. Mandatory if annual rent exceeds ₹1,00,000."
    )
    landlord_address = fields.Text(
        string="Rented Accommodation Address",
        help="Complete residential address of rented premises."
    )
    is_pan_required = fields.Boolean(
        string="Is PAN Required?",
        compute='_compute_is_pan_required',
        store=True
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tds_hra_decl_ir_attachment_rel',
        'decl_id',
        'attachment_id',
        string="Rent Receipts / Rent Agreement"
    )

    @api.depends('employee_id', 'financial_year_id')
    def _compute_name(self):
        for rec in self:
            emp_name = rec.employee_id.name if rec.employee_id else "New"
            fy_name = rec.financial_year_id.name if rec.financial_year_id else ""
            rec.name = f"HRA Declaration - {emp_name} [{fy_name}]"

    @api.depends('employee_id', 'financial_year_id')
    def _compute_tax_regime_id(self):
        for rec in self:
            if rec.employee_id and rec.financial_year_id:
                regime_rec = self.env['tds.employee.tax.regime'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('financial_year_id', '=', rec.financial_year_id.id)
                ], limit=1)
                rec.tax_regime_id = regime_rec.regime_id.id if regime_rec else False
            else:
                rec.tax_regime_id = False

    @api.depends('annual_rent_paid')
    def _compute_monthly_rent(self):
        for rec in self:
            rec.monthly_rent_paid = (rec.annual_rent_paid or 0.0) / 12.0

    @api.depends('annual_rent_paid')
    def _compute_is_pan_required(self):
        for rec in self:
            rec.is_pan_required = (rec.annual_rent_paid or 0.0) > 100000.0

    @api.constrains('annual_rent_paid', 'landlord_pan')
    def _check_landlord_pan(self):
        for rec in self:
            if rec.annual_rent_paid > 100000.0 and not rec.landlord_pan:
                raise ValidationError(_("Landlord PAN Number is mandatory when annual rent paid exceeds ₹1,00,000."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_to_central_declaration()
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._sync_to_central_declaration()
        return res

    def _sync_to_central_declaration(self):
        """Sync HRA fields with central tds.employee.declaration master."""
        for rec in self:
            if not rec.employee_id or not rec.financial_year_id:
                continue
            decl = self.env['tds.employee.declaration'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('financial_year_id', '=', rec.financial_year_id.id)
            ], limit=1)
            if not decl:
                decl = self.env['tds.employee.declaration'].sudo().create({
                    'employee_id': rec.employee_id.id,
                    'financial_year_id': rec.financial_year_id.id,
                    'state': rec.state if rec.state in ['draft', 'declared', 'submitted', 'proof_submitted', 'proof_under_review', 'proof_verified', 'approved', 'rejected'] else 'draft',
                })
            
            decl.sudo().write({
                'decl_hra_annual_rent': rec.annual_rent_paid,
                'decl_hra_is_metro': rec.is_metro_city,
                'decl_hra_landlord_name': rec.landlord_name,
                'decl_hra_landlord_pan': rec.landlord_pan,
                'decl_hra_landlord_address': rec.landlord_address,
            })

    def action_submit_declaration(self):
        self.write({'state': 'declared', 'submission_date': fields.Date.today()})
        self._sync_to_central_declaration()

    def action_submit(self):
        return self.action_submit_declaration()

    def action_submit_proofs(self):
        self.write({'state': 'proof_submitted'})
        self._sync_to_central_declaration()

    def action_start_review(self):
        self.write({'state': 'proof_under_review'})
        self._sync_to_central_declaration()

    def action_verify_proofs(self):
        self.write({'state': 'proof_verified', 'approval_date': fields.Date.today(), 'approved_by_id': self.env.user.id})
        self._sync_to_central_declaration()

    def action_approve(self):
        return self.action_verify_proofs()

    def action_reject(self):
        if not self.rejection_reason:
            raise ValidationError(_("Please enter a Rejection Reason before rejecting."))
        self.write({'state': 'rejected'})
        self._sync_to_central_declaration()

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._sync_to_central_declaration()
