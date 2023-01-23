#### Script to test the following scenario
# - DRT created by smart contract creator
# - Account 2 buys the newly created DRT
# - Account 2 wants to add data so buys the Append DRT and redeems it
# - Account 2 is added as a data contributor and receives a contributor token representing their contribution
# - The creator then claims their royalty fees 

#!/bin/sh

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
    --app-arg "int:1000000" 

echo ""
echo "Store DRT asset ID... "
ASSET_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk -F'"' '{print $2}' | head -6 | tail -1)
echo ""
echo "Account 2 purhases the newly created DRT..."
echo "To purchase a DRT, account 2 has to opt into the assset..."
echo ""

goal asset optin \
    --assetid $ASSET_ID \
    -a $ACCOUNT_2 

echo ""
echo "Account 2 can now purchase the DRT..."
echo ""

pushd "${0%/*}"
box_name = `python3 /data/encode_decode_test.py $ASSET_ID $ACCOUNT_APP`
popd
echo "$box_name"

# goal app call \
#     --app-id $APP_ID \
#     -f $ACCOUNT_2 \
#     --app-arg "str:buy_drt" \
#     --app-arg "int:1" \
#     --foreign-asset $ASSET_ID \
#     --box "$APP_ID,b64:"
#     --out txnAppCall.tx

# goal clerk send \
#     -a 1000000 \
#     -t "$ACCOUNT_APP" \
#     -f "$ACCOUNT_2" \
#     --out txnPayment.tx

# cat txnAppCall.tx txnPayment.tx > buyCombinedTxns.tx
# goal clerk group -i buyCombinedTxns.tx -o buyGroupedTxns.tx
# goal clerk sign -i buyGroupedTxns.tx -o signoutbuy.tx
# goal clerk rawsend -f signoutbuy.tx

