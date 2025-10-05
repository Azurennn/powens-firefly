from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal

from powens.account import PowensAccount
from powens.transaction import PowensTransaction


@dataclass
class PowensCounterParty:
    iban: str

    def __hash__(self):
        return hash(self.iban)


@dataclass
class PowensAccount:
    iban: str

    def __hash__(self):
        return hash(self.iban)


@dataclass
class PowensTransaction:
    value: Decimal
    datetime: Optional[datetime] = None
    date: Optional[date] = None
    counterparty: Optional[PowensCounterParty] = None

    def __hash__(self):
        return hash(self.value) + hash(self.datetime) + hash(self.date) + hash(self.counterparty)


class TransactionMatcher:
    def __init__(
        self,
        accounts_transactions: Dict[PowensAccount, List[PowensTransaction]]
    ):
        self.accounts_transactions = accounts_transactions

    def find_matching_transactions(
            self,
            target_transaction: PowensTransaction,
            source_account: PowensAccount
    ) -> List[Tuple[PowensAccount, PowensTransaction]]:
        """
        Find transactions that could match the target transaction.
        """
        matches = []

        # First, try to match using counterparty IBAN if available
        if target_transaction.counterparty and target_transaction.counterparty.iban:
            matches = self._match_by_counterparty_iban(target_transaction, source_account)
            if matches:
                return matches

        # If no counterparty IBAN or no matches found, search all accounts
        matches = self._match_by_amount_and_date(target_transaction, source_account)

        return matches

    def _match_by_counterparty_iban(
            self,
            target_transaction: PowensTransaction,
            source_account: PowensAccount
    ) -> List[Tuple[PowensAccount, PowensTransaction]]:
        """Match transactions using the counterparty IBAN"""
        matches = []
        counterparty_iban = target_transaction.counterparty.iban

        # Find the account with matching IBAN
        target_account = None
        for account in self.accounts_transactions:
            if account.iban == counterparty_iban:
                target_account = account
                break

        if not target_account:
            return matches

        # Search for matching transactions in the target account
        for transaction in self.accounts_transactions[target_account]:
            if self._transactions_match(target_transaction, transaction, source_account, target_account):
                matches.append((target_account, transaction))

        return matches

    def _match_by_amount_and_date(
            self,
            target_transaction: PowensTransaction,
            source_account: PowensAccount
    ) -> List[Tuple[PowensAccount, PowensTransaction]]:
        """Match transactions by amount and date across all accounts"""
        matches = []

        for account, transactions in self.accounts_transactions.items():
            # Skip the source account
            if account == source_account:
                continue

            for transaction in transactions:
                if self._transactions_match(target_transaction, transaction, source_account, account):
                    matches.append((account, transaction))

        return matches

    def _transactions_match(
            self,
            transaction1: PowensTransaction,
            transaction2: PowensTransaction,
            account1: PowensAccount,
            account2: PowensAccount
    ) -> bool:
        """
        Check if two transactions match based on amount, date, and account relationship.

        For a proper match:
        - Amounts should be opposite (one positive, one negative) and equal in absolute value
        - Dates should match
        - Accounts should be different
        """
        # Check if amounts are opposite and equal
        if transaction1.value + transaction2.value != 0:
            return False

        # Check if dates match
        try:
            if transaction1.date != transaction2.date:
                return False
        except ValueError:
            # If either transaction has no date, they can't match
            return False

        # Check if accounts are different (transfers should be between different accounts)
        if account1 == account2:
            return False

        return True

    def process_transaction_matching(
            self,
            interactive: bool = True
    ) -> Dict[Tuple[PowensAccount, PowensTransaction], Optional[Tuple[PowensAccount, PowensTransaction]]]:
        """
        Process all transactions and find their matches.

        Args:
            interactive: Whether to prompt user for input when multiple matches found

        Returns:
            Dictionary mapping each (account, transaction) to its match, or None if no match
        """
        results = {}
        processed_transactions = set()

        for source_account, transactions in self.accounts_transactions.items():
            for transaction in transactions:
                # Skip if we've already processed this transaction as part of a match
                transaction_key = (source_account, transaction)
                if transaction_key in processed_transactions:
                    continue

                matches = self.find_matching_transactions(transaction, source_account)

                if len(matches) == 0:
                    results[transaction_key] = None
                elif len(matches) == 1:
                    # Single match found - automatic match
                    match_account, match_transaction = matches[0]
                    results[transaction_key] = (match_account, match_transaction)

                    # Mark both transactions as processed to avoid duplicate processing
                    processed_transactions.add(transaction_key)
                    processed_transactions.add((match_account, match_transaction))
                else:
                    # Multiple matches found
                    if interactive:
                        chosen_match = self._prompt_user_choice(transaction, source_account, matches)
                        results[transaction_key] = chosen_match

                        if chosen_match:
                            # Mark chosen match as processed
                            processed_transactions.add(transaction_key)
                            processed_transactions.add(chosen_match)
                    else:
                        # Non-interactive mode - no match assigned
                        results[transaction_key] = None

        return results

    def _prompt_user_choice(
            self,
            transaction: PowensTransaction,
            source_account: PowensAccount,
            matches: List[Tuple[PowensAccount, PowensTransaction]]
    ) -> Optional[Tuple[PowensAccount, PowensTransaction]]:
        """Prompt user to choose from multiple matches"""
        print(f"\nMultiple matches found for transaction:")
        print(f"  Account: {source_account.iban}")
        print(f"  Amount: {transaction.value}")
        print(f"  Date: {transaction.date}")
        if transaction.counterparty:
            print(f"  Counterparty IBAN: {transaction.counterparty.iban}")

        print(f"\nPossible matches:")
        for i, (account, match_transaction) in enumerate(matches, 1):
            print(f"  {i}. Account: {account.iban}")
            print(f"     Amount: {match_transaction.value}")
            print(f"     Date: {match_transaction.date}")
            if match_transaction.counterparty:
                print(f"     Counterparty IBAN: {match_transaction.counterparty.iban}")
            print()

        print(f"  0. No match (skip this transaction)")

        while True:
            try:
                choice = input(f"Choose a match (0-{len(matches)}): ").strip()
                choice_num = int(choice)

                if choice_num == 0:
                    return None
                elif 1 <= choice_num <= len(matches):
                    return matches[choice_num - 1]
                else:
                    print(f"Please enter a number between 0 and {len(matches)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nOperation cancelled")
                return None


