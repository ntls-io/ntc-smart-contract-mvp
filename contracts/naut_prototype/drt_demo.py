from typing import TypeVar
from pyteal import *
from pyteal.ast.bytes import Bytes
from pyteal_helpers import program
from pyteal_helpers.strings import itoa
from algosdk.future.transaction import StateSchema

DRT_UNIT_NAME = Bytes("DRT") #need to confirm
DRT_ASSET_URL = Bytes("https://gold.rush") #this is just for testing... 
CONTRIBUTOR_UNIT_NAME = Bytes("DRT_C") #came up with this by myself, need to confirm
DEFAULT_NOTE= Bytes("")

def approval():
    #globals
    global_data_package_hash = Bytes("data_package_hash") 
    global_company_wallet_address = Bytes("company_wallet_address") 
    global_contributor_asset_id = Bytes("global_contributor_asset_id")
    global_drt_counter= Bytes("drt_counter")
    global_drt_payment_row_average = Bytes("drt_payment_row_average")
    global_dataset_total_rows = Bytes("dataset_total_rows")
    global_total_fees = Bytes("total_fees")
    
    #locals
    local_rows_contributed = Bytes("rows_contributed")
    local_g_drt_payment_row_average = Bytes("g_drt_payment_row_average")
    local_no_times_contributed = Bytes("no_times_contributed")
 
    #operations
    op_create_drt = Bytes("create_drt") 
    op_update_data_package = Bytes("update_data_package") 
    op_contributor_token = Bytes("contributor_token") 
    op_new_contributor = Bytes("add_contributor")
    op_update_drt_price = Bytes("update_drt_price")
    op_buy_drt = Bytes("buy_drt")
    op_claim_fees = Bytes("claim_fees")
    
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
    def inner_asset_create_txn(name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, note: Expr):
        #convert to pyteal uint64
        btoi_amount = Btoi(amount)

        return Seq(      
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields( #python dictionariy
                {
                    TxnField.type_enum: TxnType.AssetConfig, #transaction type
                    TxnField.config_asset_total: btoi_amount,
                    TxnField.config_asset_decimals: Int(0),
                    TxnField.config_asset_unit_name: unit_name,
                    TxnField.config_asset_name: name,
                    TxnField.config_asset_url: asset_url,
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
                    App.globalGet(global_drt_counter) < Int(50)
                    #ensure there is atleast 2 arguments
                    #Txn.application_args.length() == Int(3), #ensure there is, amount, name, hash of database schema, hash of binary
                )
            ),
            #create drt and record asset id
            asset_id.store(inner_asset_create_txn(Txn.application_args[1],DRT_UNIT_NAME ,Txn.application_args[2], DRT_ASSET_URL ,Txn.application_args[3])),
            #store DRT price in contract alongside asset id in globals
            exchange_rate.store(Btoi(Txn.application_args[4])),
            App.globalPut(itoa(asset_id.load()),exchange_rate.load()),
            #incremement counter
            App.globalPut(global_drt_counter, App.globalGet(global_drt_counter) + Int(1)),
            Approve(),
        )

#function to create the contributor token
    @Subroutine(TealType.none)
    def create_contributor_token():
        asset_id = ScratchVar()
        contrib_exist = App.globalGet(global_contributor_asset_id)
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
                    Txn.sender() == Global.creator_address(), #ensure transaction sender is the smart contract creator
                    contrib_exist == Int(0) #ensure there is not already a data contributor
                )
            ),
            asset_id.store(inner_asset_create_txn(Bytes("DRT_Contributor"),CONTRIBUTOR_UNIT_NAME ,Bytes("1000"), DRT_ASSET_URL ,DEFAULT_NOTE)), #use scratch variable to store asset id of contributor token
            App.globalPut(global_contributor_asset_id,asset_id.load()), #store asset id in gloabl variable
            # App.localPut(Txn.sender(),local_g_drt_payment_row_average, App.globalGet(global_drt_payment_row_average)),       
            # App.localPut(Txn.sender(),local_rows_contributed, Btoi(Txn.application_args[1]) ),
            # App.localPut(Txn.sender(),local_no_times_contributed, Int(0)),
            #App.globalPut(global_dataset_total_rows, Btoi(Txn.application_args[1])),
            Approve(),
        )

