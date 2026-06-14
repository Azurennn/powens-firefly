# Powens-Firefly

This package aims at transfering Powens transactions to Firefly III
transactions using both tools' API.

This package stores no banking information, only tokens and information to access both APIs in a `credentials.yaml` file 
which can be specified by the user`.


---------
## Install

```commandline
pip install powens-firefly
```


---------
## Use

```commandline
powens-firefly
```
This will store credentials in the default path "credentials.yml"
which can be changed with the option "--credentials_path"


---------
## Banks

Tested and Customised with
- Credit-Agricole
- Revolut (limitation with Exchanges)

Listing all transactions works for all banks, but transfers need to be tested.

### Revolut's Exchanges limitation

Example: If your base account is in EUR and you transfer GBP into USD and a comission/fee is applied in EUR.
Exchange transfer will likely be wrong, possibly creating the transfer as from your EUR account to your USD account
and a widthdrawal transaction in your GBP account.


### Configuration yaml

```yaml
firefly:
  token: <firefly_token>
  token_type: BearerToken
  url: http://<firefly_url>/api

mapping:
  <powens_account_id1>: <firefly_account_id1>
  <powens_account_id2>: <firefly_account_id2>
  <powens_account_id3>: <firefly_account_id3>
  <powens_account_id4>: <firefly_account_id4>

powens:
  client_id: <powens_client_id>
  date_acquired_utc: <automatically-filled-date>
  domain: <powens_domain>.biapi.pro
  expires_in: <automatically-filled-int>
  token: <powens token>
  user_id: <powens_user_id>
```


---------
## Note
This package was developed very quickly,
I should be able to maintain it but improvements will take time.

Feel free to fork it and make merge requests.
