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
    --global-byteslices 3 \
    --global-ints 55 \
    --local-byteslices 2 \
    --local-ints 4 \
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
    -a 1000000 \
    -t "$ACCOUNT_APP" \
    -f "$ACCOUNT_1" \

echo ""

# the third will be to instruct the smart contract to create the contributor token
echo "Call smart contract to create contributor and append token"
goal app call \
    --app-id $APP_ID \
    -f $ACCOUNT_1 \
    --app-arg "str:contributor_append_token" \
    --app-arg "str:DRT_Contributor" \
    --app-arg "str:DRT_C" \
    --app-arg "int:10000" \
    --app-arg "str:Append_DRT" \
    --app-arg "str:DRT" \
    --app-arg "int:1000000"
    

export CONTRIB_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk '{print $2}' | head -28 | tail -1)
echo "Store contributor token ID: CONTRIB_ID=$CONTRIB_ID"

echo ""
export APPEND_ID=$(goal app read --global --app-id $APP_ID --guess-format | awk '{print $2}' | head -24 | tail -1)
echo "Store append DRT token ID: APPEND_ID=$APPEND_ID"

echo "Optin to contributor token"

goal asset optin \
    --assetid $CONTRIB_ID \
    -a $ACCOUNT_1 \

echo ""
echo "Add smart contract creator as a data contributor for initialisation, add data package hash"

goal app call \
    --app-id $APP_ID \
     -f $ACCOUNT_1 \
    --app-arg "str:add_creator_as_contributor" \
    --app-arg "int:5" \
    --app-arg "str:DGVWUSNA--DATA_PACKAGE_HASH--ASUDBQ" \
    --app-account $ACCOUNT_1 \
    --foreign-asset $CONTRIB_ID \
    
echo ""

echo "Smart Contract creation complete."