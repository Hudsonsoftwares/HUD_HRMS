# -*- coding: utf-8 -*-
from odoo import api, fields, models
import re

class FinancialReport(models.TransientModel):
    _inherit = 'financial.report'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': self.account_report_id.name or 'Financial Report',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def _check_unposted_entries(self, form_data):
        if form_data.get('target_move') == 'posted':
            domain = [('state', '=', 'draft')]
            if form_data.get('date_to'):
                domain.append(('date', '<=', form_data['date_to']))
            return self.env['account.move'].search_count(domain) > 0
        return False

    def get_report_data(self):
        self.ensure_one()
        data = self._financial_report_data()
        report_lines = self.get_account_lines(data['form'])
        
        currency_id = self._get_currency()
        currency = self.env['res.currency'].browse(currency_id) if isinstance(currency_id, int) else False
        currency_symbol = currency.symbol if currency else (currency_id or '$')
        
        has_unposted = self._check_unposted_entries(data['form'])
        
        return {
            'report_name': self.account_report_id.name or 'Financial Report',
            'report_lines': report_lines,
            'debit_credit': self.debit_credit,
            'enable_filter': self.enable_filter,
            'currency_symbol': currency_symbol,
            'has_unposted': has_unposted,
            'wizard_model': self._name,
            'wizard_id': self.id,
            'form_data': data['form'],
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        wizard_data = self._financial_report_data()
        items = self.find_journal_items([line_data], wizard_data['form'])
        for item in items:
            if item.get('partner_id'):
                partner = self.env['res.partner'].browse(item['partner_id'])
                item['partner_name'] = partner.name
            else:
                item['partner_name'] = ''
        return items
