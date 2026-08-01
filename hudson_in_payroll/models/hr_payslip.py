# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ..services.epf.epf_service import EPFService
from ..services.esic.esic_service import ESICService
from ..services.lwf.lwf_service import LWFService


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # Transient in-memory dictionary cache for active payslip evaluation contexts
    _eval_contexts = {}

    # -------------------------------------------------------------------------
    # STATUTORY CONTEXT INJECTION HOOK
    # -------------------------------------------------------------------------
    def _get_statutory_context(self, localdict):
        """
        Extensible hook to inject domain services and actual recordsets into localdict.
        Stores localdict in HrPayslip._eval_contexts[self.id]
        so that payslip_record.hds_in_compute_*() calls require ZERO parameters in XML.
        
        Future localization modules (ESIC, PT, LWF, TDS) extend this hook via super().
        """
        self.ensure_one()
        HrPayslip._eval_contexts[self.id] = localdict
        localdict.update({
            'epf_service': EPFService(self.env, localdict=localdict),
            'esic_service': ESICService(self.env, localdict=localdict),
            'lwf_service': LWFService(self.env, localdict=localdict),
            'payslip_record': self,
        })
        return localdict

    # -------------------------------------------------------------------------
    # OVERRIDDEN GET_PAYSLIP_LINES
    # -------------------------------------------------------------------------
    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        """
        Overridden to inject domain services and real hr.payslip record into localdict.
        """
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = (
                localdict['categories'].dict[category.code] + amount
                if category.code in localdict['categories'].dict else amount
            )
            return localdict

        class DummyInput(object):
            amount = 0.0
            number_of_days = 0.0
            number_of_hours = 0.0

        class BrowsableObject(object):
            def __init__(self, employee_id, dict_val, env):
                self.employee_id = employee_id
                self.dict = dict_val
                self.env = env
                self.amount = 0.0

            def __contains__(self, attr):
                if isinstance(self.dict, dict):
                    return attr in self.dict
                return hasattr(self.dict, attr)

            def __getitem__(self, attr):
                if isinstance(self.dict, dict):
                    return self.dict.get(attr, DummyInput())
                return getattr(self.dict, attr, DummyInput())

            def __getattr__(self, attr):
                if isinstance(self.dict, dict):
                    return self.dict.get(attr, DummyInput())
                return getattr(self.dict, attr, DummyInput())

        class InputLine(BrowsableObject):
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                    FROM hr_payslip as hp, hr_payslip_line as pl
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)

        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {
            'categories': categories,
            'rules': rules,
            'payslip': payslips,
            'worked_days': worked_days,
            'inputs': inputs
        }

        contracts = self.env['hr.version'].browse(contract_ids)
        if payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        elif len(contracts) == 1 and contracts.struct_id:
            structure_ids = list(set(contracts.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()

        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        try:
            for contract in contracts:
                employee = contract.employee_id
                localdict = dict(baselocaldict, employee=employee, contract=contract)

                # INJECTION HOOK: Inject epf_service and payslip_record into localdict & store _eval_contexts
                localdict = payslip._get_statutory_context(localdict)

                for rule in sorted_rules:
                    key = rule.code + '-' + str(contract.id)
                    localdict['result'] = None
                    localdict['result_qty'] = 1.0
                    localdict['result_rate'] = 100

                    if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                        amount, qty, rate = rule._compute_rule(localdict)
                        previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                        tot_rule = (amount * qty * rate / 100.0)
                        localdict[rule.code] = tot_rule
                        rules_dict[rule.code] = rule
                        localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                        result_dict[key] = {
                            'salary_rule_id': rule.id,
                            'contract_id': contract.id,
                            'name': rule.name,
                            'code': rule.code,
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'condition_select': rule.condition_select,
                            'condition_python': rule.condition_python,
                            'condition_range': rule.condition_range,
                            'condition_range_min': rule.condition_range_min,
                            'condition_range_max': rule.condition_range_max,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_python_compute': rule.amount_python_compute,
                            'amount_percentage': rule.amount_percentage,
                            'amount_percentage_base': rule.amount_percentage_base,
                            'register_id': rule.register_id.id,
                            'amount': amount,
                            'employee_id': contract.employee_id.id,
                            'quantity': qty,
                            'rate': rate,
                        }
                    else:
                        blacklist += [id for id, seq in rule._recursive_search_of_rules()]
        finally:
            # Clean up transient context after computation
            HrPayslip._eval_contexts.pop(payslip_id, None)

        return list(result_dict.values())

    # -------------------------------------------------------------------------
    # PRIVATE STATUTORY DELEGATION HELPERS
    # -------------------------------------------------------------------------
    def _get_payroll_eval_context(self, raise_if_missing=True):
        """
        Safely retrieves the transient evaluation context (_eval_context)
        bound during _get_payslip_lines execution.
        Raises UserError if executed outside active payslip sheet computation.
        """
        self.ensure_one()
        eval_ctx = HrPayslip._eval_contexts.get(self.id)
        if not eval_ctx and raise_if_missing:
            raise UserError(_(
                "Statutory calculation methods on 'hr.payslip' can only be executed "
                "during active payslip sheet computation."
            ))
        return eval_ctx

    def _delegate_statutory_service(self, service_class, compute_method_name, negate=False):
        """
        Generic DRY helper to instantiate statutory service facades with evaluation context
        and delegate computation cleanly without repeating validation logic.
        """
        self.ensure_one()
        eval_ctx = self._get_payroll_eval_context(raise_if_missing=True)
        service = service_class(self.env, localdict=eval_ctx)
        compute_fn = getattr(service, compute_method_name)
        amount = compute_fn(self)
        return -amount if negate else amount

    # -------------------------------------------------------------------------
    # PUBLIC ORCHESTRATION API FOR SALARY RULES (Zero Arguments in XML)
    # -------------------------------------------------------------------------
    def hds_in_compute_pf_wage(self):
        """Public API entrypoint for PF_WAGE Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(EPFService, 'compute_pf_wage')

    def hds_in_compute_employee_epf(self):
        """Public API entrypoint for Employee EPF Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(EPFService, 'compute_employee_epf', negate=True)

    def hds_in_compute_employer_total_pf(self):
        """Public API entrypoint for Total Employer PF Contribution (12% = ₹2,040)."""
        return self._delegate_statutory_service(EPFService, 'compute_employer_total_pf')

    def hds_in_compute_employer_epf_share(self):
        """Public API entrypoint for Net Employer EPF Share (12% - EPS = ₹790)."""
        return self._delegate_statutory_service(EPFService, 'compute_employer_epf_share')

    def hds_in_compute_employer_epf(self):
        """Backward compatible entrypoint for Net Employer EPF Share (₹790)."""
        return self._delegate_statutory_service(EPFService, 'compute_employer_epf')

    def hds_in_compute_employer_eps(self):
        """Public API entrypoint for Employer Pension Scheme (EPS) Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(EPFService, 'compute_employer_eps')

    def hds_in_compute_employer_edli(self):
        """Public API entrypoint for Employer EDLI Contribution Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(EPFService, 'compute_employer_edli')

    def hds_in_compute_epf_admin(self):
        """Public API entrypoint for EPF Admin Charges Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(EPFService, 'compute_epf_admin')

    def hds_in_compute_edli_admin(self):
        """Public API entrypoint for EDLI Admin Charges Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(EPFService, 'compute_edli_admin')

    def hds_in_compute_epf_admin_charge(self):
        """Alias for hds_in_compute_epf_admin for backward compatibility."""
        return self.hds_in_compute_epf_admin()

    def hds_in_compute_edli_admin_charge(self):
        """Alias for hds_in_compute_edli_admin for backward compatibility."""
        return self.hds_in_compute_edli_admin()

    # -------------------------------------------------------------------------
    # PUBLIC ESIC ORCHESTRATION API FOR SALARY RULES (Zero Arguments in XML)
    # -------------------------------------------------------------------------
    def hds_in_compute_esic_wage(self):
        """Public API entrypoint for ESIC_WAGE Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(ESICService, 'compute_esic_wage')

    def hds_in_compute_esic_employee(self):
        """Public API entrypoint for ESIC_EE Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(ESICService, 'compute_esic_employee', negate=True)

    def hds_in_compute_esic_employer(self):
        """Public API entrypoint for ESIC_ER Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(ESICService, 'compute_esic_employer')

    # -------------------------------------------------------------------------
    # PUBLIC LWF ORCHESTRATION API FOR SALARY RULES (Zero Arguments in XML)
    # -------------------------------------------------------------------------
    def hds_in_compute_lwf_employee(self):
        """Public API entrypoint for LWF_EE Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(LWFService, 'compute_lwf_employee', negate=True)

    def hds_in_compute_lwf_employer(self):
        """Public API entrypoint for LWF_ER Salary Rule (Zero arguments)."""
        return self._delegate_statutory_service(LWFService, 'compute_lwf_employer')

    # -------------------------------------------------------------------------
    # WAGE RESOLUTION HELPERS
    # -------------------------------------------------------------------------
    def hds_in_get_actual_pf_wage(self, localdict=None):
        """
        Calculates actual PF-eligible wage by summing components with hds_in_include_in_pf_wage = True.
        Does NOT read localdict['PF_WAGE'] to prevent circular dependency.
        """
        import logging
        _logger = logging.getLogger(__name__)

        self.ensure_one()
        ld = localdict or self._get_payroll_eval_context(raise_if_missing=False)
        pf_wage = 0.0

        if ld:
            pf_rules = self.env['hr.salary.rule'].search([
                ('hds_in_include_in_pf_wage', '=', True)
            ])
            for rule in pf_rules:
                amount = float(ld.get(rule.code, 0.0) or 0.0)
                _logger.info("PF Rule %s -> %s", rule.code, amount)
                pf_wage += amount
            return pf_wage

        for line in self.line_ids:
            if line.salary_rule_id.hds_in_include_in_pf_wage:
                pf_wage += line.total

        return pf_wage

    def get_pf_eligible_wage(self, localdict=None):
        """Alias for hds_in_get_actual_pf_wage for backwards compatibility."""
        return self.hds_in_get_actual_pf_wage(localdict=localdict)

    def hds_in_get_pf_contribution_wage(self, localdict=None):
        """Calculates employee's PF Contribution Wage for this payslip."""
        self.ensure_one()
        ld = localdict or self._get_payroll_eval_context(raise_if_missing=False)
        return EPFService(self.env, localdict=ld).wage_calc.get_pf_contribution_wage(self)

    def get_pf_contribution_wage(self, localdict=None):
        """Alias for hds_in_get_pf_contribution_wage for backwards compatibility."""
        return self.hds_in_get_pf_contribution_wage(localdict=localdict)

    hds_in_statutory_audit_count = fields.Integer(
        string="Statutory Audits",
        compute='_compute_hds_in_statutory_audit_count'
    )

    def _compute_hds_in_statutory_audit_count(self):
        audit_data = self.env['hds.in.payroll.audit'].read_group(
            [('payslip_id', 'in', self.ids)],
            ['payslip_id'],
            ['payslip_id']
        )
        mapped_data = {data['payslip_id'][0]: data['payslip_id_count'] for data in audit_data}
        for slip in self:
            slip.hds_in_statutory_audit_count = mapped_data.get(slip.id, 0)

    def action_view_statutory_audits(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hudson_in_payroll.hds_in_payroll_audit_action")
        action['domain'] = [('payslip_id', '=', self.id)]
        action['context'] = {'default_payslip_id': self.id, 'default_employee_id': self.employee_id.id}
        return action

    def action_compute_sheet(self):
        """Auto-sync BONUS input lines before computing salary rules."""
        for slip in self:
            if slip.state == 'draft' and slip.contract_id and slip.employee_id:
                bonus_lines = self.env['hds.in.bonus.line'].search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('bonus_id.payment_method', '=', 'monthly_payroll'),
                    ('bonus_id.state', 'in', ('manager_approved', 'hr_approved', 'approved', 'processed', 'paid')),
                    ('bonus_id.date_from', '<=', slip.date_to),
                    ('bonus_id.date_to', '>=', slip.date_from),
                    ('amount', '>', 0.0)
                ])
                for b_line in bonus_lines:
                    input_line = slip.input_line_ids.filtered(lambda i: i.code == 'BONUS')
                    if input_line:
                        input_line.write({'amount': b_line.amount, 'name': b_line.bonus_id.name})
                    else:
                        self.env['hr.payslip.input'].create({
                            'name': b_line.bonus_id.name,
                            'code': 'BONUS',
                            'amount': b_line.amount,
                            'payslip_id': slip.id,
                            'contract_id': slip.contract_id.id,
                            'date_from': slip.date_from,
                            'date_to': slip.date_to,
                        })
        return super(HrPayslip, self).action_compute_sheet()

    def compute_sheet(self):
        """Alias for action_compute_sheet for backwards compatibility."""
        return self.action_compute_sheet()

    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_inputs(contracts, date_from, date_to)
        for contract in contracts:
            emp = contract.employee_id
            bonus_lines = self.env['hds.in.bonus.line'].search([
                ('employee_id', '=', emp.id),
                ('bonus_id.payment_method', '=', 'monthly_payroll'),
                ('bonus_id.state', 'in', ('manager_approved', 'hr_approved', 'approved', 'processed', 'paid')),
                '|',
                '&', ('bonus_id.date_from', '<=', date_to), ('bonus_id.date_to', '>=', date_from),
                '&', ('bonus_id.payment_date', '>=', date_from), ('bonus_id.payment_date', '<=', date_to),
                ('amount', '>', 0.0)
            ])
            for b_line in bonus_lines:
                existing = [i for i in res if i.get('code') == 'BONUS' and i.get('contract_id') == contract.id]
                if existing:
                    existing[0]['amount'] = b_line.amount
                    existing[0]['name'] = b_line.bonus_id.name
                else:
                    res.append({
                        'name': b_line.bonus_id.name,
                        'code': 'BONUS',
                        'amount': b_line.amount,
                        'contract_id': contract.id,
                        'date_from': date_from,
                        'date_to': date_to,
                    })
        return res

