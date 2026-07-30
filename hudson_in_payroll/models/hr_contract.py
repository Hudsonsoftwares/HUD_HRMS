# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrVersion(models.Model):
    """
    Extends Contract model (hr.version in Odoo 19 Community) to calculate
    projected Monthly and Annual Employer Cost to Company (CTC).
    """
    _inherit = 'hr.version'

    hds_in_employer_cost_monthly = fields.Monetary(
        string="Employer Cost (Monthly)",
        compute='_compute_employer_cost',
        store=True,
        currency_field='currency_id',
        help="Monthly Cost to Company (Gross Salary + Employer Contributions)."
    )

    hds_in_employer_cost_annual = fields.Monetary(
        string="Employer Cost to Company (CTC)",
        compute='_compute_employer_cost',
        store=True,
        currency_field='currency_id',
        help="Annual Employer Cost to Company (CTC)."
    )

    def _register_hook(self):
        """Pre-emptively ensure columns exist in PostgreSQL hr_version table."""
        super()._register_hook()
        cr = self.env.cr
        try:
            cr.execute("""
                ALTER TABLE hr_version
                ADD COLUMN IF NOT EXISTS hds_in_employer_cost_monthly double precision DEFAULT 0.0,
                ADD COLUMN IF NOT EXISTS hds_in_employer_cost_annual double precision DEFAULT 0.0;
            """)
        except Exception:
            pass

    def _auto_init(self):
        """Pre-emptively ensure columns exist in PostgreSQL hr_version table."""
        cr = self.env.cr
        cr.execute("""
            ALTER TABLE hr_version
            ADD COLUMN IF NOT EXISTS hds_in_employer_cost_monthly double precision DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS hds_in_employer_cost_annual double precision DEFAULT 0.0;
        """)
        return super()._auto_init()

    @api.depends('wage', 'struct_id', 'struct_id.rule_ids', 'struct_id.rule_ids.hds_in_contributes_to_employer_cost')
    def _compute_employer_cost(self):
        for contract in self:
            wage = contract.wage or 0.0
            employer_contrib_monthly = 0.0

            if contract.struct_id:
                ctc_rules = contract.struct_id.get_all_rules()
                rule_ids = [r[0] if isinstance(r, (tuple, list)) else r for r in ctc_rules]
                rules = self.env['hr.salary.rule'].browse(rule_ids).filtered(
                    lambda r: r.hds_in_contributes_to_employer_cost and r.active
                )
            else:
                rules = self.env['hr.salary.rule'].search([('hds_in_contributes_to_employer_cost', '=', True), ('active', '=', True)])

            for rule in rules:
                if rule.amount_select == 'fix':
                    employer_contrib_monthly += rule.amount_fix
                elif rule.amount_select == 'percentage':
                    employer_contrib_monthly += (wage * rule.amount_percentage / 100.0)
                elif rule.amount_select == 'code':
                    employer_contrib_monthly += self._estimate_statutory_rule_amount(contract, rule)

            monthly_ctc = wage + employer_contrib_monthly
            contract.hds_in_employer_cost_monthly = monthly_ctc
            contract.hds_in_employer_cost_annual = monthly_ctc * 12.0
            if contract.employee_id:
                contract.employee_id._compute_hds_in_employer_cost()

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        super()._onchange_contract_template_id()
        self._compute_employer_cost()

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        for contract in contracts:
            contract._compute_employer_cost()
            if contract.employee_id and contract.wage:
                contract._sync_employee_esic_default()
        return contracts

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('wage', 'employee_id', 'struct_id', 'contract_template_id', 'basic_salary', 'hra', 'da')):
            for contract in self:
                contract._compute_employer_cost()
                if contract.employee_id and contract.wage:
                    contract._sync_employee_esic_default()
        return res

    @api.onchange('wage', 'employee_id')
    def _onchange_wage_sync_esic(self):
        for contract in self:
            if contract.employee_id and contract.wage:
                default_esic = contract.employee_id._evaluate_default_esic_applicable(
                    gross_wage=contract.wage,
                    eval_date=contract.date_start or fields.Date.today()
                )
                contract.employee_id.hds_in_esic_applicable = default_esic

    def _sync_employee_esic_default(self):
        """
        Updates default ESIC applicability on employee when contract wage changes,
        while maintaining manual override capability.
        """
        self.ensure_one()
        employee = self.employee_id
        if not employee:
            return
        default_esic = employee._evaluate_default_esic_applicable(
            gross_wage=self.wage,
            eval_date=self.date_start or fields.Date.today()
        )
        employee.write({'hds_in_esic_applicable': default_esic})

    def _estimate_statutory_rule_amount(self, contract, rule):
        code_text = rule.amount_python_compute or ''
        wage = contract.wage or 0.0
        pf_wage = min(wage, 15000.0)
        if 'compute_employer_total_pf' in code_text:
            return pf_wage * 0.12
        elif 'compute_employer_epf_share' in code_text or 'compute_employer_epf' in code_text:
            return (pf_wage * 0.12) - min(wage * 0.0833, 1250.0)
        elif 'compute_employer_eps' in code_text:
            return min(wage * 0.0833, 1250.0)
        elif 'compute_employer_edli' in code_text:
            return pf_wage * 0.005
        elif 'compute_epf_admin' in code_text:
            return pf_wage * 0.005
        return 0.0
