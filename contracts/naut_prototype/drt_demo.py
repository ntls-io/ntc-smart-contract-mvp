from pyteal import *
from pyteal.ast.bytes import Bytes
from pyteal_helpers import program
from pyteal_helpers.strings import itoa

DRT_UNIT_NAME = Bytes("DRT") #need to confirm
CONTRIBUTOR_UNIT_NAME = Bytes("DRT_C") #came up with this by myself, need to confirm
DEFAULT_HASH = Bytes("base64", "y9OJ5MRLCHQj8GqbikAUKMBI7hom+SOj8dlopNdNHXI=")
DEFAULT_NOTE= Bytes("")
DEFAULT_URL= Bytes("")

def approval():
    # Stored global variables
    global_data_package_hash = Bytes("data_package_hash")               # The hash of the data pool
    global_enclave_address = Bytes("enclave_address")                   # The account of the nautilus wallet   
    global_contributor_asset_id = Bytes("global_contributor_asset_id")  # Asset ID of contributor token
    global_append_asset_id = Bytes("global_append_asset_id")            # Asset ID of append token
    global_drt_counter= Bytes("drt_counter")                            # Counter of available DRTs
    global_drt_payment_row_average = Bytes("drt_payment_row_average")   # Computational variable for royalty fees
    global_dataset_total_rows = Bytes("dataset_total_rows")             # Computational variable for royalty fees
    global_total_fees = Bytes("total_fees")                             # Current total fees available
    
    # Stored local variables
    local_rows_contributed = Bytes("rows_contributed")                  # Computational variable for royalty fees 
    local_g_drt_payment_row_average = Bytes("g_drt_payment_row_average")# Computational variable for royalty fees
    local_no_times_contributed = Bytes("no_times_contributed")          # No. times contributed to pool
 
    # Methods
    op_create_drt = Bytes("create_drt")                                 # Method call
    op_update_data_package = Bytes("update_data_package")               # Method call
    op_contributor_append_token = Bytes("contributor_append_token")     # Method call
    op_creator_contribution = Bytes("add_creator_as_contributor")       # Method call   
    op_update_drt_price = Bytes("update_drt_price")                     # Method call
    op_buy_drt = Bytes("buy_drt")                                       # Method call
    op_claim_fees = Bytes("claim_fees")                                 # Method call
    op_append_drt = Bytes("add_data_contributor")                       # Method call
    op_add_creator_contribution = Bytes("creator_data_validation_add")  # Method call
    
    @Subroutine(TealType.none)
    def defaultTransactionChecks(txnId: Expr):
        
    # This subroutine is used to perform some default checks on the
    # incoming transactions.
    # For a given index of the transaction to check, it verifies that
    # the rekeyTo, closeRemainderTo, and the assetCloseTo attributes
    # are set equal to the zero address
    # :param Int txnId : Index of the transaction
    
        return Seq([
                Assert(txnId < Global.group_size()),
                Assert(Gtxn[txnId].rekey_to() == Global.zero_address()),
                Assert(Gtxn[txnId].close_remainder_to() == Global.zero_address()),
                Assert(Gtxn[txnId].asset_close_to() == Global.zero_address())
        ])

    @Subroutine(TealType.none)
    def inner_sendPayment(receiver: Expr, amount: Expr):
    # """
    # This subroutine can be used to send payments from the smart
    # contract to other accounts using inner transactions
    # :param Addr receiver : The receiver of the payment
    # :param Int amount    : Amount to send in microalgos
    # """
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.amount: amount,
                TxnField.receiver: receiver,
            }),
            InnerTxnBuilder.Submit(),
        ])

# inner trasnction to create the DRT as an ASA
    @Subroutine(TealType.uint64)
    def inner_asset_create_txn(name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr):
        #convert to pyteal uint64
        btoi_amount = Btoi(amount)

        return Seq(      
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields( 
                {
                    TxnField.type_enum: TxnType.AssetConfig, #transaction type
                    TxnField.config_asset_total: btoi_amount,
                    TxnField.config_asset_decimals: Int(0),
                    TxnField.config_asset_unit_name: unit_name,
                    TxnField.config_asset_name: name,
                    TxnField.config_asset_url: asset_url,
                    TxnField.config_asset_metadata_hash: binHash,
                    TxnField.config_asset_manager: Global.current_application_address(),
                    TxnField.config_asset_reserve: Global.current_application_address(),
                    TxnField.note: note,
                }
            ),
            InnerTxnBuilder.Submit(), #finalise   
            Return (InnerTxn.created_asset_id()) #return asset id
        )

