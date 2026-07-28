# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ..services.epf.epf_service import EPFService


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # -------------------------------------------------------------------------
    # STATUTORY CONTEXT INJECTION HOOK
    # -------------------------------------------------------------------------
    def _get_statutory_context(self, localdict):
        """
        Extensible hook to inject domain services and actual recordsets into localdict.
        Future localization modules (ESIC, PT, LWF, TDS) extend this hook via super().
        """
        self.ensure_one()
        localdict.update({
            'epf_service': EPFService(self.env, localdict=localdict),
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

        class BrowsableObject(object):
            def __init__(self, employee_id, dict_val, env):
                self.employee_id = employee_id
                self.dict = dict_val
                self.env = env

            def __getattr__(self, attr):
                return self.dict.__getitem__(attr) if attr in self.dict else 0.0

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

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)

            # INJECTION HOOK: Inject epf_service and payslip_record into localdict
            localdict = payslip._get_statutory_context(localdict)

            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100

                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    amount, qty, rate = rule._compute_rule(localdict)

                    if rule.code == "EPF":
                        print("\n" + "=" * 60)
                        print("EPF RULE EXECUTED")
                        print("Rule ID:", rule.id)
                        print("Rule Name:", rule.name)
                        print("Amount:", amount)
                        print("Qty:", qty)
                        print("Rate:", rate)
                        print("Total:", amount * qty * rate / 100.0)
                        print("=" * 60)

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

        return list(result_dict.values())

    # -------------------------------------------------------------------------
    # PUBLIC ORCHESTRATION API FOR SALARY RULES
    # -------------------------------------------------------------------------
    def hds_in_compute_employee_epf(self, localdict=None):
        """Public API entrypoint for Employee EPF Salary Rule."""
        self.ensure_one()
        amount = EPFService(self.env).compute_employee_epf(self, localdict=localdict)
        return -amount

    def hds_in_compute_employer_epf(self, localdict=None):
        """Public API entrypoint for Employer EPF Share Salary Rule."""
        self.ensure_one()
        return EPFService(self.env).compute_employer_epf(self, localdict=localdict)

    def hds_in_compute_employer_eps(self, localdict=None):
        """Public API entrypoint for Employer Pension Scheme (EPS) Salary Rule."""
        self.ensure_one()
        return EPFService(self.env).compute_employer_eps(self, localdict=localdict)

    def hds_in_compute_employer_edli(self, localdict=None):
        """Public API entrypoint for EDLI Contribution Salary Rule."""
        self.ensure_one()
        return EPFService(self.env).compute_employer_edli(self, localdict=localdict)

    def hds_in_compute_epf_admin(self, localdict=None):
        """Public API entrypoint for EPF Admin Charges Salary Rule."""
        self.ensure_one()
        return EPFService(self.env).compute_epf_admin(self, localdict=localdict)

    def hds_in_compute_edli_admin(self, localdict=None):
        """Public API entrypoint for EDLI Admin Charges Salary Rule."""
        self.ensure_one()
        return EPFService(self.env).compute_edli_admin(self, localdict=localdict)

    # -------------------------------------------------------------------------
    # WAGE RESOLUTION HELPERS
    # -------------------------------------------------------------------------
    def hds_in_get_actual_pf_wage(self, localdict=None):
        """Calculates actual PF-eligible wage by summing components with hds_in_include_in_pf_wage = True."""
        self.ensure_one()
        pf_wage = 0.0

        if localdict:
            rules_dict = {}
            if 'rules' in localdict and hasattr(localdict['rules'], 'dict'):
                rules_dict = localdict['rules'].dict
            elif 'rules' in localdict and isinstance(localdict['rules'], dict):
                rules_dict = localdict['rules']

            if rules_dict:
                rule_codes = list(rules_dict.keys())
                pf_rules = self.env['hr.salary.rule'].search([
                    ('code', 'in', rule_codes),
                    ('hds_in_include_in_pf_wage', '=', True)
                ])
                pf_rule_codes = set(pf_rules.mapped('code'))
                for code in pf_rule_codes:
                    rule_val = rules_dict.get(code)
                    if rule_val:
                        amt = getattr(rule_val, 'total', False)
                        if amt is False and isinstance(rule_val, dict):
                            amt = rule_val.get('total', 0.0)
                        if amt is False and isinstance(rule_val, (int, float)):
                            amt = float(rule_val)
                        pf_wage += (amt or 0.0)
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
        return EPFService(self.env).wage_calc.get_pf_contribution_wage(self, localdict=localdict)

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
