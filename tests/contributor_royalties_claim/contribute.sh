echo "Smart Contract creator wants to claim their fees from their contributor token"
echo ""
echo "The balance of the smart contract creators account before claiming the fees"

goal account balance --address $ACCOUNT_1

echo ""
echo "Creator claims their fees.. "
echo ""

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:claim_royalty_contributor" \
    --box "str:$CONTRIB_1_ID" \
    --foreign-asset $CONTRIB_1_ID

echo ""
echo "The balance of the smart contract creators account after claiming the fees"

goal account balance --address $ACCOUNT_1

echo ""