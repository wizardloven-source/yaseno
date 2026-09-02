# core/infrastructure/db/postgres/report_repository.py
"""Report Repository"""

from typing import Optional, List
from sqlalchemy.orm import Session


class PostgresReportRepository:
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, report):
        pass
    
    def get_by_id(self, report_id):
        return None
    
    def list_all(self, category=None, limit=100, offset=0):
        return []


class PostgresReportScheduleRepository:
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, schedule):
        pass
    
    def get_by_id(self, schedule_id):
        return None
    
    def list_all(self, user_id=None, limit=100, offset=0):
        return []