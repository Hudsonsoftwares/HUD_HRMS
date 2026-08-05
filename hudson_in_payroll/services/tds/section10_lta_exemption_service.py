# -*- coding: utf-8 -*-
import logging
from odoo import fields
from ..base import BaseStatutoryService

_logger = logging.getLogger(__name__)


class Section10LtaExemptionResult:
    """
    Data Transfer Object representing the result of Section 10(5) LTA Exemption audit.
    """
    def __init__(self, employee_id, block_period, claims_in_block, declared_fare,
                 actual_lta_received, exempt_amount, is_eligible, remarks):
        self.employee_id = employee_id
        self.block_period = block_period
        self.claims_in_block = claims_in_block
        self.declared_fare = declared_fare
        self.actual_lta_received = actual_lta_received
        self.exempt_amount = exempt_amount
        self.is_eligible = is_eligible
        self.remarks = remarks


class Section10LtaExemptionService(BaseStatutoryService):
    """
    Dedicated Eligibility & Exemption Service for Section 10(5) Leave Travel Allowance (LTA).
    Statutory Provisions under Indian Income Tax Act 2025:
    1. Maximum 2 journey exemptions allowed in a 4-calendar-year block period (e.g. 2022-2025).
    2. Exemption is capped at actual domestic travel fare incurred (Air Economy / Rail AC 1st Class)
       or actual LTA allowance received from payroll, whichever is lower.
    3. Exemption applies only under the Old Tax Regime (Section 115BAC prohibits LTA under New Regime).
    """

    CURRENT_BLOCK_PERIOD = "2022-2025"
    MAX_CLAIMS_PER_BLOCK = 2

    def validate_and_calculate(self, employee_id, declared_fare, actual_lta_received=0.0, claims_in_block=0, eval_date=None):
        """
        Validates LTA block period eligibility and calculates statutory exemption under Section 10(5).

        :param employee_id: int / hr.employee id
        :param declared_fare: Float (Actual travel fare declared/proved by employee)
        :param actual_lta_received: Float (Annual LTA allowance received from payroll)
        :param claims_in_block: int (Number of LTA claims already approved in current 4-year block)
        :param eval_date: Date (optional)
        :return: Section10LtaExemptionResult
        """
        eval_date = eval_date or fields.Date.today()

        # Check block period statutory limit (Max 2 journeys per 4-year block)
        if claims_in_block >= self.MAX_CLAIMS_PER_BLOCK:
            return Section10LtaExemptionResult(
                employee_id=employee_id,
                block_period=self.CURRENT_BLOCK_PERIOD,
                claims_in_block=claims_in_block,
                declared_fare=declared_fare,
                actual_lta_received=actual_lta_received,
                exempt_amount=0.0,
                is_eligible=False,
                remarks=f"Ineligible under Section 10(5): Employee has already claimed the maximum of {self.MAX_CLAIMS_PER_BLOCK} LTA exemptions in block period {self.CURRENT_BLOCK_PERIOD}."
            )

        if declared_fare <= 0:
            return Section10LtaExemptionResult(
                employee_id=employee_id,
                block_period=self.CURRENT_BLOCK_PERIOD,
                claims_in_block=claims_in_block,
                declared_fare=0.0,
                actual_lta_received=actual_lta_received,
                exempt_amount=0.0,
                is_eligible=True,
                remarks="Zero travel fare declared: No Section 10(5) LTA exemption granted."
            )

        # Statutory Exemption = min(Declared Fare, Actual LTA Allowance Received) if payroll allowance > 0 else Declared Fare
        if actual_lta_received > 0:
            exempt_amount = min(declared_fare, actual_lta_received)
            remarks = f"Section 10(5) LTA Exemption approved at min(Declared Fare ₹{declared_fare:,.2f}, Actual LTA ₹{actual_lta_received:,.2f}) = ₹{exempt_amount:,.2f} [Claim {claims_in_block + 1} of {self.MAX_CLAIMS_PER_BLOCK} in Block {self.CURRENT_BLOCK_PERIOD}]."
        else:
            exempt_amount = declared_fare
            remarks = f"Section 10(5) LTA Exemption approved at declared travel fare ₹{exempt_amount:,.2f} [Claim {claims_in_block + 1} of {self.MAX_CLAIMS_PER_BLOCK} in Block {self.CURRENT_BLOCK_PERIOD}]."

        return Section10LtaExemptionResult(
            employee_id=employee_id,
            block_period=self.CURRENT_BLOCK_PERIOD,
            claims_in_block=claims_in_block,
            declared_fare=declared_fare,
            actual_lta_received=actual_lta_received,
            exempt_amount=exempt_amount,
            is_eligible=True,
            remarks=remarks
        )
