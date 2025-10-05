"""
Constants used for powens-firefly
"""

from firefly_iii_client.models.account_type_filter import AccountTypeFilter


ACCOUNT_TYPES = [
    AccountTypeFilter.ASSET,
    AccountTypeFilter.CASH,
    AccountTypeFilter.EXPENSE,
    AccountTypeFilter.REVENUE,
    AccountTypeFilter.LIABILITY,
    AccountTypeFilter.LIABILITIES,
    AccountTypeFilter.DEFAULT_ACCOUNT,
    AccountTypeFilter.CASH_ACCOUNT,
    AccountTypeFilter.ASSET_ACCOUNT,
    AccountTypeFilter.EXPENSE_ACCOUNT,
    AccountTypeFilter.REVENUE_ACCOUNT,
    AccountTypeFilter.BENEFICIARY_ACCOUNT,
    AccountTypeFilter.LOAN,
    AccountTypeFilter.DEBT,
    AccountTypeFilter.MORTGAGE,
]