# function to transfer asset-id to another account
    @Subroutine(TealType.none)
    def inner_asset_transfer_txn(
        asset_id: Expr,
        asset_amount: Expr,
        asset_receiver: Expr):
  
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset_id,
                TxnField.asset_amount: asset_amount,
                TxnField.asset_receiver: asset_receiver,
                }),
            InnerTxnBuilder.Submit()
        ])

# function to update the global variable - global_drt_payment_row_average
    @Subroutine(TealType.uint64)
    def compute_global_drt_payment_row_average(g_n__1: Expr, l_n: Expr, v_n: Expr):
        return Seq(
            Assert(
                g_n__1 == App.globalGet(global_drt_payment_row_average), 
            ),
            
            Return (Div(v_n,l_n) + g_n__1)
        )
        
 # function to compute the royalty fee
    @Subroutine(TealType.uint64)
    def compute_royalty_fee(acc: Expr):
        l_size = App.localGet(acc, local_rows_contributed)
        l_average = App.localGet(acc, local_g_drt_payment_row_average)
        g_average = App.globalGet(global_drt_payment_row_average)
        return Seq(
            Return (l_size*(g_average - l_average))
        )

# function to update the global variable to a new data package hash. 
    @Subroutine(TealType.none)
    def update_data_package():
        return Seq(
            #basic sanity checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), #require the fee of this input transaction to cover the fee of the inner tranaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #ensure the transaction sender is the nautilus wallet address
                    Txn.sender() == Global.creator_address(),
                    #ensure there is atleast 2 arguments
                    Txn.application_args.length() == Int(2), 
                )
            ),
            #update data package to new hash
            App.globalPut(global_data_package_hash, Txn.application_args[1]),

            Approve(),
        )

# Function to initiliase the creation of a DRT, incorporates the inner_asset_create_txn function
    @Subroutine(TealType.none)
    def create_drt():
        asset_id = ScratchVar()
        exchange_rate=ScratchVar()
        creator_times_contributed = App.localGet(Txn.sender(),local_no_times_contributed)
        return Seq(
            #basic sanity checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), #ensure 1 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #ensure the transaction sender is the data_creator , i.e. the creator of the smart contract
                    Txn.sender() == Global.creator_address(),
                    #ensure there is less than 50 drt counter
                    App.globalGet(global_drt_counter) < Int(50),
                    #ensure there is atleast 2 arguments
                    Txn.application_args.length() == Int(7), # instruction, name, amount, url of binary, hash of binary, note, exchange price
                    #ensure the creator has contributed, i.e. there is data to create a drt from
                    creator_times_contributed == Int(1),
                )
            ),
            #create drt and record asset id
            #name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr
            asset_id.store(inner_asset_create_txn(Txn.application_args[1],DRT_UNIT_NAME ,Txn.application_args[2], Txn.application_args[3] ,Txn.application_args[4], Txn.application_args[5])),
            #store DRT price in contract alongside asset id in globals
            exchange_rate.store(Btoi(Txn.application_args[6])),
            App.globalPut(itoa(asset_id.load()),exchange_rate.load()),
            #incremement counter
            App.globalPut(global_drt_counter, App.globalGet(global_drt_counter) + Int(1)),
            Approve(),
        )

# init function to create the contributor token
    @Subroutine(TealType.none)
    def init_create_contributor_append():
        contrib_id = ScratchVar()
        append_id = ScratchVar()
        contrib_exist = App.globalGet(global_contributor_asset_id)
        append_exist = App.globalGet(global_append_asset_id)
        btoi_rate = Btoi(Txn.application_args[6])
        return Seq(
            #basic sanity checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), 
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    Txn.sender() == Global.creator_address(), #ensure transaction sender is the smart contract creator
                    contrib_exist == Int(0), #ensure there is not already a data contributor token created
                    append_exist == Int(0),  #ensure there is not already append DRT created
                )
            ),
            #name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr
            contrib_id.store(inner_asset_create_txn(Txn.application_args[1],Txn.application_args[2] ,Txn.application_args[3], DEFAULT_URL , DEFAULT_HASH, DEFAULT_NOTE)), #use scratch variable to store asset id of contributor token
            append_id.store(inner_asset_create_txn(Txn.application_args[4],Txn.application_args[5], Txn.application_args[3], DEFAULT_URL , DEFAULT_HASH, DEFAULT_NOTE)), #use scratch variable to store asset id of contributor token

            
            #store asset id in gloabl variable
            App.globalPut(global_contributor_asset_id,contrib_id.load()), 
            App.globalPut(global_append_asset_id,append_id.load()), 
            
            #store new price
            App.globalPut(itoa(append_id.load()),btoi_rate),
            Approve(),
        )

