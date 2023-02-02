echo"optin to asset first for change of ownership"

goal asset optin \
    --assetid $ASSET_ID \
    --account $ACCOUNT_ENCLAVE 

echo "change ownerhsip of DRT"
goal asset send \
    --assetid $ASSET_ID \
    --to $ACCOUNT_ENCLAVE \
    --from $ACCOUNT_2 \
    --amount 1 \
    --out txnAssetTransfer.tx

goal clerk send \
    -a 1500000 \
    -t "$ACCOUNT_2" \
    -f "$ACCOUNT_ENCLAVE" \
    --out txnPayment.tx

goal clerk send \
    -a 75000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_ENCLAVE" \
    --out txnFees.tx

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:drt_owner_change" \
    --box "b64:$1" \
    --box "b64:$2" \
    --foreign-asset $ASSET_ID \
    --out txnAppCall.tx


cat txnAssetTransfer.tx txnPayment.tx txnFees.tx txnAppCall.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx