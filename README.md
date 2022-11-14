# Setup

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install [Algorand sandbox](https://github.com/algorand/sandbox)
   and add this project folder as bind volume in sandbox `docker-compose.yml` under key `services.algod`:
   ```yml
   volumes:
     - type: bind
       source: <path>
       target: /data
   ```
3. Start sandbox:
   ```txt
   $ ./sandbox up
   ```
4. Install Python virtual environment (Python 3.10+) in project folder:
   ```txt
   $ python -m venv venv
   $ source ./venv/Scripts/activate # Windows
   $ source ./venv/bin/activate # Linux
   ```
5. Use Python interpreter: `./venv/Scripts/python.exe`
   VSCode: `Python: Select Interpreter`

##### Smart Contract function calls

#### General calls

# see global variables of smart contract

```txt
goal app read --global --app-id $APP_ID --guess-format
```

# see application info of smart contract

```txt
goal app info --app-id $APP_ID
```

# see account info of the smart contract (or other accounts)

```txt
goal account info -a $ACCOUNT_APP
```

# see local variables of opted in accounts

```txt
goal app read --local --from $ACCOUNT_2 --app-id $APP_ID
```

#### Add new data contributor

to add a new data contributor, the account to be added in needs to be opted into

- the smart contract (APP_ID)
- the contributor token (CONTRIB_ID)
  and then the smart contract can be instructed to add an new contributor

1. optin to application

```txt
goal app optin \
 --app-id $APP_ID \
 --from $ACCOUNT_2 \
```

2. optin transaction to the asset id of the data contributor token

```txt
goal asset optin \
 --assetid $CONTRIB_ID \
 -a $ACCOUNT_2 \
```

3. instruction from creators account to the smart contract to "add_contributor",
   NB have to specifiy asset in the transaction instruction
   NB have to specifiy the amount of rows of data being added to the pool

```txt
goal app call \
   --app-id $APP_ID \
   -f $ACCOUNT_1 \
   --app-arg "str:add_contributor" \
   --app-arg "int:7" \
   --app-arg "str:SVCAJHVSC--hello---DHBSU#$" \
   --app-account $ACCOUNT_2 \
   --foreign-asset $CONTRIB_ID \
```

#### Update data package

transaction to update the data package of the smart contract, only executed from creators address

```txt
goal app call \
 --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:update_data_package" \
    --app-arg "str:SVCAJHVSC--UPDATED_PACKAGE---DHBSU#$" \
```

#### Create DRT

transaction to create a DRT, specify name, amount, note ( if needed ), exchange price i.e. 3000000 MicroAlgos = 3 Algos.

```txt
goal app call \
 --app-id $APP_ID \
 -f $ACCOUNT_1 \
 --app-arg "str:create_drt" \
 --app-arg "str:ALEX_DRT_01" \
 --app-arg "int:10000" \
 --app-arg "str:note" \
 --app-arg "int:3000000" \
```

#### Update DRT Price

transaction to update the price of a DRT, need to submit the asset ID and the new price

```txt
goal app call \
 --app-id $APP_ID \
 -f $ACCOUNT_1 \
 --app-arg "str:update_drt_price" \
 --app-arg "int:7" \
 --foreign-asset 125 \
```

#### Purchase DRT

- txn 1. user opts in to asset
- Group tx 1:
  - txn 1. call contract
  - txn 2. (inner) contract sends NFT
  - txn 3. user pays

1. txn 1

```txt
goal asset optin \
 --assetid 125 \
 -a $ACCOUNT_NAUT \
```

2. txn 2 (group transaction), the transaction will only be successfull if all individual transactions in the group are successful.

- creation group transaction 1

```txt
goal app call \
 --app-id $APP_ID \
    -f $ACCOUNT_NAUT \
    --app-arg "str:buy_drt" \
    --app-arg "int:2" \
    --foreign-asset 125 \
    --out txnAppCall.tx
```

2. create group transaction 2

```txt
goal clerk send \
    -a 6000000 \
    -t "$ACCOUNT_APP" \
 -f "$ACCOUNT_NAUT" \
 --out txnPayment.tx
```

join the transactions

```txt
cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
```

sign group transaction

```txt
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
```

send transaction

```txt
goal clerk rawsend -f signoutbuy.tx
```

#### Claim fees

transaction to for a data contributors to claim their fees, need the asset ID of the contributor token

```txt
goal app call \
 --app-id $APP_ID \
 -f $ACCOUNT_2 \
 --app-arg "str:claim_fees" \
 --foreign-asset $CONTRIB_ID \
```

# Links

- [Youtube Pyteal Course](https://youtube.com/playlist?list=PLpAdAjL5F75CNnmGbz9Dm_k-z5I6Sv9_x)
- [Official Algorand Smart Contract Guidelines](https://developer.algorand.org/docs/get-details/dapps/avm/teal/guidelines/)
- [PyTeal Documentation](https://pyteal.readthedocs.io/en/latest/index.html)
- [Algorand DevRel Example Contracts](https://github.com/algorand/smart-contracts)
