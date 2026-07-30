# -*- coding: utf-8 -*-
import logging
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


class ESICValidator(BaseStatutoryService):
    """
    Pure Python eligibility engine for ESIC statutory compliance.
    Validates company enablement, employee applicability, active status, IP number presence,
    and statutory contribution period validity.
    """

    def is_esic_eligible(self, payslip):
        """
        Executes statutory ESIC eligibility checks in sequence:
        1. Company ESIC Enabled?
        2. Employee ESIC Applicable?
        3. Employee Active?
        4. Valid ESIC IP Number? (Logs warning if missing, continues)
        5. Contribution Period Valid?
        """
        company = payslip.company_id
        employee = payslip.employee_id

        # 1. Company ESIC Enabled?
        if not company or not company.hds_in_esic_applicable:
            return False

        # 2. Employee ESIC Applicable?
        if not employee or not employee.hds_in_esic_applicable:
            return False

        # 3. Employee Active?
        if hasattr(employee, 'active') and not employee.active:
            return False

        # 4. Valid ESIC IP Number? (Log statutory warning if missing)
        if not employee.hds_in_esic_ip_number:
            _logger.warning(
                "[ESICValidator] Employee %s (%s) has ESIC Applicable = True but is missing ESIC IP Number.",
                employee.name, employee.id
            )

        # 5. Contribution Period Valid?
        if employee.hds_in_esic_ip_status == 'resigned':
            return False
        if employee.hds_in_esic_exit_date and payslip.date_from and employee.hds_in_esic_exit_date < payslip.date_from:
            return False

        return True

    def is_esic_applicable(self, payslip):
        """Alias for is_esic_eligible."""
        return self.is_esic_eligible(payslip)
