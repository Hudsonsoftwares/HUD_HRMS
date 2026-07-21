# -*- coding: utf-8 -*-
from odoo import api, fields, models
import re

class CashFlowReport(models.TransientModel):
    _inherit = 'cash.flow.report'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': self.account_report_id.name or 'Cash Flow Report',
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
        # Build form data dict
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(
                ['date_from', 'date_to', 'target_move', 'journal_ids',
                 'company_id', 'debit_credit', 'enable_filter', 'label_filter',
                 'filter_cmp', 'date_from_cmp', 'date_to_cmp', 'account_report_id'])[0]
        }
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(
            used_context,
            lang=self.env.context.get('lang') or 'en_US')
        
        if self.enable_filter:
            data['form']['comparison_context'] = self._build_comparison_context(data)
            
        report_lines = self.env['report.base_accounting_kit.report_cash_flow'].get_account_lines(data['form'])
        
        currency_id = self.env.company.currency_id
        currency_symbol = currency_id.symbol if currency_id else '$'
        
        has_unposted = self._check_unposted_entries(data['form'])
        
        return {
            'report_name': self.account_report_id.name or 'Cash Flow Statement',
            'report_lines': report_lines,
            'debit_credit': self.debit_credit,
            'enable_filter': self.enable_filter,
            'currency_symbol': currency_symbol,
            'has_unposted': has_unposted,
            'wizard_model': self._name,
            'wizard_id': self.id,
            'form_data': data['form'],
        }

    def find_journal_items(self, report_lines, form):
        # Implement standard find_journal_items for cash flow statement accounts
        cr = self.env.cr
        journal_items = []
        for i in report_lines:
            if i.get('type') == 'account':
                account = i['account']
                if form.get('target_move') == 'posted':
                    search_query = ("select aml.id, am.id as j_id, "
                                    "aml.account_id, aml.date, aml.name as "
                                    "label, am.name, (aml.debit-aml.credit) as "
                                    "balance, aml.debit, aml.credit, "
                                    "aml.partner_id  from "
                                    "account_move_line aml "
                                    "join account_move am on (aml.move_id=am.id"
                                    " and am.state=%s) where aml.account_id=%s")
                    vals = [form['target_move']]
                else:
                    search_query = ("select aml.id, am.id as j_id, "
                                    "aml.account_id, aml.date, aml.name as "
                                    "label, am.name, (aml.debit-aml.credit) as "
                                    "balance, aml.debit, aml.credit, "
                                    "aml.partner_id from account_move_line aml"
                                    " join account_move am on "
                                    "(aml.move_id=am.id) where "
                                    "aml.account_id=%s")
                    vals = []
                # Handle dates from common report fields
                if form.get('date_from') and form.get('date_to'):
                    search_query += " and aml.date>=%s and aml.date<=%s"
                    vals += [account, form['date_from'], form['date_to']]
                elif form.get('date_from'):
                    search_query += " and aml.date>=%s"
                    vals += [account, form['date_from']]
                elif form.get('date_to'):
                    search_query += " and aml.date<=%s"
                    vals += [account, form['date_to']]
                else:
                    vals += [account]
                cr.execute(search_query, tuple(vals))
                items = cr.dictfetchall()

                for j in items:
                    temp = j['id']
                    j['id'] = re.sub('[^0-9a-zA-Z]+', '', i['name']) + str(
                        temp)
                    j['p_id'] = str(i['a_id'])
                    j['type'] = 'journal_item'
                    journal_items.append(j)
        return journal_items

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        # Build form data dict
        data = {
            'ids': self.env.context.get('active_ids', []),
            'model': self.env.context.get('active_model', 'ir.ui.menu'),
            'form': self.read(
                ['date_from', 'date_to', 'target_move', 'journal_ids',
                 'company_id', 'debit_credit', 'enable_filter', 'label_filter',
                 'filter_cmp', 'date_from_cmp', 'date_to_cmp', 'account_report_id'])[0]
        }
        items = self.find_journal_items([line_data], data['form'])
        for item in items:
            if item.get('partner_id'):
                partner = self.env['res.partner'].browse(item['partner_id'])
                item['partner_name'] = partner.name
            else:
                item['partner_name'] = ''
        return items