# Example usage
def example_usage():
    """Example of how to use the TransactionMatcher"""
    from decimal import Decimal
    from datetime import date

    # Create sample accounts
    account1 = PowensAccount(iban="FR1234567890123456789012")
    account2 = PowensAccount(iban="FR9876543210987654321098")

    # Create sample transactions
    transaction1 = PowensTransaction(
        value=Decimal("100.00"),
        date=date(2024, 1, 15),
        counterparty=PowensCounterParty(iban="FR9876543210987654321098")
    )

    transaction2 = PowensTransaction(
        value=Decimal("-100.00"),
        date=date(2024, 1, 15),
        counterparty=PowensCounterParty(iban="FR1234567890123456789012")
    )

    # Create accounts_transactions dictionary
    accounts_transactions = {
        account1: [transaction1],
        account2: [transaction2]
    }

    # Create matcher and process transactions
    matcher = TransactionMatcher(accounts_transactions)
    results = matcher.process_transaction_matching(interactive=True)

    # Print results
    for (account, transaction), match in results.items():
        print(f"Transaction {transaction.value} from {account.iban}")
        if match:
            match_account, match_transaction = match
            print(f"  -> Matched with {match_transaction.value} from {match_account.iban}")
        else:
            print(f"  -> No match found")


if __name__ == "__main__":
    example_usage()
