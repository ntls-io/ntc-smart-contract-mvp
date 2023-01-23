############# Smart Contract Calls using goal CLI #############

### Smart Contract Creation ###
echo ""
echo "Set configuration variables"

export ACCOUNT_1=$(goal account list | awk '{print $3}' | head -1 | tail -1)
export ACCOUNT_2=$(goal account list | awk '{print $3}' | head -2 | tail -1)
export ACCOUNT_ENCLAVE=$(goal account list | awk '{print $3}' | head -3 | tail -1)

echo "ACCOUNT_1=$ACCOUNT_1"
echo "ACCOUNT_2=$ACCOUNT_2"
echo "ACCOUNT_ENCLAVE=$ACCOUNT_ENCLAVE"
echo ""
#first you need to deploy the smart contract.
# the first transaction will be to initialise the smart contract
echo "Create Smart Contract....."

export APP_ID=$(
goal app create \
    --creator $ACCOUNT_1 \
    --approval-prog /data/build/approval.teal \
    --clear-prog /data/build/clear.teal \
    --global-byteslices 6 \
    --global-ints 50 \
    --local-byteslices 2 \
    --local-ints 5 \
    --extra-pages 2 \
    --app-account $ACCOUNT_ENCLAVE |
    grep Created |
    awk '{ print $6 }'
)

echo ""
echo "Store Smart Contract variables."
echo "APPLICATION ID of Smart Contract: APP_ID=$APP_ID"  

# second will be to fund the smart contract with minimum amount of algos - 200000
# but first you need to set the  ACCOUNT_APP to point to the account address of the newly created smart contract.
# to get the smart contract account use the following
export ACCOUNT_APP=$(goal app info  --app-id "$APP_ID" | awk '{print $3}' | head -2 | tail -1)

echo "APPLICATION ADDRESS of Smart Contract: ACCOUNT_APP=$ACCOUNT_APP" 
echo ""
echo "Optin to Smart Contract"
goal app optin \
    --app-id $APP_ID \
    --from $ACCOUNT_1 \
    
echo ""
echo "Fund smart contract from ACCOUNT_1"
#now you can fund the smart contract from account 1
goal clerk send \
    -a 100000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_1" \

echo ""

# the third will be to instruct the smart contract to create the contributor token
echo "Call to initialise smart contracts first contribution, called by the enclave"
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_ENCLAVE \
    --app-arg "str:init_contract" \
    --app-arg "int:5" \
    --app-arg "str:DGVWUSNA--init--ASUDBQ" \
    --app-arg "str:Append_DRT" \
    --app-arg "str:DRT" \
    --app-arg "int:1000000" \
    --app-account $ACCOUNT_1 
    
echo ""
export APPEND_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk -F'"' '{print $2}' | head -2 | tail -1)
echo "Store Append token ID: APPEND_ID=$APPEND_ID"
export CONTRIB_1_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk '{print $2}' | head -37 | tail -1)
echo "Store contributor token ID: CONTRIB_1_ID=$CONTRIB_1_ID"
echo ""
echo "Smart contract creator must claim their contributor token from their initial contribution..."
echo "1. Optin to contributor token"
goal app read --global --app-id $APP_ID --guess-format

goal asset optin \
    --assetid $CONTRIB_1_ID \
    -a $ACCOUNT_1 \

echo ""
echo "2. Claim contributor token... "

goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:box_store_transfer" \
    --foreign-asset $CONTRIB_1_ID \
    --box "str:$CONTRIB_1_ID"
    
echo ""

echo "Smart Contract creation complete."