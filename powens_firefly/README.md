# Powens-Firefly

This package aims at transfering Powens transactions to Firefly III
transactions using both tools' API.

This package stores no banking information, only tokens and information to access both APIs.


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


### Additional Options

```commandline

```

### Configuration yaml

```yaml
firefly:
  token: <firefly_token>
  token_type: BearerToken
  url: http://<firefly_url>/api

mapping:
  <origin_account_id1>: <firefly_id1>
  <origin_account_id2>: <firefly_id2>
  <origin_account_id3>: <firefly_id3>
  <origin_account_id4>: <firefly_id4>

powens:
  client_id: <powens_client_id>
  domain: <powens_domain>.biapi.pro
  token: <powens token>
  user_id: <powens_user_id>
```


---------
## Note
This package was developed very quickly,
I should be able to maintain it but improvements will take time.

Feel free to fork it and make merge requests.


---------
## To-Dos

 - [ ] Email option on fail in automation mode
 - [ ] Make connection and connector classes
 - [ ] Make the python version lower
 - [ ] Additional typing
 - [ ] Documentation
 - [ ] Who needs tests ; )
