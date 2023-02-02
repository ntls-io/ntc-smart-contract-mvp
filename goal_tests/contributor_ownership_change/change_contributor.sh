echo "Optin to asset ID from buyer of contributor"
goal asset optin \
    --assetid $ASSET_ID \
    --account $ACCOUNT_2 

echo "initiate transfer and pay royalty fees to register new ownerhsip"

goal asset send \
    --assetid $ASSET_ID \
    --to $ACCOUNT_2 \
    --from $ACCOUNT_1 \
    --amount 1 \
    --out txnAssetTransfer.tx

goal clerk send \
    -a 1500000 \
    -t "$ACCOUNT_1" \
    -f "$ACCOUNT_2" \
    --out txnPayment.tx

goal clerk send \
    -a 75000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_2" \
    --out txnFees.tx

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:contributor_owner_change" \
    --box "str:$ASSET_ID" \
    --foreign-asset $ASSET_ID \
    --out txnAppCall.tx


cat txnAssetTransfer.tx txnPayment.tx txnFees.tx txnAppCall.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx

# --box "b64:AAAAAAAAAAv+Wgeg6daJwBdXLMa6VuVZJFiG88hV7E/BJj10KFLmDQ==" \

#AAAAAAAAAAAAAAAAAAAABSM+eHgR8rYopy+cmDhR5PBsSUp3WN39Dhippzz7q7gr