import logging
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

DECLARATION_BUSINESS_REGISTRY = [
    # Section 80C
    {'category': '80c', 'field_name': 'decl_80c_ppf', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_elss', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_epf', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_lic', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_nsc', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_ssy', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_fd', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_tuition', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_housing_principal', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80c', 'field_name': 'decl_80c_other', 'statutory_section': 'Section 80C', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80C_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    # Section 80CCD(1B)
    {'category': '80ccd1b', 'field_name': 'decl_80ccd1b_nps', 'statutory_section': 'Section 80CCD(1B)', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80CCD1B_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    # Section 80D
    {'category': '80d_self', 'field_name': 'decl_80d_self', 'statutory_section': 'Section 80D', 'eligibility_strategy': 'MEDICAL_INSURANCE_SELF_BUCKET', 'parameter_code': 'HDS_IN_TDS_80D_SELF_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80d_parents', 'field_name': 'decl_80d_parents', 'statutory_section': 'Section 80D', 'eligibility_strategy': 'MEDICAL_INSURANCE_PARENTS_BUCKET', 'parameter_code': 'HDS_IN_TDS_80D_PARENTS_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'is_senior_field': 'decl_80d_parents_is_senior', 'deduction_group': 'chapter6a'},
    {'category': '80d_preventive', 'field_name': 'decl_80d_preventive', 'statutory_section': 'Section 80D', 'eligibility_strategy': 'PREVENTIVE_CHECKUP_SUB_LIMIT', 'parameter_code': 'HDS_IN_TDS_80D_PREVENTIVE_CHECKUP_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    # Section 24(b) & Section 80EEA
    {'category': '24b', 'field_name': 'decl_24b_self_interest', 'alt_field_name': 'decl_home_loan_interest', 'statutory_section': 'Section 24(b)', 'eligibility_strategy': 'HOME_LOAN_INTEREST', 'parameter_code': 'HDS_IN_TDS_24B_HOME_LOAN_INTEREST_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'home_loan'},
    {'category': '80eea', 'field_name': 'decl_80eea_interest', 'statutory_section': 'Section 80EEA', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80EEA_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'home_loan'},
    # Section 10(13A) HRA
    {'category': 'hra', 'field_name': 'decl_hra_annual_rent', 'statutory_section': 'Section 10(13A)', 'eligibility_strategy': 'HRA_EXEMPTION', 'parameter_code': 'HDS_IN_TDS_HRA_METRO_PERCENT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'hra'},
    # Other Chapter VI-A
    {'category': '80tta', 'field_name': 'decl_80tta_interest', 'statutory_section': 'Section 80TTA', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80TTA_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80ttb', 'field_name': 'decl_80ttb_interest', 'statutory_section': 'Section 80TTB', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80TTB_MAX_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80e', 'field_name': 'decl_80e_interest', 'statutory_section': 'Section 80E', 'eligibility_strategy': 'UNLIMITED', 'parameter_code': None, 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80g', 'field_name': 'decl_80g_donation', 'statutory_section': 'Section 80G', 'eligibility_strategy': 'UNLIMITED', 'parameter_code': None, 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80gg', 'field_name': 'decl_80gg_rent', 'statutory_section': 'Section 80GG', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80GG_MAX_MONTHLY_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    {'category': '80dd', 'field_name': 'decl_80dd_amount', 'statutory_section': 'Section 80DD', 'eligibility_strategy': 'CAP_LIMIT', 'parameter_code': 'HDS_IN_TDS_80DD_NORMAL_LIMIT', 'allowed_regimes': ['old'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'chapter6a'},
    # Shared Deductions (Both Regimes)
    {'category': '80ccd2', 'field_name': 'decl_80ccd2_employer_nps', 'statutory_section': 'Section 80CCD(2)', 'eligibility_strategy': 'EMPLOYER_NPS_PERCENTAGE_CAP', 'parameter_code': 'HDS_IN_TDS_EMPLOYER_CONTRIBUTION_LIMIT', 'allowed_regimes': ['old', 'new'], 'workflow': {'planning_supported': True, 'proof_required': False, 'hr_verification_required': False}, 'deduction_group': 'statutory_earning_deduction'},
    {'category': '57iia', 'field_name': 'decl_57iia_family_pension', 'statutory_section': 'Section 57(iia)', 'eligibility_strategy': 'FAMILY_PENSION_CAP', 'parameter_code': 'HDS_IN_TDS_FAMILY_PENSION_LIMIT', 'allowed_regimes': ['old', 'new'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'statutory_earning_deduction'},
    {'category': '80cch', 'field_name': 'decl_80cch_agniveer', 'statutory_section': 'Section 80CCH', 'eligibility_strategy': 'UNLIMITED', 'parameter_code': None, 'allowed_regimes': ['old', 'new'], 'workflow': {'planning_supported': True, 'proof_required': True, 'hr_verification_required': True}, 'deduction_group': 'statutory_earning_deduction'},
]

DECLARATION_UI_REGISTRY = {
    'decl_80c_ppf': {'label': 'Public Provident Fund (PPF)', 'display_order': 10},
    'decl_80c_elss': {'label': 'ELSS Mutual Funds', 'display_order': 20},
    'decl_80c_epf': {'label': 'Voluntary EPF (VPF)', 'display_order': 30},
    'decl_80c_lic': {'label': 'Life Insurance Premium (LIC)', 'display_order': 40},
    'decl_80c_nsc': {'label': 'National Savings Certificate (NSC)', 'display_order': 50},
    'decl_80c_ssy': {'label': 'Sukanya Samriddhi Yojana (SSY)', 'display_order': 60},
    'decl_80c_fd': {'label': 'Tax Saving Fixed Deposit', 'display_order': 70},
    'decl_80c_tuition': {'label': 'Children Tuition Fees', 'display_order': 80},
    'decl_80c_housing_principal': {'label': 'Housing Loan Principal Repayment', 'display_order': 90},
    'decl_80c_other': {'label': 'Other 80C Specified Investments', 'display_order': 100},
    'decl_80ccd1b_nps': {'label': 'Employee Voluntary NPS', 'display_order': 110},
    'decl_80d_self': {'label': 'Medical Insurance (Self & Family)', 'display_order': 120},
    'decl_80d_parents': {'label': 'Medical Insurance (Parents)', 'display_order': 130},
    'decl_80d_preventive': {'label': 'Preventive Health Checkup', 'display_order': 140},
    'decl_24b_self_interest': {'label': 'Interest on Housing Loan (Self-Occupied)', 'display_order': 150},
    'decl_80eea_interest': {'label': 'First-Time Home Buyer Interest (80EEA)', 'display_order': 160},
    'decl_hra_annual_rent': {'label': 'Annual House Rent Paid', 'display_order': 170},
    'decl_80tta_interest': {'label': 'Savings Interest Deduction (80TTA)', 'display_order': 180},
    'decl_80ttb_interest': {'label': 'Senior Citizen Interest (80TTB)', 'display_order': 190},
    'decl_80e_interest': {'label': 'Education Loan Interest (80E)', 'display_order': 200},
    'decl_80g_donation': {'label': 'Charitable Donations (80G)', 'display_order': 210},
    'decl_80gg_rent': {'label': 'Rent Paid without HRA (80GG)', 'display_order': 220},
    'decl_80dd_amount': {'label': 'Dependent Disability Deduction (80DD)', 'display_order': 230},
    'decl_80ccd2_employer_nps': {'label': 'Employer NPS Contribution (80CCD(2))', 'display_order': 240},
    'decl_57iia_family_pension': {'label': 'Family Pension Deduction (57(iia))', 'display_order': 250},
    'decl_80cch_agniveer': {'label': 'Agniveer Corpus Fund Contribution (80CCH)', 'display_order': 260},
}


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
    is_proof_window_open = fields.Boolean(
        string="Proof Submission Window Open",
        compute='_compute_is_proof_window_open',
        help="Returns True if HR manually opened proof submission toggle OR current date falls within December proof submission window."
    )

    @api.depends('financial_year_id', 'financial_year_id.is_proof_submission_open', 'financial_year_id.proof_submission_start_date', 'financial_year_id.proof_submission_end_date')
    def _compute_is_proof_window_open(self):
        today = fields.Date.today()
        for rec in self:
            fy = rec.financial_year_id
            if not fy:
                rec.is_proof_window_open = False
                continue
            if fy.is_proof_submission_open:
                rec.is_proof_window_open = True
                continue
            if fy.proof_submission_start_date and fy.proof_submission_end_date:
                rec.is_proof_window_open = (fy.proof_submission_start_date <= today <= fy.proof_submission_end_date)
            elif today.month == 12:
                rec.is_proof_window_open = True
            else:
                rec.is_proof_window_open = False

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
        ('declared', 'Declared'),
        ('submitted', 'Submitted'),
        ('proof_submitted', 'Proof Submitted'),
        ('proof_under_review', 'Proof Under Review'),
        ('proof_verified', 'Proof Verified'),
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
    total_rejected_amount = fields.Monetary(
        string="Total Rejected Amount (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help="Sum of all rejected investment amounts across lines."
    )
    total_eligible_amount = fields.Monetary(
        string="Total Eligible Deduction (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=False,
        help="Sum of all system-calculated allowable statutory deductions."
    )
    total_excess_amount = fields.Monetary(
        string="Total Excess / Non-Eligible Amount (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=False,
        help="Sum of all investment portions exceeding statutory limits (Display only)."
    )

    decl_80c_total_declared = fields.Monetary(
        string="Section 80C Declared Investment (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=False,
        help="Total Section 80C declared investments before statutory limit cap."
    )
    decl_80c_total_eligible = fields.Monetary(
        string="Section 80C Eligible Deduction (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=False,
        help="Eligible Section 80C deduction capped at statutory limit of ₹1,50,000."
    )
    decl_80c_total_excess = fields.Monetary(
        string="Section 80C Excess Investment (₹)",
        currency_field='currency_id',
        compute='_compute_totals',
        store=False,
        help="Section 80C investment portion exceeding statutory limit of ₹1,50,000."
    )

    @api.depends(
        'decl_80c_ppf', 'decl_80c_epf', 'decl_80c_lic', 'decl_80c_elss', 'decl_80c_nsc',
        'decl_80c_ssy', 'decl_80c_fd', 'decl_80c_tuition', 'decl_80c_housing_principal', 'decl_80c_other',
        'decl_80ccd1b_nps', 'decl_80d_self', 'decl_80d_self_is_senior', 'decl_80d_parents',
        'decl_80d_parents_is_senior', 'decl_80d_preventive', 'decl_80tta_interest',
        'decl_80ttb_interest', 'decl_80e_interest', 'decl_80g_donation', 'decl_80gg_rent',
        'decl_80dd_amount', 'decl_hra_annual_rent', 'decl_home_loan_interest',
        'declaration_line_ids', 'declaration_line_ids.declared_amount', 'declaration_line_ids.approved_amount',
        'declaration_line_ids.rejected_amount', 'declaration_line_ids.eligible_amount', 'declaration_line_ids.excess_amount',
        'regime_code'
    )
    def _compute_totals(self):
        for rec in self:
            sum_80c_scalars = (
                (rec.decl_80c_ppf or 0.0) + (rec.decl_80c_epf or 0.0) + (rec.decl_80c_lic or 0.0) +
                (rec.decl_80c_elss or 0.0) + (rec.decl_80c_nsc or 0.0) + (rec.decl_80c_ssy or 0.0) +
                (rec.decl_80c_fd or 0.0) + (rec.decl_80c_tuition or 0.0) + (rec.decl_80c_housing_principal or 0.0) +
                (rec.decl_80c_other or 0.0)
            )
            sum_80d = (rec.decl_80d_self or 0.0) + (rec.decl_80d_parents or 0.0) + (rec.decl_80d_preventive or 0.0)
            sum_other_ded = (
                (rec.decl_80ccd1b_nps or 0.0) + (rec.decl_80tta_interest or 0.0) + (rec.decl_80ttb_interest or 0.0) +
                (rec.decl_80e_interest or 0.0) + (rec.decl_80g_donation or 0.0) + (rec.decl_80gg_rent or 0.0) +
                (rec.decl_80dd_amount or 0.0) + (rec.decl_hra_annual_rent or 0.0) + (rec.decl_home_loan_interest or 0.0)
            )
            
            lines_80c_declared = sum(rec.declaration_line_ids.filtered(lambda l: l.category == '80c').mapped('declared_amount'))
            sum_80c_total_declared = sum_80c_scalars + lines_80c_declared

            eligible_80c = min(sum_80c_total_declared, 150000.0) if rec.regime_code == 'old' else 0.0
            excess_80c = max(0.0, sum_80c_total_declared - eligible_80c) if rec.regime_code == 'old' else sum_80c_total_declared

            rec.decl_80c_total_declared = sum_80c_total_declared
            rec.decl_80c_total_eligible = eligible_80c
            rec.decl_80c_total_excess = excess_80c

            lines_declared = sum(rec.declaration_line_ids.mapped('declared_amount'))
            lines_approved = sum(rec.declaration_line_ids.mapped('approved_amount'))
            lines_rejected = sum(rec.declaration_line_ids.mapped('rejected_amount'))
            lines_eligible = sum(rec.declaration_line_ids.mapped('eligible_amount'))
            lines_excess = sum(rec.declaration_line_ids.mapped('excess_amount'))
            
            rec.total_declared_amount = sum_80c_scalars + sum_80d + sum_other_ded + lines_declared
            
            approved_80c = min(sum_80c_scalars, 150000.0) if rec.regime_code == 'old' else 0.0
            approved_80d_self = min((rec.decl_80d_self or 0.0) + min(rec.decl_80d_preventive or 0.0, 5000.0), 50000.0 if rec.decl_80d_self_is_senior else 25000.0)
            approved_80d_parents = min(rec.decl_80d_parents or 0.0, 50000.0 if rec.decl_80d_parents_is_senior else 25000.0)
            approved_80d = (approved_80d_self + approved_80d_parents) if rec.regime_code == 'old' else 0.0
            approved_80ccd1b = min(rec.decl_80ccd1b_nps or 0.0, 50000.0) if rec.regime_code == 'old' else 0.0
            approved_home_loan = min(rec.decl_home_loan_interest or 0.0, 200000.0) if rec.regime_code == 'old' else 0.0
            
            if rec.regime_code == 'old':
                scalar_approved = approved_80c + approved_80d + approved_80ccd1b + approved_home_loan + (rec.decl_80e_interest or 0.0) + (rec.decl_80g_donation or 0.0)
            else:
                scalar_approved = 0.0

            rec.total_approved_amount = scalar_approved + lines_approved
            rec.total_rejected_amount = lines_rejected
            rec.total_eligible_amount = eligible_80c + lines_eligible
            rec.total_excess_amount = excess_80c + lines_excess

            _logger.info(
                "\n=========================================\n"
                "DEDUCTION ELIGIBILITY TRACE\n"
                "=========================================\n"
                "Employee        : %s\n"
                "Financial Year  : %s\n"
                "Section         : Section 80C\n"
                "Declared Amount : ₹%s\n"
                "Statutory Limit : ₹1,50,000.00\n"
                "Eligible Deduct : ₹%s\n"
                "Excess Amount   : ₹%s (Display Only)\n"
                "Rule Applied    : Income Tax Act Section 80C (Capped at ₹1,50,000 p.a.)\n"
                "=========================================",
                rec.employee_id.name if rec.employee_id else 'N/A',
                rec.financial_year_id.name if rec.financial_year_id else 'N/A',
                sum_80c_total_declared, eligible_80c, excess_80c
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

    regime_choice_id = fields.Many2one(
        'tds.tax.regime',
        string="Selected Tax Regime Choice",
        compute='_compute_regime_choice_id',
        inverse='_inverse_regime_choice_id',
        store=False,
        help="Editable Tax Regime selection for employee in current FY."
    )

    # -------------------------------------------------------------------------
    # PROXY FIELDS MAPPED TO tds.employee.income.declaration FOR ESS DASHBOARD
    # -------------------------------------------------------------------------
    savings_bank_interest = fields.Monetary(
        string="Savings Account Interest (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 56 - Savings Account Interest\n"
             "• Type: Income from Other Sources.\n"
             "• Applicability: Both Old and New Regimes.\n"
             "• Notes: Report total annual interest earned from all savings bank accounts. Under Old Regime, deduction up to ₹10,000 is available under Section 80TTA (₹50,000 under 80TTB for Senior Citizens)."
    )
    fixed_deposit_interest = fields.Monetary(
        string="Fixed Deposit Interest (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 56 - Fixed & Term Deposit Interest\n"
             "• Type: Income from Other Sources.\n"
             "• Applicability: Both Old and New Regimes.\n"
             "• Notes: Report annual interest accrued on term deposits, fixed deposits, and recurring deposits."
    )
    dividend_income = fields.Monetary(
        string="Dividend Income (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 56 - Dividend Income\n"
             "• Type: Taxable Dividend Income.\n"
             "• Applicability: Both Old and New Regimes.\n"
             "• Notes: Total dividend income received from Indian companies and mutual funds, taxable at applicable slab rates."
    )
    other_sources_income = fields.Monetary(
        string="Other Miscellaneous Income (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 56 - Miscellaneous Income\n"
             "• Type: Other Sources.\n"
             "• Applicability: Both Old and New Regimes.\n"
             "• Notes: Includes gifts, interest on income tax refund, commission, or any other non-payroll taxable income."
    )
    total_other_sources_income = fields.Monetary(
        string="Total Other Sources Income (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        store=False,
        help="Total Income from Other Sources aggregated for TDS computation."
    )

    annual_let_out_rent = fields.Monetary(
        string="Gross Annual Rent (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 23(1)(b) - Gross Annual Rent Received\n"
             "• Type: Income from House Property (Let-Out Property).\n"
             "• Applicability: Both Old and New Regimes.\n"
             "• Notes: Total rent collected from let-out residential or commercial property during the financial year."
    )
    municipal_taxes_paid = fields.Monetary(
        string="Municipal Taxes Paid (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 23(1) - Municipal Taxes Paid\n"
             "• Type: Property Tax Deduction.\n"
             "• Applicability: Both Old and New Regimes.\n"
             "• Notes: Municipal taxes paid to local authorities during the financial year. Allowed as deduction from gross rent."
    )
    let_out_interest_paid = fields.Monetary(
        string="Housing Loan Interest (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Section 24(b) - Home Loan Interest (Let-Out Property)\n"
             "• Limit: Full actual interest paid (UNCAPPED for let-out property).\n"
             "• Applicability: Both Old and New Regimes (Loss set-off restricted to let-out income under New Regime)."
    )
    net_house_property_income_loss = fields.Monetary(
        string="Net Property Income / Loss (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        store=False,
        help="Net taxable income or loss from Let-Out House Property after 30% statutory standard deduction under Section 24(a)."
    )

    prev_employer_taxable_gross = fields.Monetary(
        string="Previous Employer Taxable Salary (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Form 12B / Form 16 Part B - Previous Employer Taxable Gross Salary\n"
             "• Applicability: Mid-year joiners.\n"
             "• Notes: Total taxable salary received from previous employer during the current financial year."
    )
    prev_employer_tds = fields.Monetary(
        string="Previous Employer TDS Deducted (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Previous Employer Income Tax (TDS) Deducted\n"
             "• Notes: Total income tax already deducted at source by previous employer as per Form 12B."
    )
    prev_employer_pt = fields.Monetary(
        string="Previous Employer PT Deducted (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Previous Employer Professional Tax (PT)\n"
             "• Notes: Professional tax deducted by previous employer."
    )
    prev_employer_pf = fields.Monetary(
        string="Previous Employer EPF (₹)",
        currency_field='currency_id',
        compute='_compute_income_decl_fields',
        inverse='_inverse_income_decl_fields',
        store=False,
        help="Previous Employer Provident Fund (EPF)\n"
             "• Notes: Employee EPF contribution deducted by previous employer."
    )

    # -------------------------------------------------------------------------
    # STORED DEDUCTION FIELDS (PERSISTENT DATABASE COLUMNS)
    # -------------------------------------------------------------------------
    # Section 80C Specified Investments (Gross Limit ₹1,50,000)
    decl_80c_ppf = fields.Monetary(
        string="Public Provident Fund (PPF) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Public Provident Fund (PPF)"
    )
    decl_80c_elss = fields.Monetary(
        string="ELSS Mutual Funds (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Equity Linked Savings Scheme (ELSS)"
    )
    decl_80c_epf = fields.Monetary(
        string="Voluntary EPF (VPF) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Voluntary Employees' Provident Fund (VPF)"
    )
    decl_80c_lic = fields.Monetary(
        string="Life Insurance Premium (LIC) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Life Insurance Premium"
    )
    decl_80c_nsc = fields.Monetary(
        string="National Savings Certificate (NSC) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - National Savings Certificate (NSC)"
    )
    decl_80c_ssy = fields.Monetary(
        string="Sukanya Samriddhi Yojana (SSY) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Sukanya Samriddhi Yojana (SSY)"
    )
    decl_80c_fd = fields.Monetary(
        string="Tax Saving Fixed Deposit (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Tax Saving 5-Year Bank Fixed Deposit"
    )
    decl_80c_tuition = fields.Monetary(
        string="Children Tuition Fees (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Children's School / College Tuition Fees"
    )
    decl_80c_housing_principal = fields.Monetary(
        string="Housing Loan Principal Repayment (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Housing Loan Principal Repayment"
    )
    decl_80c_other = fields.Monetary(
        string="Other 80C Specified Investments (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80C - Other Specified Investments"
    )

    decl_80c_total = fields.Monetary(
        string="Total Section 80C Declared (₹)",
        currency_field='currency_id',
        compute='_compute_80c_summary',
        store=True,
        help="Total Section 80C declared amount subject to statutory cap of ₹1,50,000."
    )
    is_80c_exceeded = fields.Boolean(
        string="Section 80C Exceeds Ceiling (₹1.5L)",
        compute='_compute_80c_summary',
        store=True,
        help="True if total declared Section 80C investments exceed the statutory ceiling of ₹1,50,000."
    )
    section_80c_warning_msg = fields.Char(
        string="Section 80C Warning Message",
        compute='_compute_80c_summary',
        store=True,
        help="Informative warning message when Section 80C declared investments exceed ₹1,50,000 statutory limit."
    )

    @api.depends(
        'decl_80c_ppf', 'decl_80c_elss', 'decl_80c_epf', 'decl_80c_lic', 'decl_80c_nsc',
        'decl_80c_ssy', 'decl_80c_fd', 'decl_80c_tuition', 'decl_80c_housing_principal', 'decl_80c_other'
    )
    def _compute_80c_summary(self):
        for rec in self:
            rec.decl_80c_total = (
                (rec.decl_80c_ppf or 0.0) + (rec.decl_80c_elss or 0.0) + (rec.decl_80c_epf or 0.0) +
                (rec.decl_80c_lic or 0.0) + (rec.decl_80c_nsc or 0.0) + (rec.decl_80c_ssy or 0.0) +
                (rec.decl_80c_fd or 0.0) + (rec.decl_80c_tuition or 0.0) + (rec.decl_80c_housing_principal or 0.0) +
                (rec.decl_80c_other or 0.0)
            )
            if rec.decl_80c_total > 150000.0:
                rec.is_80c_exceeded = True
                rec.section_80c_warning_msg = f"Notice: Total Section 80C declared investments (₹{rec.decl_80c_total:,.2f}) exceed the statutory ceiling of ₹1,50,000. All declared values are fully preserved, and the ₹1,50,000 cap will be applied automatically during tax calculation."
            else:
                rec.is_80c_exceeded = False
                rec.section_80c_warning_msg = ""

    # Section 80CCD(1B) Additional NPS Contribution
    decl_80ccd1b_nps = fields.Monetary(
        string="Employee Voluntary NPS (80CCD(1B)) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80CCD(1B) - Employee Voluntary NPS Contribution"
    )

    # Section 80D Medical Insurance
    decl_80d_self = fields.Monetary(
        string="Medical Insurance - Self & Family (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80D - Health Insurance Premium (Self, Spouse & Children)"
    )
    decl_80d_parents = fields.Monetary(
        string="Medical Insurance - Parents (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80D - Health Insurance Premium (Parents)"
    )
    decl_80d_parents_is_senior = fields.Boolean(
        string="Parents are Senior Citizens (Age ≥ 60)",
        default=False,
        store=True,
        help="Mark True if parents are aged 60 years or above."
    )
    decl_80d_preventive = fields.Monetary(
        string="Preventive Health Checkup (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80D - Preventive Annual Health Checkup"
    )

    # HRA
    decl_hra_annual_rent = fields.Monetary(
        string="Annual House Rent Paid (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 10(13A) - House Rent Allowance (HRA Exemption)"
    )
    decl_hra_landlord_name = fields.Char(
        string="Landlord Name",
        store=True,
        help="Full name of property owner / landlord."
    )
    decl_hra_landlord_pan = fields.Char(
        string="Landlord PAN",
        store=True,
        help="10-character PAN of landlord."
    )
    decl_hra_is_metro = fields.Boolean(
        string="Accommodation in Metro City",
        default=False,
        store=True,
        help="Mark True if rented accommodation is located in Metro city."
    )

    @api.constrains('decl_hra_annual_rent', 'decl_hra_landlord_name', 'decl_hra_landlord_pan')
    def _check_hra_landlord_validation(self):
        pan_regex = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
        for rec in self:
            rent = rec.decl_hra_annual_rent or 0.0
            if rent > 0.0:
                if not rec.decl_hra_landlord_name or not rec.decl_hra_landlord_name.strip():
                    raise ValidationError(_("Landlord Name is mandatory when declaring House Rent Allowance (HRA) rent of ₹%s.") % f"{rent:,.2f}")
            if rent > 100000.0:
                pan = (rec.decl_hra_landlord_pan or '').strip().upper()
                if not pan:
                    raise ValidationError(_("CBDT Statutory Requirement: Landlord PAN is mandatory when annual rent exceeds ₹1,00,000 p.a. (Current declaration: ₹%s p.a. / ₹%s monthly). Please enter Landlord PAN before submitting.") % (f"{rent:,.2f}", f"{(rent/12.0):,.2f}"))
                if not pan_regex.match(pan):
                    raise ValidationError(_("Invalid Landlord PAN '%s'. Landlord PAN must be a valid 10-character Indian PAN format (e.g. ABCDE1234F).") % rec.decl_hra_landlord_pan)

    # Home Loan Interest
    decl_24b_self_interest = fields.Monetary(
        string="Self-Occupied Home Loan Interest (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 24(b) - Home Loan Interest"
    )
    decl_80eea_interest = fields.Monetary(
        string="First-Time Home Buyer Interest (80EEA) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80EEA - First-Time Home Buyer Additional Interest"
    )
    decl_80eea_loan_sanction_date = fields.Date(
        string="80EEA Loan Sanction Date",
        store=True,
        help="Sanction date of housing loan by bank (Must be between 01-Apr-2019 and 31-Mar-2022 for Section 80EEA)."
    )
    decl_80eea_property_stamp_value = fields.Monetary(
        string="80EEA Property Stamp Duty Value (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Stamp duty value of residential house property (Must not exceed ₹45,00,000 for Section 80EEA)."
    )
    decl_80eea_first_time_home_buyer = fields.Boolean(
        string="First-Time Home Buyer (Section 80EEA)",
        default=True,
        store=True,
        help="Mark True if employee does not own any other residential property on loan sanction date."
    )
    decl_80eea_claimed_under_80ee = fields.Boolean(
        string="Claimed Deduction under Section 80EE",
        default=False,
        store=True,
        help="Mark True if deduction has already been claimed under Section 80EE (Disqualifies Section 80EEA)."
    )
    decl_80eea_lending_institution = fields.Char(
        string="80EEA Lending Bank / Institution",
        store=True,
        help="Name of bank or financial institution (e.g. State Bank of India, HDFC Bank)."
    )
    decl_80eea_loan_account_number = fields.Char(
        string="80EEA Loan Account Number",
        store=True,
        help="Housing loan account number."
    )

    # Other Chapter VI-A Deductions
    decl_80tta_interest = fields.Monetary(
        string="Savings Interest Deduction (80TTA) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80TTA - Savings Account Interest Deduction"
    )
    decl_80ttb_interest = fields.Monetary(
        string="Senior Citizen Interest (80TTB) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80TTB - Senior Citizen Savings & FD Interest"
    )
    decl_80e_interest = fields.Monetary(
        string="Education Loan Interest (80E) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80E - Education Loan Interest"
    )
    decl_80g_donation = fields.Monetary(
        string="Charitable Donations (80G) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80G - Donations to Charitable Trusts & Relief Funds"
    )
    decl_80gg_rent = fields.Monetary(
        string="Rent Paid without HRA (80GG) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80GG - Rent Paid by Employees NOT Receiving HRA"
    )
    decl_80dd_amount = fields.Monetary(
        string="Dependent Disability Deduction (80DD) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80DD - Maintenance / Medical Treatment of Disabled Dependent"
    )

    # Deductions Allowed Under BOTH Regimes
    decl_80ccd2_employer_nps = fields.Monetary(
        string="Employer NPS Contribution (80CCD(2)) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80CCD(2) - Employer NPS Contribution"
    )
    decl_57iia_family_pension = fields.Monetary(
        string="Family Pension Deduction (57(iia)) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 57(iia) - Standard Deduction on Family Pension"
    )
    decl_80cch_agniveer = fields.Monetary(
        string="Agniveer Corpus Fund Contribution (80CCH) (₹)",
        currency_field='currency_id',
        default=0.0,
        store=True,
        help="Section 80CCH - Agniveer Corpus Fund Contribution"
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
                reg_record = self.env['tds.employee.tax.regime'].sudo().search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('financial_year_id', '=', rec.financial_year_id.id),
                ], limit=1)
                if reg_record:
                    rec.tax_regime_id = reg_record.regime_id
                    continue

            # Fallback to default regime master
            default_reg = self.env['tds.tax.regime'].search([('is_default', '=', True)], limit=1)
            rec.tax_regime_id = default_reg.id if default_reg else False

    @api.depends('tax_regime_id')
    def _compute_regime_choice_id(self):
        for rec in self:
            rec.regime_choice_id = rec.tax_regime_id

    def _inverse_regime_choice_id(self):
        for rec in self:
            if rec.employee_id and rec.financial_year_id and rec.regime_choice_id:
                rec.tax_regime_id = rec.regime_choice_id
                reg_record = self.env['tds.employee.tax.regime'].sudo().search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('financial_year_id', '=', rec.financial_year_id.id),
                ], limit=1)
                if reg_record:
                    if reg_record.is_locked:
                        raise ValidationError(_("Tax regime choice is locked by HR for Financial Year '%s'. Contact HR to request an unlock.") % rec.financial_year_id.name)
                    reg_record.sudo().write({'regime_id': rec.regime_choice_id.id})
                else:
                    self.env['tds.employee.tax.regime'].sudo().create({
                        'employee_id': rec.employee_id.id,
                        'financial_year_id': rec.financial_year_id.id,
                        'regime_id': rec.regime_choice_id.id,
                    })

    def _get_income_declaration(self):
        self.ensure_one()
        if not self.employee_id or not self.financial_year_id:
            return False
        return self.env['tds.employee.income.declaration'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('financial_year_id', '=', self.financial_year_id.id),
        ], limit=1)

    @api.depends('employee_id', 'financial_year_id')
    def _compute_income_decl_fields(self):
        for rec in self:
            decl = rec._get_income_declaration()
            if decl:
                rec.savings_bank_interest = decl.savings_bank_interest
                rec.fixed_deposit_interest = decl.fixed_deposit_interest
                rec.dividend_income = decl.dividend_income
                rec.other_sources_income = decl.other_sources_income
                rec.total_other_sources_income = decl.total_other_sources_income
                rec.annual_let_out_rent = decl.annual_let_out_rent
                rec.municipal_taxes_paid = decl.municipal_taxes_paid
                rec.let_out_interest_paid = decl.let_out_interest_paid
                rec.net_house_property_income_loss = decl.net_house_property_income_loss
                rec.prev_employer_taxable_gross = decl.prev_employer_taxable_gross
                rec.prev_employer_tds = decl.prev_employer_tds
                rec.prev_employer_pt = decl.prev_employer_pt
                rec.prev_employer_pf = decl.prev_employer_pf
            else:
                rec.savings_bank_interest = 0.0
                rec.fixed_deposit_interest = 0.0
                rec.dividend_income = 0.0
                rec.other_sources_income = 0.0
                rec.total_other_sources_income = 0.0
                rec.annual_let_out_rent = 0.0
                rec.municipal_taxes_paid = 0.0
                rec.let_out_interest_paid = 0.0
                rec.net_house_property_income_loss = 0.0
                rec.prev_employer_taxable_gross = 0.0
                rec.prev_employer_tds = 0.0
                rec.prev_employer_pt = 0.0
                rec.prev_employer_pf = 0.0

    def _inverse_income_decl_fields(self):
        income_fields = [
            'savings_bank_interest', 'fixed_deposit_interest', 'dividend_income',
            'other_sources_income', 'annual_let_out_rent', 'municipal_taxes_paid',
            'let_out_interest_paid', 'prev_employer_taxable_gross', 'prev_employer_tds',
            'prev_employer_pt', 'prev_employer_pf'
        ]
        for rec in self:
            if not rec.employee_id or not rec.financial_year_id:
                continue
            decl = rec._get_income_declaration()
            if decl:
                vals = {}
                for f in income_fields:
                    val = getattr(rec, f, False)
                    if val is False or val is None:
                        continue
                    val = float(val)
                    decl_val = float(getattr(decl, f, 0.0) or 0.0)
                    if abs(val - decl_val) > 0.001:
                        vals[f] = val
                if vals:
                    decl.sudo().write(vals)
            else:
                vals = {f: float(getattr(rec, f, 0.0) or 0.0) for f in income_fields}
                vals.update({
                    'employee_id': rec.employee_id.id,
                    'financial_year_id': rec.financial_year_id.id,
                })
                self.env['tds.employee.income.declaration'].sudo().create(vals)

    def _sync_declaration_line(self, category_code, description, amount, ui_field_label, python_field_name, is_senior=False, is_severe=False, method_name='write'):
        """
        Helper to create or update a tds.employee.declaration.line.
        Logs detailed FIELD PERSISTENCE TRACE for exact audit trail.
        """
        self.ensure_one()
        lines = self.declaration_line_ids.filtered(
            lambda l: l.category == category_code and l.description and description.split(' (')[0] in l.description
        )
        existing_val = lines[0].declared_amount if lines else 0.0
        line_id = lines[0].id if lines else 'New'

        if amount > 0.0:
            if lines:
                lines[0].sudo().write({
                    'declared_amount': amount,
                    'description': description,
                    'is_senior_citizen': is_senior,
                    'is_severe_disability': is_severe,
                })
                line_id = lines[0].id
                post_val = lines[0].declared_amount
            else:
                new_line = self.env['tds.employee.declaration.line'].sudo().create({
                    'declaration_id': self.id,
                    'category': category_code,
                    'description': description,
                    'declared_amount': amount,
                    'is_senior_citizen': is_senior,
                    'is_severe_disability': is_severe,
                })
                line_id = new_line.id
                post_val = new_line.declared_amount
        else:
            if lines:
                lines.sudo().unlink()
            post_val = 0.0

        read_val = float(getattr(self, python_field_name, 0.0) or 0.0) if hasattr(self, python_field_name) else post_val

        _logger.warning(
            "\n====================================================\n"
            "FIELD PERSISTENCE TRACE\n"
            "====================================================\n"
            "Employee : %s\n"
            "FY : %s\n"
            "Declaration ID : %s\n"
            "UI Field : %s\n"
            "Python Field : %s\n"
            "Category : %s\n"
            "Description : %s\n"
            "Incoming Value : %s\n"
            "Existing DB Value : %s\n"
            "Written Value : %s\n"
            "DB After Write : %s\n"
            "DB After Read : %s\n"
            "Line ID : %s\n"
            "Method : %s\n"
            "====================================================",
            self.employee_id.name if self.employee_id else "N/A",
            self.financial_year_id.name if self.financial_year_id else "N/A",
            self.id,
            ui_field_label,
            python_field_name,
            category_code,
            description,
            amount,
            existing_val,
            amount,
            post_val,
            read_val,
            line_id,
            method_name
        )

    def _sync_all_declaration_lines(self, method_name='write'):
        """
        Metadata-driven synchronization of stored decl_* fields to child declaration_line_ids.
        Iterates over DECLARATION_BUSINESS_REGISTRY to automatically manage child line items for all statutory fields.
        """
        for rec in self:
            for item in DECLARATION_BUSINESS_REGISTRY:
                cat = item['category']
                field_name = item['field_name']
                alt_field = item.get('alt_field_name')

                # Read monetary value from primary or alternate header field
                val = float(getattr(rec, field_name, 0.0) or 0.0)
                if val == 0.0 and alt_field:
                    val = float(getattr(rec, alt_field, 0.0) or 0.0)

                is_senior = False
                if 'is_senior_field' in item:
                    is_senior = bool(getattr(rec, item['is_senior_field'], False))

                ui_info = DECLARATION_UI_REGISTRY.get(field_name, {})
                desc = ui_info.get('label', field_name)

                if cat == 'hra':
                    if rec.decl_hra_landlord_name or rec.decl_hra_landlord_pan:
                        desc += f" (Landlord: {rec.decl_hra_landlord_name or 'N/A'} (PAN: {rec.decl_hra_landlord_pan or 'N/A'}))"

                rec._sync_declaration_line(
                    category_code=cat,
                    description=desc,
                    amount=val,
                    ui_field_label=desc,
                    python_field_name=field_name,
                    is_senior=is_senior,
                    method_name=method_name
                )
    def _compute_totals(self):
        for rec in self:
            rec.total_declared_amount = sum(line.declared_amount for line in rec.declaration_line_ids)
            rec.total_approved_amount = sum(line.approved_amount for line in rec.declaration_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            _logger.warning(
                "[HR & ESS DECLARATION PERSISTENCE AUDIT] Created Declaration ID: %s | Employee: %s (ID: %s) | FY: %s | Total Declared: ₹%s | Line Items: %s",
                rec.id, rec.employee_id.name if rec.employee_id else "None", rec.employee_id.id if rec.employee_id else "None",
                rec.financial_year_id.name if rec.financial_year_id else "None", rec.total_declared_amount, len(rec.declaration_line_ids)
            )
        return records

    def write(self, vals):
        _logger.warning(
            "[HR & ESS DECLARATION PERSISTENCE AUDIT] Write Called on Declaration IDs: %s | Payload Vals: %s",
            self.ids, vals
        )
        res = super().write(vals)
        for rec in self:
            _logger.warning(
                "[HR & ESS DECLARATION PERSISTENCE AUDIT] Post-Write Verified Declaration ID: %s | Employee: %s | FY: %s | Total Declared: ₹%s | Total Approved: ₹%s | Line Items Count: %s",
                rec.id, rec.employee_id.name if rec.employee_id else "None",
                rec.financial_year_id.name if rec.financial_year_id else "None",
                rec.total_declared_amount, rec.total_approved_amount, len(rec.declaration_line_ids)
            )
        return res

    def action_validate_declaration_rules(self):
        """
        Invokes EmployeeTaxDeclarationValidationService to perform regime-aware line item validations.
        """
        for rec in self:
            from ..services.tds.employee_tax_declaration_validation_service import EmployeeTaxDeclarationValidationService
            val_svc = EmployeeTaxDeclarationValidationService(self.env)
            val_svc.validate_declaration(rec)

    def action_submit_declaration(self):
        """Phase 1 / Phase 2: Employee submits planned investment declaration."""
        for rec in self:
            old_state = rec.state
            rec.action_validate_declaration_rules()
            rec.write({
                'state': 'declared',
                'submission_date': fields.Date.today(),
            })
            _logger.info(
                "[TDS TRACE] Phase: Declaration | Model: tds.employee.declaration | Record ID: %s | Employee: %s | FY: %s | Field: state | Old Value: %s | New Value: declared | Target Model: tds.employee.declaration | DB Write: True | Service: TdsEmployeeDeclaration | Result: Planned Investment Declaration Active",
                rec.id, rec.employee_id.name if rec.employee_id else 'N/A', rec.financial_year_id.name if rec.financial_year_id else 'N/A', old_state
            )

    def action_submit(self):
        """Alias for action_submit_declaration for UI compatibility."""
        return self.action_submit_declaration()

    def action_submit_proofs(self):
        """Phase 3: Employee submits proof attachments during December/January proof window."""
        for rec in self:
            old_state = rec.state
            fy = rec.financial_year_id
            if fy and not rec.is_proof_window_open and not fy.is_proof_submission_active():
                raise ValidationError(_("The Investment Proof Submission Window for Financial Year '%s' is not currently open. Please contact HR.") % (fy.name if fy else ''))
            rec.write({'state': 'proof_submitted'})
            _logger.info(
                "[TDS TRACE] Phase: Proof Submission | Model: tds.employee.declaration | Record ID: %s | Employee: %s | FY: %s | Field: state | Old Value: %s | New Value: proof_submitted | Target Model: tds.employee.declaration | DB Write: True | Service: TdsEmployeeDeclaration | Result: Proof Documents Submitted for HR Verification",
                rec.id, rec.employee_id.name if rec.employee_id else 'N/A', rec.financial_year_id.name if rec.financial_year_id else 'N/A', old_state
            )

    def action_start_review(self):
        """Phase 3 / Phase 4: HR starts proof verification."""
        for rec in self:
            old_state = rec.state
            rec.write({'state': 'proof_under_review'})
            _logger.info(
                "[TDS TRACE] Phase: HR Verification | Model: tds.employee.declaration | Record ID: %s | Employee: %s | FY: %s | Field: state | Old Value: %s | New Value: proof_under_review | Target Model: tds.employee.declaration | DB Write: True | Service: TdsEmployeeDeclaration | Result: Proof Verification In Progress by HR",
                rec.id, rec.employee_id.name if rec.employee_id else 'N/A', rec.financial_year_id.name if rec.financial_year_id else 'N/A', old_state
            )

    def action_review(self):
        """Alias for action_start_review."""
        return self.action_start_review()

    def action_verify_proofs(self):
        """Phase 4: HR completes proof verification, setting approved amounts active for Jan-Mar payroll."""
        for rec in self:
            old_state = rec.state
            rec.action_validate_declaration_rules()
            rec.write({
                'state': 'proof_verified',
                'approval_date': fields.Date.today(),
                'approved_by_id': self.env.user.id,
            })
            _logger.info(
                "[TDS TRACE] Phase: HR Verification | Model: tds.employee.declaration | Record ID: %s | Employee: %s | FY: %s | Field: state | Old Value: %s | New Value: proof_verified | Target Model: tds.employee.declaration | DB Write: True | Service: TdsEmployeeDeclaration | Result: Proof Verified; Approved Amounts Active for Jan-Mar TDS",
                rec.id, rec.employee_id.name if rec.employee_id else 'N/A', rec.financial_year_id.name if rec.financial_year_id else 'N/A', old_state
            )
            # Log audit entry
            if 'hds.in.payroll.audit' in self.env:
                self.env['hds.in.payroll.audit'].sudo().create({
                    'employee_id': rec.employee_id.id,
                    'company_id': rec.company_id.id,
                    'statutory_module': 'tds',
                    'rule_code': 'TDS_DECL_APPROVE',
                    'calculation_date': fields.Date.today(),
                    'messages': f"Tax Declaration Proof Verified: {rec.name}. FY {rec.financial_year_id.name}. Total Declared: ₹{rec.total_declared_amount:,.2f}, Total Approved: ₹{rec.total_approved_amount:,.2f}, Total Rejected: ₹{rec.total_rejected_amount:,.2f}.",
                    'status': 'success',
                })

    def action_approve(self):
        """Alias for action_verify_proofs for backward compatibility."""
        return self.action_verify_proofs()

    def action_reject(self):
        """Transition to Rejected."""
        for rec in self:
            old_state = rec.state
            if not rec.rejection_reason:
                raise ValidationError(_("Please provide a Rejection Reason before rejecting the declaration."))
            rec.write({'state': 'rejected'})
            _logger.info(
                "[TDS TRACE] Phase: HR Verification | Model: tds.employee.declaration | Record ID: %s | Employee: %s | FY: %s | Field: state | Old Value: %s | New Value: rejected | Target Model: tds.employee.declaration | DB Write: True | Service: TdsEmployeeDeclaration | Result: Declaration Rejected",
                rec.id, rec.employee_id.name if rec.employee_id else 'N/A', rec.financial_year_id.name if rec.financial_year_id else 'N/A', old_state
            )

    def action_reset_to_draft(self):
        """Reset back to Draft state."""
        for rec in self:
            old_state = rec.state
            rec.write({'state': 'draft'})
            _logger.info(
                "[TDS TRACE] Phase: Declaration | Model: tds.employee.declaration | Record ID: %s | Employee: %s | FY: %s | Field: state | Old Value: %s | New Value: draft | Target Model: tds.employee.declaration | DB Write: True | Service: TdsEmployeeDeclaration | Result: Reset to Draft",
                rec.id, rec.employee_id.name if rec.employee_id else 'N/A', rec.financial_year_id.name if rec.financial_year_id else 'N/A', old_state
            )

    def _sync_tax_regime(self):
        """
        Synchronizes tax_regime_id on declaration header to tds.employee.tax.regime master record.
        Ensures AnnualIncomeProjectionService and DeductionCalculationService always read the correct regime.
        """
        for rec in self:
            if rec.employee_id and rec.financial_year_id and rec.tax_regime_id:
                reg_record = self.env['tds.employee.tax.regime'].sudo().search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('financial_year_id', '=', rec.financial_year_id.id),
                ], limit=1)
                if reg_record:
                    if reg_record.regime_id != rec.tax_regime_id:
                        if reg_record.is_locked:
                            raise ValidationError(_("Tax regime choice is locked by HR for Financial Year '%s'.") % rec.financial_year_id.name)
                        reg_record.sudo().write({'regime_id': rec.tax_regime_id.id})
                else:
                    self.env['tds.employee.tax.regime'].sudo().create({
                        'employee_id': rec.employee_id.id,
                        'financial_year_id': rec.financial_year_id.id,
                        'regime_id': rec.tax_regime_id.id,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_tax_regime()
        records._sync_all_declaration_lines(method_name='create')
        for rec in records:
            _logger.warning(
                "[HR & ESS DECLARATION PERSISTENCE AUDIT] Created Declaration ID: %s | Employee: %s (ID: %s) | FY: %s | Total Declared: ₹%s | Line Items: %s",
                rec.id, rec.employee_id.name if rec.employee_id else "None", rec.employee_id.id if rec.employee_id else "None",
                rec.financial_year_id.name if rec.financial_year_id else "None", rec.total_declared_amount, len(rec.declaration_line_ids)
            )
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_tax_regime()
        self._sync_all_declaration_lines(method_name='write')
        _logger.warning(
            "[HR & ESS DECLARATION PERSISTENCE AUDIT] Write Called on Declaration IDs: %s | Payload Vals: %s",
            self.ids, vals
        )
        return res