#function to transfer contributor token
    @Subroutine(TealType.none)
    def add_new_contributor(added_account: Expr, asset_id: Expr):
        accountAssetBalance = AssetHolding.balance(added_account, asset_id)
        new_rows = Btoi(Txn.application_args[1])
        creator_times_contributed = App.localGet(Global.creator_address(),local_no_times_contributed)
        royalty_fee = compute_royalty_fee(added_account)
        new_hash = Txn.application_args[2]
        return Seq(
            accountAssetBalance,
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            #defaultTransactionChecks(Int(1)),
            program.check_self(
                # group_size=Int(1), #ensure 1 transaction
                # group_index=Int(0),
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
                )
            ),
            #part of the smart contract initialisation
            If(And(creator_times_contributed == Int(0), App.globalGet(global_dataset_total_rows) == Int(0)))
            .Then( 
                  inner_asset_transfer_txn(asset_id, Int(1), Global.creator_address()),
                  App.localPut(Txn.sender(), local_no_times_contributed, Int(1)),
                  App.localPut(Txn.sender(),local_g_drt_payment_row_average, App.globalGet(global_drt_payment_row_average)),       
                  App.localPut(Txn.sender(),local_rows_contributed, new_rows ),
                  App.globalPut(global_dataset_total_rows, new_rows),
                  App.globalPut(global_data_package_hash, new_hash),
                  Approve(),
                  )
            #post initialisation
            .ElseIf(creator_times_contributed > Int(0))
            .Then(
                App.localPut(added_account,local_g_drt_payment_row_average, App.globalGet(global_drt_payment_row_average)),       
                App.localPut(added_account,local_rows_contributed, (Btoi(Txn.application_args[1]) + App.localGet(added_account, local_rows_contributed))),
                App.localPut(added_account, local_no_times_contributed, (App.localGet(added_account, local_no_times_contributed)+Int(1))),
                App.globalPut(global_data_package_hash, new_hash),
                App.globalPut(global_dataset_total_rows, (new_rows + App.globalGet(global_dataset_total_rows))),
                Approve(),
                ),
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
            #update data package to new hash
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

    return program.event(
        
        init=Seq( #if statement to determine what type of transaction this is. init is triggered when the smart contract is created/initialised
            [
                #App.globalPut(global_data_package_hash, Txn.application_args[0]), #put data package hash in global.... 
                App.globalPut(global_company_wallet_address, Txn.accounts[1]), #put nautilus enclave wallet address in global.... 
                App.globalPut(global_drt_counter, Int(0)),
                App.globalPut(global_drt_payment_row_average, Int(0)),
                App.globalPut(global_dataset_total_rows, Int(0)), 
                App.globalPut(global_total_fees, Int(0)),
                App.globalPut(global_data_package_hash, Bytes("")),
                Approve(), #then approve. 
            ]
        ),
        opt_in=Seq( 
            
            Approve(), # then approve
        ),
        no_op=Seq(
            Cond( #condtion expression
                [
                    Txn.application_args[0] == op_create_drt,
                    create_drt(),
                ],
                [
                    Txn.application_args[0] == op_update_data_package,
                    update_data_package(),
                ],
                [
                    Txn.application_args[0] == op_contributor_token,
                    create_contributor_token(),
                ],
                [
                    Txn.application_args[0] == op_new_contributor,
                    add_new_contributor(Txn.accounts[1], Txn.assets[0]),
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

            ),
            Reject(),
        ),
    )


def clear():
    return Approve()
