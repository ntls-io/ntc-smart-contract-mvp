### Smart Contract function calls ###

## Add new data contributor - ACCOUNT_2

#this will be a single group transaction including an optin transaction and a transfer instruction
#1. optin transaction to the asset id of the data contributor token
goal asset optin \
    --assetid $CONTRIB_ID \
    -a $ACCOUNT_2 \

#2. transfer instruction from creators account to the smart contract, 
#NB have to specifiy asset in the transaction instruction
goal app call \
    --app-id $APP_ID \
     -f $ACCOUNT_1 \
    --app-arg "str:transfer_to_contributor" \
    --app-account "$ACCOUNT_2" \
    --foreign-asset $CONTRIB_ID \

## Update data package

#transaction to update the data package of the smart contract, only executed from creators address
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:update_data_package" \
    --app-arg "str:SVCAJHVSC--UPDATED_PACKAGE---DHBSU#$" \

## Create DRT

#transaction to create a DRT, specify name and amount
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:create_drt" \
    --app-arg "str:ALEX_DRT_01" \
    --app-arg "int:10000" \
    --app-arg "str:note" \
    --app-arg "int:5" \

# to see the created app ID and its exchange rate of 5 algos
goal app read --global --app-id $APP_ID --guess-format


## Update DRT Price

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:update_drt_price" \
    --app-arg "int:7" \
    --foreign-asset 24 \

## Purchase DRT
# txn 1. user opts in to asset
# Group tx 1:
# txn 1. call contract
# txn 2. (inner) contract sends NFT
# txn 3. user pays

#txn 1
goal asset optin \
    --assetid 54 \
    -a $ACCOUNT_2 \

#Gtx
#txn 1
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:buy_drt" \
    --app-arg "int:1" \
    --foreign-asset 54 \
    --out txnAppCall.tx
#txn 2
goal clerk send \
    -a 5 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_2" \
    --out txnPayment.tx

cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx
# create wager transaction /payment 
# amount, to, and from, and put into output file to

#nned to fund the smart contract with something
goal clerk send \
    -a 1000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_1" \
   # -o challenge-wager.tx

# group transactions
# we are going to concatenate the two files into challenge_combined.tx
cat challenge-call.tx challenge-wager.tx > challenge-combined.tx
# then we group them together with a group ID, put into challenge_group
goal clerk group -i challenge-combined.tx -o challenge-grouped.tx
#split into two files
goal clerk split -i challenge-grouped.tx -o challenge-split.tx

# sign individual transactions
goal clerk sign -i challenge-split-0.tx -o challenge-signed-0.tx
goal clerk sign -i challenge-split-1.tx -o challenge-signed-1.tx

# re-combine individually signed transactions
cat challenge-signed-0.tx challenge-signed-1.tx > challenge-signed-final.tx

# send final signed transaction
goal clerk rawsend -f challenge-signed-final.tx
