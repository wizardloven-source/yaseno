# core/application/handlers/centers/get_center_tree_handler.py
"""
Get Center Tree Handler - معالج استعلام الشجرة الهرمية للمراكز
"""

import logging
from typing import List, Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import GetCenterTreeQuery

logger = logging.getLogger(__name__)


class GetCenterTreeHandler(BaseQueryHandler[GetCenterTreeQuery, List[Dict[str, Any]]]):
    """
    معالج استعلام الشجرة الهرمية للمراكز
    
    يقوم بجلب الشجرة الكاملة للمراكز مع تسلسل هرمي.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetCenterTreeQuery, user_context: UserContext = None) -> List[Dict[str, Any]]:
        """
        تنفيذ جلب الشجرة الهرمية
        
        Args:
            query: استعلام الشجرة الهرمية
        
        Returns:
            List[Dict[str, Any]]: الشجرة الهرمية للمراكز
        """
        logger.debug(f"Fetching center tree: root={query.root_code}")

        with self._uow:
            center_repo = self._uow.centers
            tree = center_repo.get_tree(query.root_code)

            logger.info(f"Center tree built with {len(tree)} root nodes")

            return tree