# init function to add the creators data contributions
    @Subroutine(TealType.none)
    def init_add_creator_contribution(added_account: Expr, asset_id: Expr):
        accountAssetBalance = AssetHolding.balance(added_account, asset_id) #check creator has opted into contributor
        new_rows = Btoi(Txn.application_args[1]) #store rows of data to append
        royalty_fee = compute_royalty_fee(added_account) #compute creator royalty fee
        new_hash = Txn.application_args[2] #store the new data hash
        creator_no_contributed = App.localGet(Txn.sender(),local_no_times_contributed)
        return Seq(
            accountAssetBalance,
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                 group_size=Int(1), #ensure 1 transaction
                 group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #check the sender of the transactrion is the smart contract creator
                    Txn.sender() == Global.creator_address(),
                    #check that the recevier of the token has opted in. 
                    accountAssetBalance.hasValue(),
                    #check the passed asset is the equal to the globally stored one
                    App.globalGet(global_contributor_asset_id) == Txn.assets[0],
                     #ensure there is atleast 3 arguments
                    Txn.application_args.length() == Int(3), #ensure there is add contributor arguments
                    #check added_account is opted in 
                    App.optedIn(added_account, Global.current_application_id()),
                    #ensure royalty fee is zero for added account
                    royalty_fee == Int(0),
                    # ensure hashes are not the same
                    new_hash != App.globalGet(global_data_package_hash),
                    #ensure new hash not nothing
                    new_hash != Bytes(""),
                    #ensure added account is creators address
                    added_account == Global.creator_address(),
                    #ensure creator has not already contributed
                    creator_no_contributed == Int(0),
                )
            ),
            #send contributor asset to creator
            inner_asset_transfer_txn(asset_id, Int(1), Txn.sender()),
        
            # add contribution counter in local variable
            App.localPut(added_account, local_no_times_contributed, Int(1)),           
            # add new row average to local
            App.localPut(Txn.sender(),local_g_drt_payment_row_average, App.globalGet(global_drt_payment_row_average)),    
            # add no of rows contributed
            App.localPut(added_account,local_rows_contributed, (Btoi(Txn.application_args[1]) + App.localGet(added_account, local_rows_contributed))),
        
            #update global hash 
            App.globalPut(global_data_package_hash, new_hash),
            #update global row counter
            App.globalPut(global_dataset_total_rows, (new_rows + App.globalGet(global_dataset_total_rows))),

            Approve(),
        )

# function to add the creators data contributions after initialisation of pool, i.e. add more data a second time round.
    @Subroutine(TealType.none)
    def add_creator_contribution():
        
        accountAssetBalance = AssetHolding.balance(Txn.accounts[1], Txn.assets[0]) #check creator has opted into contributor and has a contributor token
        royalty_fee = compute_royalty_fee(Txn.accounts[1]) #compute creator royalty fee
        creator_no_contributed = App.localGet(Txn.accounts[1],local_no_times_contributed) #store no times contributed
        
        
        new_rows = Btoi(Txn.application_args[1]) #store rows of data to append, gathered from enclave
        new_hash = Txn.application_args[2] #store the new data hash, gathered from enclave
        approved = Btoi(Txn.application_args[3]) #approved yes (1) or no (0)
        
        return Seq(
            accountAssetBalance,
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                 group_size=Int(1), #ensure 2 transactions
                 group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #check the sender of transaction 1 is the enclave address
                    Txn.sender() == App.globalGet(global_enclave_address),
                    #check the sender of transaction 2 is the enclave
                    Txn.accounts[1] == Global.creator_address(),
                    # #check it is approved
                    approved == Int(1),
                    # #check that the receiver of the token has opted in. 
                    accountAssetBalance.hasValue(),
                    #ensure asset provided is the same as contributor asset ID
                    Txn.assets[0] == App.globalGet(global_contributor_asset_id),
                    # #ensure there is atleast 4 arguments
                    Txn.application_args.length() == Int(4),
                    #check creator is still opted in 
                    App.optedIn(Txn.accounts[1], Global.current_application_id()),
                    #ensure royalty fee is zero for creator
                    royalty_fee == Int(0),
                    #ensure hashes are not the same
                    new_hash != App.globalGet(global_data_package_hash),
                    #ensure new hash not nothing
                    new_hash != Bytes(""),
                    #ensure creator has already contributed during initialisation
                    creator_no_contributed > Int(0),
                )
            ),
            # add contribution counter in local variable
            App.localPut(Txn.accounts[1], local_no_times_contributed, (creator_no_contributed+Int(1))),       
            # add new row average to local
            App.localPut(Txn.accounts[1],local_g_drt_payment_row_average, App.globalGet(global_drt_payment_row_average)),    
            # add no of rows contributed
            App.localPut(Txn.accounts[1],local_rows_contributed, (new_rows + App.localGet(Txn.accounts[1], local_rows_contributed))),
        
            #update global hash 
            App.globalPut(global_data_package_hash, new_hash),
            #update global row counter
            App.globalPut(global_dataset_total_rows, (new_rows + App.globalGet(global_dataset_total_rows))),
            Approve(),
        )


