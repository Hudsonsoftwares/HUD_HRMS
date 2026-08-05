# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TdsEmployeeDeclarationLine(models.Model):
    """
    TDS Employee Tax Declaration Line Item Model.
    Captures individual investment proofs, Section 10 exemptions, and Chapter VI-A deduction line items.
    Enforces regime compatibility and statutory ceiling calculations.
    """
    _name = 'tds.employee.declaration.line'
    _description = 'Employee Tax Declaration Line Item'
    _order = 'declaration_id, category, id'

    declaration_id = fields.Many2one(
        'tds.employee.declaration',
        string="Declaration Header",
        required=True,
        ondelete='cascade',
        help="Parent declaration header."
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        related='declaration_id.employee_id',
        store=True,
        readonly=True
    )
    financial_year_id = fields.Many2one(
        'tds.financial.year',
        string="Financial Year",
        related='declaration_id.financial_year_id',
        store=True,
        readonly=True
    )
    regime_code = fields.Selection(
        related='declaration_id.regime_code',
        string="Regime Code",
        store=True,
        readonly=True
    )
    category = fields.Selection([
        ('80c', 'Section 80C (PPF, ELSS, LIC, Tuition Fee, EPF)'),
        ('80ccd1b', 'Section 80CCD(1B) Additional NPS Contribution'),
        ('80d_self', 'Section 80D Medical Insurance (Self & Family)'),
        ('80d_parents', 'Section 80D Medical Insurance (Parents)'),
        ('80d_preventive', 'Section 80D Preventive Health Checkup'),
        ('80tta', 'Section 80TTA Savings Interest (Non-Senior)'),
        ('80ttb', 'Section 80TTB Savings & FD Interest (Senior Citizen)'),
        ('80dd', 'Section 80DD Dependent Disability'),
        ('24b', 'Section 24(b) Home Loan Interest (Self-Occupied)'),
        ('80eea', 'Section 80EEA First-time Home Loan Additional Interest'),
        ('hra', 'Section 10(13A) House Rent Exemption (Rent Paid)'),
        ('children_edu', 'Section 10(14) Children Education Allowance'),
        ('hostel', 'Section 10(14) Hostel Expenditure Allowance'),
        ('lta', 'Section 10(5) Leave Travel Assistance (LTA)'),
        ('nps_employee', 'Section 80CCD(1) Employee NPS Contribution'),
        ('80ccd2', 'Section 80CCD(2) Employer NPS Contribution (Both Regimes)'),
        ('57iia', 'Section 57(iia) Family Pension Deduction (Both Regimes)'),
        ('80cch', 'Section 80CCH Agniveer Corpus Fund Contribution (Both Regimes)'),
        ('leave_encashment', 'Section 10(10AA) Leave Encashment Exemption'),
        ('vrs', 'Section 10(10C) VRS Compensation Exemption'),
        ('other', 'Other Statutory Exemptions'),
    ], string="Declaration Category", required=True)


    section_code = fields.Char(
        string="Statutory Section Code",
        compute='_compute_section_code',
        store=True,
        help="Automated section code designation."
    )
    description = fields.Char(
        string="Investment Particulars / Description",
        required=True,
        help="Detailed description of investment or claim (e.g. LIC Policy #98765, Rent Paid to Landlord)."
    )
    declared_amount = fields.Monetary(
        string="Declared Amount (₹)",
        currency_field='currency_id',
        required=True,
        default=0.0,
        help="Amount declared by employee."
    )
    is_senior_citizen = fields.Boolean(
        string="Insured Person is Senior Citizen (Age ≥ 60)",
        default=False,
        help="Mark True if the insured person (Self/Spouse or Parents) is a Senior Citizen (Age 60+), unlocking higher Section 80D statutory limits."
    )
    is_severe_disability = fields.Boolean(
        string="Severe Disability (Disability ≥ 80%)",
        default=False,
        help="Mark True if dependent disability is 80% or higher, unlocking higher Section 80DD statutory ceiling of ₹1,25,000."
    )

    verified_amount = fields.Monetary(
        string="Verified Amount (₹)",
        currency_field='currency_id',
        default=0.0,
        help="Amount verified by HR after proof document inspection."
    )

    approved_amount = fields.Monetary(
        string="Approved Statutory Deduction (₹)",
        currency_field='currency_id',
        default=0.0,
        help="Final statutory deduction allowed after ceiling cap and regime validation."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='declaration_id.currency_id',
        readonly=True
    )
    is_regime_permitted = fields.Boolean(
        string="Regime Permitted",
        default=True,
        help="True if deduction category is permitted under the employee's selected tax regime."
    )
    validation_status = fields.Selection([
        ('valid', 'Statutory Valid'),
        ('exceeds_limit', 'Exceeds Statutory Limit (Capped)'),
        ('ineligible_regime', 'Not Permitted Under New Regime'),
        ('pending_proof', 'Pending Document Proof'),
    ], string="Validation Status", default='valid', required=True)

    validation_remarks = fields.Text(
        string="Validation Remarks",
        help="Audit trail explaining statutory capping or regime rejection reasons."
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tds_declaration_line_ir_attachment_rel',
        'line_id',
        'attachment_id',
        string="Supporting Document Proofs",
        help="Proof receipts attached specifically for this investment line item."
    )

    @api.depends('category')
    def _compute_section_code(self):
        code_map = {
            '80c': 'Sec 80C',
            '80ccd1b': 'Sec 80CCD(1B)',
            '80d_self': 'Sec 80D (Self)',
            '80d_parents': 'Sec 80D (Parents)',
            '80d_preventive': 'Sec 80D (Preventive)',
            '80tta': 'Sec 80TTA',
            '80ttb': 'Sec 80TTB',
            '80dd': 'Sec 80DD',
            '24b': 'Sec 24(b)',
            '80eea': 'Sec 80EEA',
            'hra': 'Sec 10(13A)',
            'children_edu': 'Sec 10(14)',
            'hostel': 'Sec 10(14)',
            'lta': 'Sec 10(5)',
            'nps_employee': 'Sec 80CCD(1)',
            'leave_encashment': 'Sec 10(10AA)',
            'vrs': 'Sec 10(10C)',
            'other': 'Other',
        }
        for line in self:
            line.section_code = code_map.get(line.category, 'General')
