goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:drt_to_box" \
    --foreign-asset $ASSET_ID \
    --box "$APP_ID,b64:$1" 