# Function to update the global variable to a new data package hash. 
    @Subroutine(TealType.none)
    def update_drt_price():
        drt_exist = App.globalGetEx(Int(0), itoa(Txn.assets[0])) #Int(0) represnets the smart contract address
        btoi_rate = Btoi(Txn.application_args[1])
        return Seq(
            drt_exist,
            #basic sanity checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), #require the fee of this input transaction to cover the fee of the inner tranaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #ensure the transaction sender is the nautilus wallet address
                    Txn.sender() == Global.creator_address(),
                    #ensure that this drt exists
                    drt_exist.hasValue(),
                )
            ),
            #store new price
            App.globalPut(itoa(Txn.assets[0]),btoi_rate),

            Approve(),
        )

# Function to transfer contributor token
    @Subroutine(TealType.none)
    def claim_royalty(account: Expr, asset_id: Expr):
        accountAssetBalance = AssetHolding.balance(account, asset_id)
        royalty_fee = compute_royalty_fee(account)
        fees_change = ScratchVar()
        return Seq(
            accountAssetBalance,
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), #ensure 1 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #check the passed asset is the equal to the globally stored one
                    App.globalGet(global_contributor_asset_id) == asset_id,
                    #check that the recevier of the token has opted in and has a balance of 1 contributor token
                    accountAssetBalance.hasValue(),
                    #ensure the correct amount of arguments
                    Txn.application_args.length() == Int(1), 
                    #check added_account has opted into smart contract
                    App.optedIn(account, Global.current_application_id()),
                    #ensure royalty fee is greater than zero account
                    royalty_fee > Int(0),
                    App.globalGet(global_total_fees) >= royalty_fee,
                )
            ),
            fees_change.store(royalty_fee),
            #transfer the amount
            inner_sendPayment(Txn.sender(), royalty_fee),
            #reset the local variable ( as if the user has rejoined the pool )
            App.localPut(account,local_g_drt_payment_row_average, App.globalGet(global_drt_payment_row_average)),          
            #minus fee payout from total fees collected
            App.globalPut(global_total_fees, (App.globalGet(global_total_fees) - fees_change.load())),
            #Approve
            Approve(),
        )
   
