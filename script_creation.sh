############# Smart Contract Calls using goal CLI #############

### Smart Contract Creation ###
echo ""
echo "Set configuration variables"

export ACCOUNT_1=$(goal account list | awk '{print $3}' | head -1 | tail -1)
export ACCOUNT_2=$(goal account list | awk '{print $3}' | head -2 | tail -1)
export ACCOUNT_NAUT=$(goal account list | awk '{print $3}' | head -3 | tail -1)

echo "ACCOUNT_1=$ACCOUNT_1"
echo "ACCOUNT_2=$ACCOUNT_2"
echo "ACCOUNT_NAUT=$ACCOUNT_NAUT"
echo ""
#first you need to deploy the smart contract.
# the first transaction will be to initialise the smart contract
echo "Create Smart Contract....."

export APP_ID=$(
goal app create \
    --creator $ACCOUNT_1 \
    --approval-prog /data/build/approval.teal \
    --clear-prog /data/build/clear.teal \
    --global-byteslices 5 \
    --global-ints 55 \
    --local-byteslices 0 \
    --local-ints 0 \
    --extra-pages 1 \
    --app-arg "str:DGVWUSNA--DATA_PACKAGE_HASH--ASUDBQ" \
    --app-account $ACCOUNT_NAUT \
    --fee 2000 |
    grep Created |
    awk '{ print $6 }'
)
echo ""
echo "Store Smart Contract variables."
echo "APPLICATION ID of Smart Contract: APP_ID=$APP_ID"  
# second will be to fund the smart contract with minimum amount of algos - 2000
# but first you need to set the  ACCOUNT_APP to point to the account address of the newly created smart contract.
# to get the smart contract account use the following
export ACCOUNT_APP=$(goal app info  --app-id "$APP_ID" | awk '{print $3}' | head -2 | tail -1)

echo "APPLICATION ADDRESS of Smart Contract: ACCOUNT_APP=$ACCOUNT_APP" 
echo ""
echo "Fund smart contract from ACCOUNT_1"
#now you can fund the smart contract from account 1
goal clerk send \
    -a 1000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_1" \

echo ""
echo "Call smart contract to create contributor token"
# the third will be to instruct the smart contract to create the contributor token
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:contributor_token" \

echo ""
export CONTRIB_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk '{print $2}' | head -15 | tail -1)
echo "Store contributor token ID: CONTRIB_ID=$CONTRIB_ID"
echo ""
echo "Smart Contract creation complete."