# -*- coding: utf-8 -*-
import base64
import io
from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class HdsPfEcrWizard(models.TransientModel):
    _name = 'hds.pf.ecr.wizard'
    _inherit = 'hds.pf.report.wizard.base'
    _description = 'EPFO ECR Export Wizard'

    name = fields.Char(string='Report Name', compute='_compute_name', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
    ], string='State', default='draft')

    txt_file = fields.Binary(string='ECR Text File (.txt)', readonly=True)
    txt_filename = fields.Char(string='Text Filename', readonly=True)
    xlsx_file = fields.Binary(string='ECR Excel File (.xlsx)', readonly=True)
    xlsx_filename = fields.Char(string='Excel Filename', readonly=True)

    record_count = fields.Integer(string='Total Employees', readonly=True)
    total_epf_wages = fields.Float(string='Total EPF Wages', readonly=True)
    total_epf_deduction = fields.Float(string='Total Employee EPF', readonly=True)
    total_eps_contribution = fields.Float(string='Total Employer EPS', readonly=True)
    total_epf_er_contribution = fields.Float(string='Total Employer EPF', readonly=True)

    @api.depends('month', 'year')
    def _compute_name(self):
        month_dict = dict(self._fields['month'].selection)
        for rec in self:
            m_label = month_dict.get(rec.month, '')
            rec.name = f"EPF-ECR Report / {m_label}-{rec.year}"

    def action_generate_ecr(self):
        self.ensure_one()
        payslips = self._get_confirmed_payslips([('employee_id.hds_in_epf_applicable', '=', True)])

        if not payslips:
            raise UserError(_("No confirmed payslips found for EPF-applicable employees in the selected period (%s).") % self._get_month_label())

        missing_uan_employees = payslips.filtered(lambda p: not p.employee_id.hds_in_uan).mapped('employee_id.name')
        if missing_uan_employees:
            unique_missing = sorted(list(set(missing_uan_employees)))
            raise UserError(_(
                "Cannot generate EPFO ECR File. The following EPF-applicable employee(s) are missing a UAN:\n\n - %s\n\n"
                "EPFO rejects ECR files with missing UANs. Please populate UAN on employee profile(s) before export."
            ) % ("\n - ".join(unique_missing)))

        date_from, date_to = self._get_date_range()
        eps_ceiling = self.env['hr.rule.parameter'].get_pf_parameter('EPS_WAGE_CEILING', date=date_to)

        ecr_rows = []
        tot_wages = 0.0
        tot_ee_epf = 0.0
        tot_er_eps = 0.0
        tot_er_epf = 0.0

        for payslip in payslips:
            emp = payslip.employee_id
            uan = emp.hds_in_uan or ''
            member_name = emp.name or ''

            pf_vals = self._get_pf_line_amounts(payslip)

            gross_line = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
            gross_wages = gross_line.total if gross_line else (payslip.contract_id.wage if payslip.contract_id else 0.0)

            epf_wages = pf_vals['pf_wage']
            eps_wages = min(epf_wages, eps_ceiling) if emp.hds_in_eps_applicable else 0.0

            ee_epf = pf_vals['ee_epf']
            er_epf = pf_vals['er_epf']
            er_eps = pf_vals['er_eps']

            ncp_days = 0
            if payslip.hds_snapshot_id:
                ncp_days = int(payslip.hds_snapshot_id.lop_days or 0)
            else:
                unpaid_lines = payslip.worked_days_line_ids.filtered(lambda l: l.code == 'UNPAID')
                ncp_days = int(sum(unpaid_lines.mapped('number_of_days')) if unpaid_lines else 0)

            refund_advances = 0

            ecr_rows.append({
                'uan': uan,
                'name': member_name,
                'gross': round(gross_wages, 2),
                'epf_wages': round(epf_wages, 2),
                'eps_wages': round(eps_wages, 2),
                'ee_epf': round(ee_epf, 2),
                'er_epf': round(er_epf, 2),
                'er_eps': round(er_eps, 2),
                'ncp_days': ncp_days,
                'refund': refund_advances,
            })

            tot_wages += epf_wages
            tot_ee_epf += ee_epf
            tot_er_eps += er_eps
            tot_er_epf += er_epf

        txt_lines = []
        for row in ecr_rows:
            line = f"{row['uan']}#~#{row['name']}#~#{int(round(row['gross']))}#~#{int(round(row['epf_wages']))}#~#{int(round(row['eps_wages']))}#~#{int(round(row['ee_epf']))}#~#{int(round(row['er_epf']))}#~#{int(round(row['er_eps']))}#~#{row['ncp_days']}#~#{row['refund']}"
            txt_lines.append(line)
        txt_content = "\n".join(txt_lines)

        month_label = self._get_month_label().replace('-', '_')
        txt_filename = f"EPFO_ECR_{month_label}.txt"
        xlsx_filename = f"EPFO_ECR_{month_label}.xlsx"

        output = io.BytesIO()
        if xlsxwriter:
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('EPF ECR')
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': '#FFFFFF', 'border': 1})
            num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
            text_fmt = workbook.add_format({'border': 1})

            headers = [
                'UAN', 'Member Name', 'Gross Wages', 'EPF Wages', 'EPS Wages',
                'Employee EPF Contribution', 'Employer EPF Contribution',
                'Employer EPS Contribution', 'NCP Days', 'Refund of Advances'
            ]
            for col_idx, text in enumerate(headers):
                sheet.write(0, col_idx, text, header_fmt)

            for row_idx, r in enumerate(ecr_rows, start=1):
                sheet.write(row_idx, 0, r['uan'], text_fmt)
                sheet.write(row_idx, 1, r['name'], text_fmt)
                sheet.write(row_idx, 2, r['gross'], num_fmt)
                sheet.write(row_idx, 3, r['epf_wages'], num_fmt)
                sheet.write(row_idx, 4, r['eps_wages'], num_fmt)
                sheet.write(row_idx, 5, r['ee_epf'], num_fmt)
                sheet.write(row_idx, 6, r['er_epf'], num_fmt)
                sheet.write(row_idx, 7, r['er_eps'], num_fmt)
                sheet.write(row_idx, 8, r['ncp_days'], text_fmt)
                sheet.write(row_idx, 9, r['refund'], text_fmt)

            workbook.close()
            output.seek(0)
            xlsx_content = output.read()
        else:
            xlsx_content = txt_content.encode('utf-8')

        self.write({
            'state': 'generated',
            'txt_file': base64.b64encode(txt_content.encode('utf-8')),
            'txt_filename': txt_filename,
            'xlsx_file': base64.b64encode(xlsx_content),
            'xlsx_filename': xlsx_filename,
            'record_count': len(ecr_rows),
            'total_epf_wages': tot_wages,
            'total_epf_deduction': tot_ee_epf,
            'total_eps_contribution': tot_er_eps,
            'total_epf_er_contribution': tot_er_epf,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
