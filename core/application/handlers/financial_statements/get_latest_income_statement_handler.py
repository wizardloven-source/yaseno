from core.application.handlers.base_handler import BaseQueryHandler
from core.application.financial_statements.commands import GetLatestIncomeStatementQuery
from core.application.financial_statements.dtos import IncomeStatementDTO
from core.application.financial_statements.converters import income_statement_to_dto
from core.application.security.authorization import UserContext, require_permission, Permission


class GetLatestIncomeStatementHandler(BaseQueryHandler[GetLatestIncomeStatementQuery, IncomeStatementDTO]):
    def __init__(self, statement_repo):
        self._statement_repo = statement_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetLatestIncomeStatementQuery, user_context: UserContext = None) -> IncomeStatementDTO:
        statement = self._statement_repo.get_latest_income_statement(query.currency)
        if not statement:
            return None
        return income_statement_to_dto(statement)