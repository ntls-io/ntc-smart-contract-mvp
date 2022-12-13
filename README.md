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

# How to run

1. Follow the setup instructions above.
2. Build the smart contract
```txt
$ ./build.sh contracts.naut_prototype.drt_demo
```
3. Enter sandbox
```txt
$ ./sandbox enter algod
```
4. In sandbox, deploy and create smart contract
```txt
$ source /data/create.sh
```
## Run Test

In sandbox, directly after you have created the smart contract, run
```txt
$ source /data/test.sh 
```

# Interact with Smart Contract Manually

## General Calls
These are general calls made to your sandboxed algorand lockchain using the `goal` cli. Please enter the sandbox to execute these commands.
### See global variables of smart contract
```txt
goal app read --global --app-id $APP_ID --guess-format
```

### See application info of smart contract
```txt
goal app info --app-id $APP_ID
```

### See account info of the smart contract (or other accounts)
```txt
goal account info -a $ACCOUNT_APP
```

### See local variables of opted in accounts
```txt
goal app read --local --from $ACCOUNT_2 --app-id $APP_ID
```

## Smart Contract Functional Calls
### Add new data contributor
To add a new data contributor, the account to be added needs to purchase and the Append DRT and be opted into:
- the smart contract (APP_ID)
- and, the contributor token (CONTRIB_ID)

Once the above is complete, the contributor needs to sign a transfer transaction to transfer the Append DRT back to the smart contract (redeem) within a group transaction where the second transaction in the group transaction is signed by the enclave to validate the incoming data. 

1. optin to Apppend DRT
```txt
goal asset optin \
    --assetid $APPEND_ID \
    -a $ACCOUNT_2 
```
2. Purchase the Append DRT
```
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:buy_drt" \
    --app-arg "int:1" \
    --foreign-asset $APPEND_ID \
    --out txnAppCall.tx

goal clerk send \
    -a 1000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_2" \
    --out txnPayment.tx

cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx
```
3. optin to application
```txt
goal app optin \
 --app-id $APP_ID \
 --from $ACCOUNT_2 \
```
4. optin to the asset id of the contributor token
```txt
goal asset optin \
 --assetid $CONTRIB_ID \
 -a $ACCOUNT_2 \
```
3. Group transaction from the contributor and the enclave.
   * Transaction 1 is an asset transfer instruction to send an Append DRT to the smart contract.
```txt
goal asset send \
    -f $ACCOUNT_2 \
    -t $ACCOUNT_APP \
    --assetid $APPEND_ID \
    -a 1 \
    --out txnTransfer2.tx
```
   * Transaction 2 is an application call to the smart contract with the instruction to "add_data_contributor".
      NB have to specifiy how many rows of data to contribute to the pool
      NB have to provide the new data package hash
      NB have to specify that the new data is approved
      NB have to include the contributor token ID
      NB have to reference the account that has redeemed the append DRT.
```txt
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:add_data_contributor" \
    --app-arg "int:9" \
    --app-arg "str:DGVWUSNA--Newnew--ASUDBQ" \
    --app-arg "int:1" \
    --foreign-asset $CONTRIB_ID \
    --app-account $ACCOUNT_2 \
    --out txnAppCall2.tx
```
   The two transactions are joined into a single group transaction and sent to the smart contract. 
```txt
cat txnTransfer2.tx txnAppCall2.tx > appendCombinedTxns2.tx
goal clerk group -i appendCombinedTxns2.tx -o groupedtransactions.tx 
goal clerk split -i groupedtransactions.tx -o splitfiles  

goal clerk sign -i splitfiles-0 -o splitfiles-0.sig 
goal clerk sign -i splitfiles-1 -o splitfiles-1.sig 

cat splitfiles-0.sig splitfiles-1.sig > signout.tx
goal clerk rawsend -f signout.tx 
```

### Update data package
Transaction to update the data package of the smart contract, only executed from enclave address
```txt
goal app call \
 --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:update_data_package" \
    --app-arg "str:SVCAJHVSC--UPDATED_PACKAGE---DHBSU#$" \
```

### Create Digital Right Token (DRT)
Transaction to create a DRT, specify name, amount, url of the binary code it represents, the hash of the binary code , note ( if needed ), exchange price i.e. 3000000 MicroAlgos = 3 Algos.
```txt
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:create_drt" \
    --app-arg "str:ALEX_DRT_01" \
    --app-arg "int:10000" \
    --app-arg "str:https://code_binary_url" \
    --app-arg "str:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" \
    --app-arg "str:note" \
    --app-arg "int:3000000"
```

### Update DRT Price
Transaction to update the price of a DRT, need to submit the asset ID and the new price

```txt
goal app call \
 --app-id $APP_ID \
 -f $ACCOUNT_1 \
 --app-arg "str:update_drt_price" \
 --app-arg "int:7" \
 --foreign-asset 125 \
```

### Purchase DRT
- Txn 1. user opts in to asset
- Group Txn:
  * txn 1. call contract
  * txn 2. (inner) contract sends NFT
  * txn 3. user pays

1. Txn 1

```txt
goal asset optin \
 --assetid 125 \
 -a $ACCOUNT_2 \
```

2. Group Txn, the transaction will only be successfull if all individual transactions in the group are successful.
- txn 1
```txt
goal app call \
 --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:buy_drt" \
    --app-arg "int:2" \
    --foreign-asset 125 \
    --out txnAppCall.tx
```

- txn 2 & 3
```txt
goal clerk send \
    -a 6000000 \
    -t "$ACCOUNT_APP" \
 -f "$ACCOUNT_NAUT" \
 --out txnPayment.tx
```
Join the transactions
```txt
cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
```
Sign group transaction
```txt
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
```
Send transaction
```txt
goal clerk rawsend -f signoutbuy.tx
```

### Claim fees
Transaction for data contributors to claim their fees, need the asset ID of the contributor token
```txt
goal app call \
 --app-id $APP_ID \
 -f $ACCOUNT_2 \
 --app-arg "str:claim_fees" \
 --foreign-asset $CONTRIB_ID \
```
### Compute Fees
Transaction for data contributors to compute the current fees owed to them that can then be viewed in their local vairables.
```txt
goal app call \
 --app-id $APP_ID \
 -f $ACCOUNT_2 \
 --app-arg "str:compute_royalty_fee" \

```

### Add additional data contributor from creator 
Transaction only for the smart contract creator to add additional data. The smart contract creator need not to purchase an Append DRT to contribute to the smart contract they created. Only a single transaction from the enclave to validate the incoming data is needed.
```txt
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:creator_data_validation_add" \
    --app-arg "int:12" \
    --app-arg "str:DGVWUSNA--CREATOR--ASUDBQ" \
    --app-arg "int:1" \
    --foreign-asset $CONTRIB_ID \
    --app-account $ACCOUNT_1
```

# Links

- [Youtube Pyteal Course](https://youtube.com/playlist?list=PLpAdAjL5F75CNnmGbz9Dm_k-z5I6Sv9_x)
- [Official Algorand Smart Contract Guidelines](https://developer.algorand.org/docs/get-details/dapps/avm/teal/guidelines/)
- [PyTeal Documentation](https://pyteal.readthedocs.io/en/latest/index.html)
- [Algorand DevRel Example Contracts](https://github.com/algorand/smart-contracts)