# Function to buy a created DRT, incorporates the inner_asset_create_txn function
    @Subroutine(TealType.none)
    def buy_drt():
        assetToBuy = Gtxn[0].assets[0]
        paymentAmount = Gtxn[1].amount()
        assetExchangeRate = App.globalGet(itoa(assetToBuy))
        drt_exist = App.globalGetEx(Int(0), itoa(assetToBuy))
        buyerOptIn = AssetHolding.balance(Gtxn[0].sender(), assetToBuy)
        assetSupply = AssetHolding.balance(Global.current_application_address(), assetToBuy)
        g_n = compute_global_drt_payment_row_average(App.globalGet(global_drt_payment_row_average), App.globalGet(global_dataset_total_rows) , paymentAmount)
        return Seq(
            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            defaultTransactionChecks(Int(1)), # Perform default transaction checks
            drt_exist,
            buyerOptIn,
            assetSupply,
            #basic sanity checks
            program.check_self(
                group_size=Int(2), #ensure 2 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    Gtxn[1].type_enum() == TxnType.Payment,
                    drt_exist.hasValue(), # Check drt exists
                    paymentAmount == (assetExchangeRate*Btoi(Gtxn[0].application_args[1])), # Check amount to be paid is correct (exchange rate * how many)
                    Global.current_application_address() == Gtxn[1].receiver(), # check the reciever of the payment (2nd transaction) is the app
                    buyerOptIn.hasValue(), #ensure the user has opted in to asset
                    assetSupply.value() >= Btoi(Gtxn[0].application_args[1]), #ensure there is enough supply
                    Gtxn[0].application_args.length() == Int(2),   #ensure there is atleast 2 arguments
                    Gtxn[0].sender() == Gtxn[1].sender(),
                    #g_n > Int(0), #g_n greater than 0
                )
            ),
            #store it 
            App.globalPut(global_drt_payment_row_average, g_n),
            App.globalPut(global_total_fees, (paymentAmount + App.globalGet(global_total_fees))),
             # if the above checks out, transfer asset
            inner_asset_transfer_txn(assetToBuy, Btoi(Gtxn[0].application_args[1]), Gtxn[0].sender()),
            
            Approve(),
        )

# # Function to redeem the Append DRT [WIP]
#     @Subroutine(TealType.none)
#     def redeem_append_drt():
#         return Seq(
#             Assert(
#                 And(
#                     Gtxn[0].type_enum() == TxnType.AssetTransfer,
#                     #Global.current_application_address() == Gtxn[0].receiver(), # check the reciever of the asset transfer is the smart cotnract
                    
#                 )
#             ),
#             App.globalPut(Bytes("Gtxn[0].receiver()"), Gtxn[0].amount()),
#             Approve(),
#         )


# Check the transaction type and execute the corresponding code
# 1. If smart contract does not exist it will trigger the initialisation sequence contained in the "init" variable.
# 2. An Optin transaction is simply approved.
# 3. If the transaction type is a NoOp transaction, i.e. an Application Call, then it checks the first argument of the call which must be equal to one of the method call variables
# "op_create_drt", "op_update_data_package", "op_contributor_append_token", "op_new_contributor", "op_update_drt_price", "op_update_drt_price", 
# "op_buy_drt", "op_claim_fees".
    return program.event(
        init=Seq( 
            [
                Assert(
                    # Check if it's an application call
                    Txn.type_enum() == TxnType.ApplicationCall,
                    # Check the arguments length
                    Txn.application_args.length() == Int(0),
                    # Check the accounts length 
                    Txn.accounts.length() == Int(1),
                    ),                  
                # Store nautilus company wallet address 
                App.globalPut(global_enclave_address, Txn.accounts[1]), 
                # Initialise global variables
                App.globalPut(global_drt_counter, Int(0)),
                App.globalPut(global_drt_payment_row_average, Int(0)),
                App.globalPut(global_dataset_total_rows, Int(0)), 
                App.globalPut(global_total_fees, Int(0)),
                App.globalPut(global_data_package_hash, Bytes("")),
                # Then approve.
                Approve(), 
            ]
        ),
        opt_in=Seq(
            Approve(),
        ),
        no_op=Seq(
            # Condition expression
            Cond( 
                [
                    Txn.application_args[0] == op_create_drt,
                    create_drt(),
                ],
                [
                    Txn.application_args[0] == op_update_data_package,
                    update_data_package(),
                ],
                [
                    Txn.application_args[0] == op_creator_contribution,
                    init_add_creator_contribution(Txn.accounts[1], Txn.assets[0]),
                ],
                [
                    Txn.application_args[0] == op_contributor_append_token,
                    init_create_contributor_append(),
                ],
                 [
                    Txn.application_args[0] == op_add_creator_contribution,
                    add_creator_contribution(),
                ],
                [
                    Txn.application_args[0] == op_update_drt_price,
                    update_drt_price(),
                ],
                 [
                    Txn.application_args[0] == op_buy_drt,
                    buy_drt(),
                ],
                 [
                    Txn.application_args[0] == op_claim_fees,
                    claim_royalty(Txn.sender(), Txn.assets[0]),
                ],
                #   [
                #     Txn.application_args[0] == op_append_drt,
                #     redeem_append_drt(),
                # ],
            ),
            Reject(),
        ),
    )


def clear():
    return Approve()
