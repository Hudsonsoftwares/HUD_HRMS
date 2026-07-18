# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestThemeToggle(TransactionCase):

    def test_theme_toggle_field_and_session(self):
        """Test dark_mode field behavior on res.users and its injection in session_info."""
        user = self.env.user
        self.assertFalse(user.dark_mode)

        # Update preference
        user.write({'dark_mode': True})
        self.assertTrue(user.dark_mode)

        # Check session_info updates (safely guarded)
        session_info = self.env['ir.http'].session_info()
        self.assertIn('hudson_dark_mode', session_info)
        self.assertTrue(session_info['hudson_dark_mode'])
