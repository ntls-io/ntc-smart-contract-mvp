
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
