echo "First Account 2 has to buy the Append DRT and then redeem it"
echo ",but to buy the Append DRT Account 2 needs to optin in to receive the Append DRT."
echo "Account 2 opts into the Append DRT"
echo ""

goal asset optin \
    --assetid $APPEND_ID \
    -a $ACCOUNT_2 

echo ""
echo "Account 2 can now purhcase the Append DRT ..."
echo ""

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

echo ""
echo "Account 2 now wants to redeem the Append DRT and add 4 rows of data. "
echo ""
echo "This is done by sending tbe append DRT back to smart contract and waiting on confirmation from enclave.."
echo "A group transaction is created containing one transaction from the account 2 sending the append asset back to the smart contract"
echo "and a second transction from the enclave validating the addition of the new data..."
echo ""

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
    --app-arg "int:4" \
    --app-arg "str:DGVWUSNA--Newnew--ASUDBQ" \
    --app-arg "int:1" \
    --app-account $ACCOUNT_2 \
    --out txnAppCall2.tx

cat txnTransfer2.tx txnAppCall2.tx > appendCombinedTxns2.tx
goal clerk group -i appendCombinedTxns2.tx -o groupedtransactions.tx 
goal clerk split -i groupedtransactions.tx -o splitfiles  

goal clerk sign -i splitfiles-0 -o splitfiles-0.sig 
goal clerk sign -i splitfiles-1 -o splitfiles-1.sig 

cat splitfiles-0.sig splitfiles-1.sig > signout.tx
goal clerk rawsend -f signout.tx 

echo ""
echo "Account 2's contributor token has been created but now needs to be claimed by the contributor "
echo ""
echo ""
CONTRIB_2_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk '{print $2}' | head -44 | tail -1)

echo "Store contributor token ID: CONTRIB_2_ID=$CONTRIB_2_ID"
echo ""
echo "Account 2 has to opt into the newly created contributor token and then claim the token ..."
echo ""
echo "1. Optin to contributor token"

goal asset optin \
    --assetid $CONTRIB_2_ID \
    -a $ACCOUNT_2 \

echo ""
echo "2. Claim contributor token... "

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:box_store_transfer" \
    --foreign-asset $CONTRIB_2_ID \
    --box "str:$CONTRIB_2_ID"
    
echo ""
