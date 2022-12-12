#### Script to test the following scenario
# - DRT created by smart contract creator
# - Account 2 buys the newly created DRT
# - The smart contract creator then wants to contribute more data to the pool
# - Account 2 is then added as a data contributor, contributing 7 rows of data
# - Account 2 buys the Append DRT and redeems it
# - Account 2 then decides  to buy 2 more DRTs 
# - The creator then claims their royalty fees 


echo "Create DRT"
echo ""

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

echo ""
echo "Store asset ID... "
ASSET_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk -F'"' '{print $2}' | head -6 | tail -1)
echo ""
echo "Account 2 purhases DRT..."
echo "To purchase a DRT, account 2 has to opt into the assset..."
echo ""

goal asset optin \
    --assetid $ASSET_ID \
    -a $ACCOUNT_2 \

echo ""
echo "Account 2 can now purchase the DRT..."
echo ""

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:buy_drt" \
    --app-arg "int:1" \
    --foreign-asset $ASSET_ID \
    --out txnAppCall.tx

goal clerk send \
    -a 3000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_2" \
    --out txnPayment.tx

cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx

echo ""
echo "Now the data pool creator wants to add more data to the pool that they created.."
echo "To do so, they first need to claim their pending fees... otherwise they wont be allowed to add more data."
echo "The creator claims fees.."
echo ""

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:claim_fees" \
    --foreign-asset $CONTRIB_ID \

echo ""
echo "Now that there are no outstanding fees to claim the creator can add data."
echo "The creator needs to send an instruction to the enclave to validate the incoming data"
echo "The enclave then sends a transaction to the smart contract to approve the additional data"
echo ""

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:creator_data_validation_add" \
    --app-arg "int:12" \
    --app-arg "str:DGVWUSNA--CREATOR--ASUDBQ" \
    --app-arg "int:1" \
    --foreign-asset $CONTRIB_ID \
    --app-account $ACCOUNT_1

echo ""
echo "Account 2 now wants to contribute data ..."
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
echo "Account 2 now wants to redeem the Append DRT and add data. "
echo "First, Account 2 needs to optin to the contributor token and the smart contract..."
echo "Opting in to contributor token..."
echo ""

goal asset optin \
    --assetid $CONTRIB_ID \
    -a $ACCOUNT_2 

echo ""
echo "Opting in to smart contract..."
echo ""

goal app optin \
    --app-id $APP_ID \
    --from $ACCOUNT_2 \

echo ""
echo "Now Account 2 can Redeem the Append DRT, by sending it back to smart contract and waiting on confirmation from enclave.."
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
    --app-arg "int:9" \
    --app-arg "str:DGVWUSNA--Newnew--ASUDBQ" \
    --app-arg "int:1" \
    --foreign-asset $CONTRIB_ID \
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
echo "Account 2 is now successfully added as a contributor"
echo ""
echo "Account 2 now wants to purchase 2 more DRTs..."
echo "Account 2 has to opt into the asset to receive the DRT"
echo ""

goal asset optin \
    --assetid $ASSET_ID \
    -a $ACCOUNT_2 \

echo ""
echo "Account 2 now purchases 2 DRTs"
echo ""

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:buy_drt" \
    --app-arg "int:2" \
    --foreign-asset $ASSET_ID \
    --out txnAppCall2.tx

goal clerk send \
    -a 6000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_2" \
    --out txnPayment2.tx

cat txnAppCall2.tx txnPayment2.tx > buyCombinedTxns2.tx
goal clerk group -i buyCombinedTxns2.tx -o buyGroupedTxns2.tx
goal clerk sign -i buyGroupedTxns2.tx -o signoutbuy2.tx
goal clerk rawsend -f signoutbuy2.tx

echo ""
echo "The creator now wants to claim their fees owed to them."
echo "The creators current balance is.."
echo ""

goal account balance -a $ACCOUNT_1

echo ""
echo "The creator now claims their fees"
echo ""

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:claim_fees" \
    --foreign-asset $CONTRIB_ID \

echo ""
echo "Balance of creator account after fees claimed.."

goal account balance -a $ACCOUNT_1

echo ""
echo "Test scenario complete."

