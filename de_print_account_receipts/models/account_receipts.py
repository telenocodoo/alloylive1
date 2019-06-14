# -*- coding: utf-8 -*-
from odoo import models

class PrintJournalEntries(models.Model):
    _inherit = 'account.voucher'

    def print_journal_entries(self):
        return self.env.ref('de_print_account_receipts.action_account_receipts_report').report_action(self)
