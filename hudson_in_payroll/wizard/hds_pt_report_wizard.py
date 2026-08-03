# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.fields import Date


class HdsPtReportWizard(models.TransientModel):
    """
    Unified Professional Tax (PT) Report Generator Wizard.
    Launches and filters the 14 PT statutory report types.
    """
    _name = 'hds.pt.report.wizard'
    _description = 'Professional Tax Report Generator Wizard'

    report_type = fields.Selection([
        ('register', 'Professional Tax Register'),
        ('statement', 'Employee PT Statement'),
        ('monthly_summary', 'Monthly PT Summary'),
        ('state_summary', 'State-wise PT Summary'),
        ('company_summary', 'Company-wise PT Summary'),
        ('slab_utilization', 'Salary Slab Utilization Report'),
        ('override_month', 'PT Override Month Report'),
        ('exception', 'PT Exception Report'),
        ('compliance_audit', 'PT Compliance Audit Report'),
        ('reconciliation', 'PT Reconciliation Report'),
        ('revision_impact', 'Salary Revision Impact Report'),
        ('state_mapping', 'Employee State Mapping Report'),
        ('liability_summary', 'PT Liability Summary'),
        ('config_audit', 'Professional Tax Configuration Audit'),
    ], string="Report Type", required=True, default='register')

    title = fields.Char(string="Report Title", default="Professional Tax Report")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    state_id = fields.Many2one('res.country.state', string="Work State", domain="[('country_id.code', '=', 'IN')]")
    employee_id = fields.Many2one('hr.employee', string="Employee Filter")
    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    def action_generate_pt_report(self):
        self.ensure_one()
        action = self.env.ref('hudson_in_payroll.action_hds_in_pt_statutory_report').read()[0]
        domain = [('statutory_module', '=', 'pt')]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        if self.date_from:
            domain.append(('calculation_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('calculation_date', '<=', self.date_to))
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        
        action['domain'] = domain
        action['name'] = self.title or self.report_type.replace('_', ' ').title()
        return action

    def action_open_pivot_graph(self):
        self.ensure_one()
        action = self.env.ref('hudson_in_payroll.action_hds_in_pt_statutory_report').read()[0]
        domain = [('statutory_module', '=', 'pt')]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        if self.date_from:
            domain.append(('calculation_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('calculation_date', '<=', self.date_to))
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        
        action['domain'] = domain
        action['name'] = f"{self.title or self.report_type.replace('_', ' ').title()} - Pivot & Graphical Analysis"
        action['view_mode'] = 'pivot,graph,list,kanban,form'
        action['views'] = [
            (self.env.ref('hudson_in_payroll.hds_in_statutory_report_view_pivot').id, 'pivot'),
            (self.env.ref('hudson_in_payroll.hds_in_statutory_report_view_graph').id, 'graph'),
            (self.env.ref('hudson_in_payroll.hds_in_statutory_report_view_tree').id, 'list'),
            (self.env.ref('hudson_in_payroll.hds_in_statutory_report_view_kanban').id, 'kanban'),
            (self.env.ref('hudson_in_payroll.hds_in_statutory_report_view_form').id, 'form'),
        ]
        return action

    def action_export_excel(self):
        self.ensure_one()
        import io
        import base64
        import xlsxwriter

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Professional Tax Report')

        title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'bg_color': '#1f497d', 'font_color': '#ffffff'})
        sub_title_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center', 'bg_color': '#dce6f1'})
        header_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center', 'bg_color': '#366092', 'font_color': '#ffffff', 'border': 1})
        cell_fmt = workbook.add_format({'font_size': 9, 'border': 1})
        num_fmt = workbook.add_format({'font_size': 9, 'border': 1, 'num_format': '#,##0.00'})
        total_fmt = workbook.add_format({'bold': True, 'font_size': 10, 'border': 1, 'num_format': '#,##0.00', 'bg_color': '#d9d9d9'})

        report_title = self.title or self.report_type.replace('_', ' ').title()
        comp_name = self.company_id.name if self.company_id else 'Hudson HRMS'

        worksheet.merge_range('A1:H1', f"{comp_name} - {report_title}", title_fmt)
        date_str = f"Period: {self.date_from or 'All'} to {self.date_to or 'All'}"
        worksheet.merge_range('A2:H2', date_str, sub_title_fmt)

        headers = ['Sr.', 'Employee ID', 'Employee Name', 'Work Location / State', 'Payslip Period', 'Gross Salary (Rs)', 'PT Deduction (Rs)', 'Status']
        for col_num, header in enumerate(headers):
            worksheet.write(3, col_num, header, header_fmt)

        domain = [('statutory_module', '=', 'pt')]
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        if self.date_from:
            domain.append(('calculation_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('calculation_date', '<=', self.date_to))
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))

        records = self.env['hds.in.statutory.report'].search(domain)

        row = 4
        total_gross = 0.0
        total_pt = 0.0

        for idx, rec in enumerate(records, start=1):
            emp_name = rec.employee_id.name if rec.employee_id else ''
            emp_code = rec.employee_code or getattr(rec.employee_id, 'registration_number', '') or ''
            st_name = rec.state_id.name if rec.state_id else (rec.employee_id.work_location_id.address_id.state_id.name if (rec.employee_id and rec.employee_id.work_location_id and rec.employee_id.work_location_id.address_id) else '')
            period_str = f"{rec.date_from or ''} to {rec.date_to or ''}"
            gross = getattr(rec.payslip_id, 'gross_wage', 0.0) or getattr(rec.payslip_id, 'wage', 0.0) or 0.0
            pt_amt = rec.statutory_amount or 0.0

            total_gross += gross
            total_pt += pt_amt

            worksheet.write(row, 0, idx, cell_fmt)
            worksheet.write(row, 1, emp_code, cell_fmt)
            worksheet.write(row, 2, emp_name, cell_fmt)
            worksheet.write(row, 3, st_name, cell_fmt)
            worksheet.write(row, 4, period_str, cell_fmt)
            worksheet.write(row, 5, gross, num_fmt)
            worksheet.write(row, 6, pt_amt, num_fmt)
            worksheet.write(row, 7, (rec.status or 'success').upper(), cell_fmt)
            row += 1

        worksheet.write(row, 0, 'TOTAL', total_fmt)
        for c in range(1, 5):
            worksheet.write(row, c, '', total_fmt)
        worksheet.write(row, 5, total_gross, total_fmt)
        worksheet.write(row, 6, total_pt, total_fmt)
        worksheet.write(row, 7, '', total_fmt)

        worksheet.set_column('A:A', 6)
        worksheet.set_column('B:B', 14)
        worksheet.set_column('C:C', 24)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 22)
        worksheet.set_column('F:G', 16)
        worksheet.set_column('H:H', 12)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        file_name = f"PT_Report_{self.report_type}_{self.date_to or 'all'}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'hds.pt.report.wizard',
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
