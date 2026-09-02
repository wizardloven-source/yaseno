# core/application/handlers/tax/__init__.py
"""
Tax Handlers - معالجات الضرائب
"""

from .create_tax_rule_handler import CreateTaxRuleHandler
from .update_tax_rule_handler import UpdateTaxRuleHandler
from .delete_tax_rule_handler import DeleteTaxRuleHandler
from .create_tax_exemption_handler import CreateTaxExemptionHandler
from .update_tax_exemption_handler import UpdateTaxExemptionHandler
from .delete_tax_exemption_handler import DeleteTaxExemptionHandler
from .close_tax_period_handler import CloseTaxPeriodHandler
from .get_tax_rule_query_handler import GetTaxRuleQueryHandler
from .list_tax_rules_query_handler import ListTaxRulesQueryHandler
from .get_tax_exemption_query_handler import GetTaxExemptionQueryHandler
from .list_tax_exemptions_query_handler import ListTaxExemptionsQueryHandler
from .get_tax_period_query_handler import GetTaxPeriodQueryHandler
from .list_tax_periods_query_handler import ListTaxPeriodsQueryHandler
from .calculate_tax_query_handler import CalculateTaxQueryHandler

__all__ = [
    "CreateTaxRuleHandler",
    "UpdateTaxRuleHandler",
    "DeleteTaxRuleHandler",
    "CreateTaxExemptionHandler",
    "UpdateTaxExemptionHandler",
    "DeleteTaxExemptionHandler",
    "CloseTaxPeriodHandler",
    "GetTaxRuleQueryHandler",
    "ListTaxRulesQueryHandler",
    "GetTaxExemptionQueryHandler",
    "ListTaxExemptionsQueryHandler",
    "GetTaxPeriodQueryHandler",
    "ListTaxPeriodsQueryHandler",
    "CalculateTaxQueryHandler",
]