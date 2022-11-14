source /data/script_creation.sh 

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:create_drt" \
    --app-arg "str:ALEX_DRT_01" \
    --app-arg "int:10000" \
    --app-arg "str:note" \
    --app-arg "int:3000000" \


ASSET_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk -F'"' '{print $2}' | head -2 | tail -1)

goal asset optin \
    --assetid $ASSET_ID \
    -a $ACCOUNT_NAUT \


goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_NAUT \
    --app-arg "str:buy_drt" \
    --app-arg "int:1" \
    --foreign-asset $ASSET_ID \
    --out txnAppCall.tx

goal clerk send \
    -a 3000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_NAUT" \
    --out txnPayment.tx

cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx


goal app optin \
    --app-id $APP_ID \
    --from $ACCOUNT_2 \

goal asset optin \
    --assetid $CONTRIB_ID \
    -a $ACCOUNT_2 \

goal app call \
    --app-id $APP_ID \
     -f $ACCOUNT_1 \
    --app-arg "str:add_contributor" \
    --app-arg "int:7" \
    --app-arg "str:SVCAJHVSC--hello---DHBSU#$" \
    --app-account $ACCOUNT_2 \
    --foreign-asset $CONTRIB_ID \


goal asset optin \
    --assetid $ASSET_ID \
    -a $ACCOUNT_NAUT \


goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_NAUT \
    --app-arg "str:buy_drt" \
    --app-arg "int:2" \
    --foreign-asset $ASSET_ID \
    --out txnAppCall2.tx

goal clerk send \
    -a 6000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_NAUT" \
    --out txnPayment2.tx

cat txnAppCall2.tx txnPayment2.tx > buyCombinedTxns2.tx
goal clerk group -i buyCombinedTxns2.tx -o buyGroupedTxns2.tx
goal clerk sign -i buyGroupedTxns2.tx -o signoutbuy2.tx
goal clerk rawsend -f signoutbuy2.tx

goal account balance -a $ACCOUNT_2

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:claim_fees" \
    --foreign-asset $CONTRIB_ID \

goal account balance -a $ACCOUNT_2

goal app read --global --app-id $APP_ID --guess-format