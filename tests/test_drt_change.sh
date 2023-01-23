#### Script to test the following scenario
# - DRT created by smart contract creator
# - Account 2 buys the newly created DRT
# - Account 2 wants to add data so buys the Append DRT and redeems it
# - Account 2 is added as a data contributor and receives a contributor token representing their contribution
# - The creator then claims their royalty fees 


echo "Test"
echo ""
## drt to box app call after DRT has been created.
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:drt_to_box" \
    --foreign-asset 36 \
    --box "$APP_ID,b64:AAAAAAAAACSyoe4P+GYzSlKficYnyPm/4M9uctPzvSGd7jhSUQDCjw==" 


## transactions to buy a DRT
goal asset optin \
    --assetid 63 \
    -a $ACCOUNT_2 

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_2 \
    --app-arg "str:buy_drt" \
    --app-arg "int:1" \
    --foreign-asset 63 \
    --box "$APP_ID,b64:AAAAAAAAAD9UUco3BNy8fjhbntGkvNzn+j+BLbmglVrBIFNvqTILLQ==" \
    --box "$APP_ID,b64:AAAAAAAAAD/mto+47c5q8eYw5GhzlR4dw36YIZ7PBI7gMMWbGPkvdA==" \
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

##optin to asset first for change of ownership
goal asset optin \
    --assetid 63 \
    --account $ACCOUNT_ENCLAVE 

# ownership change of DRT
goal asset send \
    --assetid 63 \
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
    --box "b64:AAAAAAAAAD/mto+47c5q8eYw5GhzlR4dw36YIZ7PBI7gMMWbGPkvdA==" \
    --box "b64:AAAAAAAAAD/+Wgeg6daJwBdXLMa6VuVZJFiG88hV7E/BJj10KFLmDQ==" \
    --foreign-asset 63 \
    --out txnAppCall.tx


cat txnAssetTransfer.tx txnPayment.tx txnFees.tx txnAppCall.tx > buyCombinedTxns.tx
goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
goal clerk rawsend -f signoutbuy.tx

# --box "b64:AAAAAAAAAAv+Wgeg6daJwBdXLMa6VuVZJFiG88hV7E/BJj10KFLmDQ==" \

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:update_drt_price" \
    --app-arg "int:1000000" \
    --box "b64:AAAAAAAAACSyoe4P+GYzSlKficYnyPm/4M9uctPzvSGd7jhSUQDCjw==" \
    --foreign-asset 36

