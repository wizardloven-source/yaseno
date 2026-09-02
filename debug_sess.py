import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import api

bootstrap = api.bootstrap

with bootstrap.scope() as container:
    uow1 = container.resolve("uow")
    engine = container.resolve("posting_engine")
    handler_uow = container.resolve("uow")
    print("uow1 is handler_uow:", uow1 is handler_uow)
    print("engine._uow is handler_uow:", engine._uow is handler_uow)
    with handler_uow:
        print("handler session id:", id(handler_uow.session))
    with engine._uow:
        print("engine session id:", id(engine._uow.session))
    with engine._uow:
        print("engine journal_repo session is engine uow session:", engine._journal_repo._session is engine._uow.session)
        print("engine ledger_repo session is engine uow session:", engine._ledger_repo._session is engine._uow.session)