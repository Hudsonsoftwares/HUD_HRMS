# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models


class HrPayslip(models.Model):
    """Class for the inherited model hr_payslip. Supering get_inputs() method
        inorder to add details of advance salary in the payslip."""
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """Supering get_inputs() method inorder to add details of advance
           salary in the payslip."""
        res = super(HrPayslip, self).get_inputs(contract_ids, date_from,
                                                date_to)
        employee_id = self.env['hr.version'].browse(
            contract_ids[0].id).employee_id if contract_ids \
            else self.employee_id
        advance_salary = self.env['salary.advance'].search(
            [('employee_id', '=', employee_id.id), ('state', '=', 'approve')])
        total_advance = 0.0
        for record in advance_salary:
            if (record.advance and record.date and
                    record.date.year == date_from.year and
                    record.date.month == date_from.month):
                total_advance += record.advance
        if total_advance:
            sar_found = False
            for result in res:
                if result.get('code') == 'SAR':
                    result['amount'] = total_advance
                    sar_found = True
                    break
            if not sar_found:
                res.append({
                    'name': 'Salary Advance',
                    'code': 'SAR',
                    'amount': total_advance,
                    'contract_id': contract_ids[0].id if contract_ids else False,
                    'date_from': date_from,
                    'date_to': date_to,
                })
        return res
