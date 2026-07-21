# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

class AccountDayBookReport(models.TransientModel):
    _inherit = 'account.day.book.report'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Day Book Report'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'account_ids', 'company_id'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')
            
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        accounts = self.env['account.account'].search([('id', 'in', data['form']['account_ids'])]) \
            if data['form']['account_ids'] else self.env['account.account'].search([])
        
        report_model = self.env['report.base_accounting_kit.day_book_report_template']
        
        report_lines = []
        date_start = datetime.strptime(data['form']['date_from'], '%Y-%m-%d').date()
        date_end = datetime.strptime(data['form']['date_to'], '%Y-%m-%d').date()
        days = (date_end - date_start).days

        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        for i in range(days + 1):
            day = date_start + timedelta(days=i)
            res = report_model.with_context(ctx)._get_account_move_entry(
                accounts, data['form'], day.strftime('%Y-%m-%d')
            )
            if res['lines']:
                parent_id = f"day_{day}"
                report_lines.append({
                    'id': parent_id,
                    'name': day.strftime('%Y-%m-%d'),
                    'parent': False,
                    'level': 1,
                    'type': 'report',
                    'debit': res['debit'],
                    'credit': res['credit'],
                    'balance': res['balance'],
                })
                for idx, line in enumerate(res['lines']):
                    report_lines.append({
                        'id': f"line_{line['lid']}",
                        'name': f"{line.get('accname') or ''} ({line.get('move_name') or ''})",
                        'parent': parent_id,
                        'level': 2,
                        'type': 'account',
                        'account': line.get('account_id'),
                        'debit': line.get('debit', 0.0),
                        'credit': line.get('credit', 0.0),
                        'balance': line.get('balance', 0.0),
                        'ref': line.get('lref') or '',
                        'label': line.get('lname') or '',
                    })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('Day Book Report'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        # Find underlying move lines for standard drilldown
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountCashBookReport(models.TransientModel):
    _inherit = 'account.cash.book.report'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Cash Book Report'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'display_account', 'account_ids', 'sortby', 'initial_balance', 'company_id'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_cash_book']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        accounts_res = report_values['Accounts']

        report_lines = []
        for acc in accounts_res:
            account_rec = self.env['account.account'].search([('code', '=', acc['code'])], limit=1)
            if not account_rec:
                continue
            parent_id = f"account_{account_rec.id}"
            report_lines.append({
                'id': parent_id,
                'name': f"{acc['code']} {acc['name']}",
                'parent': False,
                'level': 1,
                'type': 'report',
                'debit': acc['debit'],
                'credit': acc['credit'],
                'balance': acc['balance'],
            })
            for idx, line in enumerate(acc.get('move_lines', [])):
                report_lines.append({
                    'id': f"line_{idx}_{parent_id}",
                    'name': f"{line.get('ldate') or ''} - {line.get('lcode') or ''} ({line.get('move_name') or ''})",
                    'parent': parent_id,
                    'level': 2,
                    'type': 'account',
                    'account': account_rec.id,
                    'debit': line.get('debit', 0.0),
                    'credit': line.get('credit', 0.0),
                    'balance': line.get('balance', 0.0),
                    'ref': line.get('lref') or '',
                    'label': line.get('lname') or '',
                })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('Cash Book Report'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountBankBookReport(models.TransientModel):
    _inherit = 'account.bank.book.report'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Bank Book Report'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'display_account', 'account_ids', 'sortby', 'initial_balance', 'company_id'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_bank_book']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        accounts_res = report_values['Accounts']

        report_lines = []
        for acc in accounts_res:
            account_rec = self.env['account.account'].search([('code', '=', acc['code'])], limit=1)
            if not account_rec:
                continue
            parent_id = f"account_{account_rec.id}"
            report_lines.append({
                'id': parent_id,
                'name': f"{acc['code']} {acc['name']}",
                'parent': False,
                'level': 1,
                'type': 'report',
                'debit': acc['debit'],
                'credit': acc['credit'],
                'balance': acc['balance'],
            })
            for idx, line in enumerate(acc.get('move_lines', [])):
                report_lines.append({
                    'id': f"line_{idx}_{parent_id}",
                    'name': f"{line.get('ldate') or ''} - {line.get('lcode') or ''} ({line.get('move_name') or ''})",
                    'parent': parent_id,
                    'level': 2,
                    'type': 'account',
                    'account': account_rec.id,
                    'debit': line.get('debit', 0.0),
                    'credit': line.get('credit', 0.0),
                    'balance': line.get('balance', 0.0),
                    'ref': line.get('lref') or '',
                    'label': line.get('lname') or '',
                })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('Bank Book Report'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountReportPartnerLedger(models.TransientModel):
    _inherit = 'account.report.partner.ledger'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Partner Ledger'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['date_from', 'date_to', 'target_move', 'result_selection', 'reconciled', 'journal_ids', 'company_id'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_partnerledger']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        partners = report_values['docs']

        report_lines = []
        for partner in partners:
            partner_lines = report_model.with_context(ctx)._lines(data, partner)
            if partner_lines:
                parent_id = f"partner_{partner.id}"
                debit = report_model.with_context(ctx)._sum_partner(data, partner, 'debit')
                credit = report_model.with_context(ctx)._sum_partner(data, partner, 'credit')
                balance = report_model.with_context(ctx)._sum_partner(data, partner, 'balance')

                report_lines.append({
                    'id': parent_id,
                    'name': partner.name or 'Unknown Partner',
                    'parent': False,
                    'level': 1,
                    'type': 'report',
                    'debit': debit,
                    'credit': credit,
                    'balance': balance,
                })
                for idx, line in enumerate(partner_lines):
                    report_lines.append({
                        'id': f"line_{line['lid']}_{parent_id}",
                        'name': f"{line['date']} - {line['code']} ({line['move_name']})",
                        'parent': parent_id,
                        'level': 2,
                        'type': 'account',
                        'account': line['account_id'],
                        'debit': line['debit'],
                        'credit': line['credit'],
                        'balance': line['balance'],
                        'ref': line.get('lref') or '',
                        'label': line.get('lname') or '',
                    })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('Partner Ledger'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = 'account.report.general.ledger'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('General Ledger'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['date_from', 'date_to', 'target_move', 'journal_ids', 'display_account', 'sortby', 'initial_balance', 'company_id'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_general_ledger']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        accounts_res = report_values['Accounts']

        report_lines = []
        display_account = data['form']['display_account']

        for acc in accounts_res:
            if display_account == 'all' or (display_account == 'movement' and acc['move_lines']) or (display_account == 'not_zero' and not self.env.company.currency_id.is_zero(acc['balance'])):
                account_rec = self.env['account.account'].search([('code', '=', acc['code'])], limit=1)
                if not account_rec:
                    continue
                parent_id = f"account_{account_rec.id}"
                report_lines.append({
                    'id': parent_id,
                    'name': f"{acc['code']} {acc['name']}",
                    'parent': False,
                    'level': 1,
                    'type': 'report',
                    'debit': acc['debit'],
                    'credit': acc['credit'],
                    'balance': acc['balance'],
                })
                for idx, line in enumerate(acc.get('move_lines', [])):
                    report_lines.append({
                        'id': f"line_{idx}_{parent_id}",
                        'name': f"{line.get('ldate') or ''} - {line.get('lcode') or ''} ({line.get('move_name') or ''})",
                        'parent': parent_id,
                        'level': 2,
                        'type': 'account',
                        'account': account_rec.id,
                        'debit': line.get('debit', 0.0),
                        'credit': line.get('credit', 0.0),
                        'balance': line.get('balance', 0.0),
                        'ref': line.get('lref') or '',
                        'label': line.get('lname') or '',
                    })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('General Ledger'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountBalanceReport(models.TransientModel):
    _inherit = 'account.balance.report'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Trial Balance'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['display_account', 'target_move', 'journal_ids', 'company_id', 'date_from', 'date_to'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_trial_balance']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        account_res = report_values['Accounts']

        report_lines = []
        for idx, acc in enumerate(account_res):
            account_rec = self.env['account.account'].search([('code', '=', acc['code'])], limit=1)
            report_lines.append({
                'id': f"account_{idx}",
                'name': f"{acc['code']} {acc['name']}",
                'parent': False,
                'level': 1,
                'type': 'account',
                'account': account_rec.id if account_rec else False,
                'debit': acc['debit'],
                'credit': acc['credit'],
                'balance': acc['balance'],
            })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('Trial Balance'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.aged.trial.balance'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Aged Partner Balance'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['date_from', 'date_to', 'target_move', 'result_selection', 'period_length', 'company_id'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_agedpartnerbalance']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        movelines = report_values['get_partner_lines']

        report_lines = []
        for idx, ml in enumerate(movelines):
            report_lines.append({
                'id': f"aged_{idx}",
                'name': ml.get('name') or 'Unknown Partner',
                'parent': False,
                'level': 1,
                'type': 'account',
                'account': ml.get('partner_id'),  # Will pass as partner_id for custom drilldown
                'debit': ml.get('direction', 0.0),
                'credit': 0.0,
                'balance': ml.get('total', 0.0),
            })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft')
        ], limit=1))

        return {
            'report_name': _('Aged Partner Balance'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        partner_id = line_data.get('account') # stored under account parameter
        if not partner_id:
            return []

        # Drill down into outstanding items for the partner
        move_lines = self.env['account.move.line'].search([
            ('partner_id', '=', partner_id),
            ('full_reconcile_id', '=', False),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountPrintJournal(models.TransientModel):
    _inherit = 'account.print.journal'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('Journal Audit'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        data = {'form': self.read(['target_move', 'sort_selection', 'journal_ids', 'company_id', 'date_from', 'date_to'])[0]}
        if data['form'].get('date_from') and not isinstance(data['form']['date_from'], str):
            data['form']['date_from'] = data['form']['date_from'].strftime('%Y-%m-%d')
        if data['form'].get('date_to') and not isinstance(data['form']['date_to'], str):
            data['form']['date_to'] = data['form']['date_to'].strftime('%Y-%m-%d')

        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')

        report_model = self.env['report.base_accounting_kit.report_journal_audit']
        ctx = dict(data['form']['used_context'], active_model=self._name, active_ids=self.ids, active_id=self.id)
        report_values = report_model.with_context(ctx)._get_report_values(self.ids, data)
        journals = report_values['docs']
        lines_dict = report_values['lines']

        report_lines = []
        for jrn in journals:
            j_lines = lines_dict.get(jrn.id, self.env['account.move.line'])
            if j_lines:
                parent_id = f"journal_{jrn.id}"
                debit = sum(j_lines.mapped('debit'))
                credit = sum(j_lines.mapped('credit'))
                report_lines.append({
                    'id': parent_id,
                    'name': f"{jrn.code} - {jrn.name}",
                    'parent': False,
                    'level': 1,
                    'type': 'report',
                    'debit': debit,
                    'credit': credit,
                    'balance': debit - credit,
                })
                for idx, line in enumerate(j_lines):
                    report_lines.append({
                        'id': f"line_{line.id}_{parent_id}",
                        'name': f"{line.date.strftime('%Y-%m-%d')} - {line.move_id.name or ''}",
                        'parent': parent_id,
                        'level': 2,
                        'type': 'account',
                        'account': line.account_id.id,
                        'debit': line.debit,
                        'credit': line.credit,
                        'balance': line.debit - line.credit,
                        'ref': line.ref or '',
                        'label': line.name or '',
                    })

        has_unposted = bool(self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('journal_id', 'in', self.journal_ids.ids)
        ], limit=1))

        return {
            'report_name': _('Journal Audit'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': has_unposted,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []
        
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('journal_id', 'in', self.journal_ids.ids),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines


class AccountFxRevaluation(models.TransientModel):
    _inherit = 'account.fx.revaluation'

    def action_view_online(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'hudson_dynamic_financial_report',
            'name': _('FX Revaluation'),
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }

    def get_report_data(self):
        self.ensure_one()
        adjustments = self._get_revaluation_lines()

        report_lines = []
        for idx, (account, adjustment) in enumerate(adjustments.items()):
            report_lines.append({
                'id': f"fx_{idx}",
                'name': f"{account.code} {account.name}",
                'parent': False,
                'level': 1,
                'type': 'account',
                'account': account.id,
                'debit': adjustment if adjustment > 0.0 else 0.0,
                'credit': -adjustment if adjustment < 0.0 else 0.0,
                'balance': adjustment,
            })

        return {
            'report_name': _('FX Revaluation'),
            'report_lines': report_lines,
            'debit_credit': True,
            'enable_filter': False,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'has_unposted': False,
        }

    def get_drilldown_lines(self, line_data):
        self.ensure_one()
        account_id = line_data.get('account')
        if not account_id:
            return []

        # Find unreconciled foreign currency items for the account
        company = self.env.company
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account_id),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('company_id', '=', company.id),
            ('currency_id', '!=', company.currency_id.id),
            ('currency_id', '!=', False),
        ], limit=100)

        lines = []
        for ml in move_lines:
            lines.append({
                'id': ml.id,
                'j_id': ml.move_id.id,
                'date': ml.date.strftime('%Y-%m-%d'),
                'name': ml.move_id.name or '',
                'partner_name': ml.partner_id.name or '',
                'label': ml.name or '',
                'debit': ml.debit,
                'credit': ml.credit,
                'balance': ml.debit - ml.credit,
            })
        return lines
