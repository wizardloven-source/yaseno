# core/application/handlers/accounting/post_journal_entry_handler.py

"""
Post Journal Entry Handler - Uses PostingEngine
"""

from core.domain.accounting.entities import JournalEntry
from core.domain.accounting.value_objects import JournalEntryId
from core.domain.accounting.exceptions import EntryNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.posting_engine import PostingEngine
from core.application.accounting.commands import PostJournalEntryCommand
from core.application.accounting.dtos import JournalEntryResponseDTO
from core.application.security.authorization import UserContext, require_permission, Permission
from ..base_handler import BaseHandler


class PostJournalEntryHandler(BaseHandler[PostJournalEntryCommand, JournalEntryResponseDTO]):
    """
    Handler for posting journal entries.
    
    Uses the unified PostingEngine for all posting operations.
    NO direct ledger access - everything goes through PostingEngine.
    """
    
    def __init__(self, uow: IUnitOfWork, posting_engine: PostingEngine):
        super().__init__(uow)
        self._posting_engine = posting_engine
    
    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: PostJournalEntryCommand, user_context: UserContext) -> JournalEntryResponseDTO:
        """
        Post a journal entry.
        
        The PostingEngine handles:
            1. Validation
            2. Ledger entry creation
            3. Account balance updates
            4. Event dispatch
        """
        with self._uow:
            # Get the entry
            entry_id = JournalEntryId.from_string(command.entry_id)
            entry = self._uow.journal_entries.get_by_id(entry_id)
            
            if not entry:
                raise EntryNotFoundError(command.entry_id)
            
            # Let PostingEngine handle everything
            result = self._posting_engine.post(entry, user_context.user_id, skip_save=False)
            
            if not result.success:
                raise ValueError(f"Posting failed: {result.message} - {', '.join(result.errors)}")
            
            # Save any changes (PostingEngine already saved, but UoW handles it)
            self._commit()
            
            # Return DTO
            return self._to_dto(entry)
    
    def _to_dto(self, entry: JournalEntry) -> JournalEntryResponseDTO:
        """Convert domain entity to DTO"""
        from core.application.accounting.handlers import journal_entry_to_response_dto
        return journal_entry_to_response_dto(entry)