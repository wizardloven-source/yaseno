class CurrencyError(Exception):
    pass

class CurrencyNotFoundError(CurrencyError):
    def __init__(self, currency_id: str):
        super().__init__(f"Currency not found: {currency_id}")

class CurrencyCodeAlreadyExistsError(CurrencyError):
    def __init__(self, code: str):
        super().__init__(f"Currency code already exists: {code}")

class CannotDeleteBaseCurrencyError(CurrencyError):
    def __init__(self, code: str):
        super().__init__(f"Cannot delete base currency: {code}")

class ExchangeRateNotFoundError(CurrencyError):
    def __init__(self, from_currency: str, to_currency: str):
        super().__init__(f"Exchange rate not found: {from_currency} -> {to_currency}")