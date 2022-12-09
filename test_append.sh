echo "Data pool creator wants to contribute more data ..."
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:creator_data_validation_add" \
    --app-arg "int:12" \
    --app-arg "str:DGVWUSNA--CREATOR--ASUDBQ" \
    --app-arg "int:1" \
    --foreign-asset $CONTRIB_ID \
    --app-account $ACCOUNT_1

echo "Account 2 wants to contribute data ..."
echo "Account 2 has to buy the Append DRT. But first needs to optin in to receive the Append DRT."
echo "Account 2 opts into the Append DRT"
goal asset optin \
    --assetid $APPEND_ID \
    -a $ACCOUNT_2 \

echo "Account 2 purhcases the Append DRT ..."

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

echo "Account 2 wants to redeem the Append DRT. Account 2 first needs to optin to the contributor token..."
echo "Opting in to contributor token..."
goal asset optin \
    --assetid $CONTRIB_ID \
    -a $ACCOUNT_2 

echo "Redeem DRT, by sending it back to smart contract.."
goal asset send \
    -f $ACCOUNT_2 \
    -t $ACCOUNT_APP \
    --assetid $APPEND_ID \
    -a 1 \
    --out txnTransfer2.tx

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:add_data_contributor" \
    --app-arg "int:9" \
    --app-arg "str:DGVWUSNA--NEWCONTRIB--ASUDBQ" \
    --app-arg "int:1" \
    --foreign-asset $CONTRIB_ID \
    --app-account $ACCOUNT_1
    --out txnAppCall2.tx


cat txnTransfer2.tx txnAppCall2.tx > appendCombinedTxns2.tx
goal clerk group -i appendCombinedTxns2.tx -o groupedtransactions.tx 
goal clerk split -i groupedtransactions.tx -o splitfiles  

goal clerk sign -i splitfiles-0 -o splitfiles-0.sig 
goal clerk sign -i splitfiles-1 -o splitfiles-1.sig 

cat splitfiles-0.sig splitfiles-1.sig > signout.tx
goal clerk rawsend -f signout.tx 


echo "And, waiting on confirmation from enclave"