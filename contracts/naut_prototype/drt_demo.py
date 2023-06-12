from pyteal import *
from pyteal.ast.bytes import Bytes
from contracts.pyteal_helpers import program
from contracts.pyteal_helpers.strings import itoa
from algosdk import *

DRT_UNIT_NAME = Bytes("DRT") #need to confirm
CONTRIBUTOR_UNIT_NAME = Bytes("DRT_C") #came up with this by myself, need to confirm
DEFAULT_HASH = Bytes("base64", "y9OJ5MRLCHQj8GqbikAUKMBI7hom+SOj8dlopNdNHXI=")
DEFAULT_NOTE= Bytes("")
DEFAULT_URL= Bytes("")
NAUTILUS_EXECUTION_FEE = Int(3000000) #3 algos
NAUTILUS_EXCHANGE_ID = Int(10001)
PENDING_CONTRIBUTOR = Int(20001)



def approval():
    # Stored global variables
    global_data_package_hash = Bytes("data_package_hash")                   # The hash of the data pool
    global_enclave_address = Bytes("enclave_address")                       # The account of the nautilus wallet   
    global_append_asset_id = Bytes("global_append_asset_id")                # Asset ID of append token
    global_drt_counter= Bytes("drt_counter")                                # Counter of available DRTs
    global_drt_payment_row_average = Bytes("drt_payment_row_average")       # Computational variable for royalty fees
    global_dataset_total_rows = Bytes("dataset_total_rows")                 # Computational variable for royalty fees
    global_total_fees = Bytes("total_fees")                                 # Current total fees available
    global_init = Bytes("init_progress")                                    # Smart Contract initialisation progress variable
    global_nautilus_pool = Bytes("nautilus_pool")                           # Nautilus Fee Pool
    global_nautilus_address = Bytes("nautilus")                             # Nautilus address
    
    # Methods
    op_create_drt = Bytes("create_drt")                                 # Method call  
    op_update_drt_price = Bytes("update_drt_price")                     # Method call
    op_buy_drt = Bytes("buy_drt")                                       # Method call
    op_claim_royalty = Bytes("claim_royalty_contributor")               # Method call
    op_init_contract = Bytes("init_contract")                           # Method call
    op_drt_ownership_change = Bytes("drt_owner_change")                 # Method call
    op_drt_to_box = Bytes("drt_to_box")                                 # Method Call 
    op_con_ownership_change = Bytes("contributor_owner_change")         # Method Call
    op_de_list_drt = Bytes("de_list_drt")                               # Method Call
    op_list_drt = Bytes("list_drt")                                     # Method Call
    op_execute_drt = Bytes("execute_drt")                               # Method Call
    op_add_contributor_pending = Bytes("add_contributor_pending")       # Method Call
    op_add_contributor_approved = Bytes("add_contributor_approved")     # Method Call
    op_add_contributor_claim = Bytes("add_contributor_claim")           # Method Call
    op_claim_royalty_nautilus = Bytes("nautilus_claim")
    
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

# inner trasnction to send payment of algos from one address to another
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

# inner transaction to transfer asset-id to another account
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
        
 # function to compute the royalty fee from box storage variables
    @Subroutine(TealType.uint64)
    def compute_royalty_box(asset: Expr):
        # l_size = App.localGet(acc, local_rows_contributed)
        # l_average = App.localGet(acc, local_g_drt_payment_row_average)
        asset_id = asset
        
        l_size = ScratchVar()
        l_average = ScratchVar()
         
        g_average = App.globalGet(global_drt_payment_row_average)
        royalty_fee = ScratchVar()
        return Seq(
            contents := App.box_get(Itob(asset_id)),
            
            l_average.store(ExtractUint64(contents.value(), Int(0))),
            l_size.store(ExtractUint64(contents.value(), Int(8))),
            
            royalty_fee.store(l_size.load()*(g_average - l_average.load())),
            #App.globalPut(Bytes("royalty_fee"),royalty_fee.load()),
            #App.localPut(acc, local_royalty_fee, royalty_fee.load()),
            Return (royalty_fee.load())
        )     

# init function to initiliase the smart contract
## - Create Append DRT
## - Add creators first contribution
## - Create contributor token based off the contribution
## - add first data hash and amount of rows
    @Subroutine(TealType.none)
    def init_contract():
        append_id = ScratchVar()
        append_exist = App.globalGet(global_append_asset_id)
        
        contrib_id = ScratchVar()
        
        init_rows = Btoi(Txn.application_args[1]) #store rows of data to append
        new_hash = Txn.application_args[2] #store the new data hash
        added_account = Txn.accounts[1] #store creators account to be added as a contributor
        
        contributor_box_variables = ScratchVar()
        
        init = App.globalGet(global_init)
        
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
                    Txn.sender() == App.globalGet(global_enclave_address), #ensure transaction sender is the smart contract creator
                    append_exist == Int(0),  #ensure there is not already append DRT created
                
                    # ensure hashes are not the same
                    new_hash != App.globalGet(global_data_package_hash),
                    #ensure new hash not nothing
                    new_hash != Bytes(""),
                    #ensure added account is creators address
                    added_account == Global.creator_address(),
                    #ensure rows added is not zero
                    init_rows != Int(0),
                    
                    init == Int(0),
                )
            ),
            #opup.maximize_budget(Int(1000)),
            #create append DRT
            #name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr
            append_id.store(inner_asset_create_txn(Txn.application_args[3],Txn.application_args[4] ,Txn.application_args[5], Txn.application_args[7] , Txn.application_args[8], DEFAULT_NOTE)), #use scratch variable to store asset id of contributor token
            #store price and supply and listed for sale - int(1000000) = 1 Algo
            App.globalPut(Itob(append_id.load()),Concat(Txn.application_args[6], Txn.application_args[5])),
            #store asset id in global variable
            App.globalPut(global_append_asset_id,append_id.load()),
                
            #create contributor token
            #store smart contract ID in asset URL field
            #name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr
            contrib_id.store(inner_asset_create_txn(Bytes("Contributor"),Bytes("CONTRIB") ,Itob(Int(1)),Itob(Global.current_application_id()), DEFAULT_HASH, DEFAULT_NOTE)), #use scratch variable to store asset id of contributor token
            
            # store newly created asset ID, address, variables in box storage
            contributor_box_variables.store(Concat(Itob(contrib_id.load()),Itob(App.globalGet(global_drt_payment_row_average)), Itob(Btoi(Txn.application_args[1])), added_account)),
            Pop(App.box_create(Txn.accounts[1], Int(500))),
            App.box_replace(Txn.accounts[1],Int(0),contributor_box_variables.load()),
           
            #update global hash 
            App.globalPut(global_data_package_hash, new_hash),
            #update global row counter
            App.globalPut(global_dataset_total_rows, (init_rows + App.globalGet(global_dataset_total_rows))),
            #opup.ensure_budget(Int(2000)),
            Approve(),
        )

# CREATE DRT
# # 1. Function to initiliase the creation of a DRT
    @Subroutine(TealType.none)
    def create_drt():
        asset_id = ScratchVar()
        exchangeRate_supply=ScratchVar()
        
        init = App.globalGet(global_init)
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

                    #ensure there is atleast 2 arguments
                    Txn.application_args.length() == Int(6), # instruction, name, amount, url of binary, hash of binary, note, exchange price
                    
                    init != Int(0),
                )
            ),
            #create drt and record asset id
            #name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr
            asset_id.store(inner_asset_create_txn(Txn.application_args[1],DRT_UNIT_NAME ,Txn.application_args[2], Txn.application_args[3] ,Txn.application_args[4], Txn.note())),
            #store DRT price in contract alongside asset id in globals
            exchangeRate_supply.store(Concat(Txn.application_args[5],Txn.application_args[2])),
            #incremement counter
            App.globalPut(global_drt_counter, App.globalGet(global_drt_counter) + Int(1)),
            
            App.globalPut(Itob(asset_id.load()), exchangeRate_supply.load()),
            
            Approve()
        )

# # 2. Function to store DRT in box storage and register the smart contract as current owner
    @Subroutine(TealType.none)
    def drt_to_box(asset_id: Expr):
        
        drt_variables = App.globalGet(Itob(asset_id))
        supply = ExtractUint64(drt_variables,Int(8))
        drt_exists_in_account = AssetHolding.balance(Global.current_application_address(), asset_id)
        drt_box_name = Concat(Itob(asset_id),Global.current_application_address())
        
        
        drt_variables_listed = Concat(drt_variables, Itob(NAUTILUS_EXCHANGE_ID))
        
        init = App.globalGet(global_init)
        return Seq(     
        drt_exists_in_account,
        #basic sanity checks
            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            program.check_rekey_zero(1),
            Assert(
                And(
                    #check the sender is equal to the account who sent the append drt and wants to be a contributor
                    Txn.sender() == Global.creator_address(),
                    #ensure drt was properly created
                    drt_exists_in_account.value() == supply,

                    init != Int(0),
                )
            ),
            Pop(App.box_create(drt_box_name, Int(1000))),
            App.box_replace(drt_box_name,Int(0), drt_variables_listed),
            App.globalDel(Itob(asset_id)),
            
            Approve()
        )

# Function to update the price of a DRT. 
    @Subroutine(TealType.none)
    def update_drt_price():
        btoi_rate = Btoi(Txn.application_args[1])
        drt_box_name = Concat(Itob(Txn.assets[0]),Global.current_application_address())
        
        init = App.globalGet(global_init)
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
                    #ensure price is at least 1 Algo = 1000000 micro algos
                    btoi_rate >= Int(1000000),
                    init != Int(0),
                )
            ),
            #change current exchange rate 
            App.box_replace(drt_box_name, Int(0), Itob(btoi_rate)),

            Approve(),
        )

# Function to delist a drt
    @Subroutine(TealType.none)
    def de_list_drt():
        drt_box_name = Concat(Itob(Txn.assets[0]),Global.current_application_address())
        
        init = App.globalGet(global_init)
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
                    init != Int(0),
                )
            ),
            #remove current drt listed exchange (Nautilus for MVP)
            App.box_replace(drt_box_name, Int(16), Itob(Int(0))),

            Approve(),
        )

# Function to delist a drt
    @Subroutine(TealType.none)
    def list_drt():
        drt_box_name = Concat(Itob(Txn.assets[0]),Global.current_application_address())
        
        init = App.globalGet(global_init)
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
                    init != Int(0),
                )
            ),
            #re list drt for sale 
            App.box_replace(drt_box_name, Int(16), Itob(NAUTILUS_EXCHANGE_ID)),

            Approve(),
        )

# Function to buy a created DRT, incorporates the inner_asset_create_txn function
    @Subroutine(TealType.none)
    def buy_drt():
        assetToBuy = Gtxn[0].assets[0]
        paymentAmount = Gtxn[1].amount()
        nautilus_fee = Div(paymentAmount*Int(5),Int(100))
        gn_amount = paymentAmount - nautilus_fee
        pool_fee = ScratchVar()
        buyerOptIn = AssetHolding.balance(Gtxn[0].sender(), assetToBuy)
        g_n = compute_global_drt_payment_row_average(App.globalGet(global_drt_payment_row_average), App.globalGet(global_dataset_total_rows) , gn_amount)
        
        drt_box_name = Concat(Itob(assetToBuy),Global.current_application_address())
        supply = ScratchVar()
        exchange_rate = ScratchVar()
        new_supply = ScratchVar()
        listed_for_sale = ScratchVar()
        
        #new owner box details
        new_owner_box_name = Concat(Itob(assetToBuy),Gtxn[0].sender())
        new_owner_box_variables = ScratchVar()
        
        
        init = App.globalGet(global_init)
        return Seq(
            #gather box variables
            box_contents := App.box_get(drt_box_name), 
            exchange_rate.store(ExtractUint64(box_contents.value(),Int(0))),
            supply.store(ExtractUint64(box_contents.value(),Int(8))),
            listed_for_sale.store(ExtractUint64(box_contents.value(),Int(16))),

            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            defaultTransactionChecks(Int(1)), # Perform default transaction checks
            buyerOptIn,
    
            #basic sanity checks
            program.check_self(
                group_size=Int(2), #ensure 2 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    Gtxn[1].type_enum() == TxnType.Payment,
                    box_contents.hasValue(), # Check drt exists
                    paymentAmount == (exchange_rate.load()*Btoi(Gtxn[0].application_args[1])), # Check amount to be paid is correct (exchange rate * how many)
                    Global.current_application_address() == Gtxn[1].receiver(), # check the reciever of the payment (2nd transaction) is the app
                    buyerOptIn.hasValue(), #ensure the user has opted in to asset
                    supply.load() >= Btoi(Gtxn[0].application_args[1]), #ensure there is enough supply
                    Gtxn[0].application_args.length() == Int(2),   #ensure there is atleast 2 arguments
                    Gtxn[0].sender() == Gtxn[1].sender(),

                    listed_for_sale.load() == NAUTILUS_EXCHANGE_ID,
                    
                    init == Int(1),
                )
            ),
            #store it 
            App.globalPut(global_drt_payment_row_average, g_n),
            pool_fee.store(paymentAmount - nautilus_fee),
            App.globalPut(global_total_fees, (pool_fee.load() + App.globalGet(global_total_fees))),
            App.globalPut(global_nautilus_pool, (nautilus_fee + App.globalGet(global_nautilus_pool))),
            
            #change current supply of previous owner
            new_supply.store(supply.load() - Btoi(Gtxn[0].application_args[1])),
            #update existing supply of previous owner
            App.box_replace(drt_box_name, Int(8), Itob(new_supply.load())),                
                             
            #then register new ownership in box storage, only supply is stored
            new_owner_box_variables.store(Btoi(Gtxn[0].application_args[1])),
            App.box_put(new_owner_box_name, Itob(new_owner_box_variables.load())),
            
            # if the above checks out, transfer asset
            inner_asset_transfer_txn(assetToBuy, Btoi(Gtxn[0].application_args[1]), Gtxn[0].sender()),
            
            Approve(),
        )

# JOIN DATA POOL
# # 1. Function to add a data contributor temporarily pending approval from the enclave
#       (you can only add one set of data at a time)
    @Subroutine(TealType.none)
    def add_contributor_pending(): 
        nautilus_fee = Gtxn[1].amount()
        init = App.globalGet(global_init)
        
        return Seq(
             #basic sanity checks
            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            defaultTransactionChecks(Int(1)), # Perform default transaction checks
            program.check_rekey_zero(1),
       
            Assert(
                And(
                    #check group size
                    Global.group_size() == Int(3),
                    
                    ## transaction 1 checks
                    Txn.sender() == Gtxn[0].sender(), #check the sender of the 3rd transaction is the sender of the append asset
                    Gtxn[0].type_enum() == TxnType.AssetTransfer, #check the first transaction was an asset transfer
                    Global.current_application_address() == Gtxn[0].asset_receiver(), # check the reciever of the asset transfer is the smart cotnract
                    Gtxn[0].xfer_asset() == App.globalGet(global_append_asset_id), #check the asset is the append drt
                    Gtxn[0].asset_amount() == Int(1), #ensure append drt asset amount is 1 , i.e can only append 1 set of data at a time
                    
                    # ##transaction 2 checks
                    Gtxn[1].type_enum() == TxnType.Payment, #check second transaction was a payment
                    Gtxn[1].amount() == NAUTILUS_EXECUTION_FEE, #check payment was equal to the execution fee
                    Gtxn[1].receiver() == Global.current_application_address(), #check the reciever is the smart contract
                    Gtxn[1].sender() == Txn.sender(), #check the sender of the 3rd transaction is the sender of the payment
                    
                    init != Int(0),
                )
            ),
            # add nauitlus fee to the nautilus pool global
            App.globalPut(global_nautilus_pool, (nautilus_fee + App.globalGet(global_nautilus_pool))),
            #store user as pending contributor
            Pop(App.box_create(Txn.sender(), Int(500))),
            App.box_replace(Txn.sender(),Int(0), Itob(PENDING_CONTRIBUTOR)),
            
        Approve(),
        )

# # 2. Function to approve the pending contributors contribution 
    @Subroutine(TealType.none)
    def add_contributor_approved():
        contrib_id = ScratchVar()  
        # store rows of data to append
        new_rows = Btoi(Txn.application_args[1])
        # store the new data hash
        new_hash = Txn.application_args[2]
        # store approval
        approved = Btoi(Txn.application_args[3])
        
        contributor_box_variables = ScratchVar()
        
        init = App.globalGet(global_init)
        return Seq(
             #basic sanity checks
            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            program.check_rekey_zero(1),
            contributorIsPending := App.box_get(Txn.accounts[1]),
            Assert(
                And(
                    # ensure added account is a pending contributor
                    ExtractUint64(contributorIsPending.value(), Int(0)) == PENDING_CONTRIBUTOR, 
                    #check the sender of this transaction is the enclaves accounts
                    Txn.sender() == App.globalGet(global_enclave_address),
                    #ensure hashes are not the same
                    new_hash != App.globalGet(global_data_package_hash),
                    # #ensure new hash not nothing
                    new_hash != Bytes(""),
                    # #ensure approved
                    approved == Int(1),
                    
                    init != Int(0),
                )
            ),
            #create contributor token
            #store smart contract ID in asset URL field
            #name: Expr, unit_name: Expr, amount: Expr, asset_url: Expr, binHash: Expr, note: Expr
            #use scratch variable to store asset id of contributor token
            contrib_id.store(inner_asset_create_txn(Bytes("Contributor"),Bytes("CONTRIB") ,Itob(Int(1)),itoa(Global.current_application_id()), DEFAULT_HASH, DEFAULT_NOTE)), 
         
            # store newly created asset ID, address, variables in box storage
            contributor_box_variables.store(Concat(Itob(contrib_id.load()),Itob(App.globalGet(global_drt_payment_row_average)), Itob(new_rows), Txn.accounts[1])),
            App.box_replace(Txn.accounts[1],Int(0),contributor_box_variables.load()),
            
            #update global hash 
            App.globalPut(global_data_package_hash, new_hash),
            #update global row counter
            App.globalPut(global_dataset_total_rows, (new_rows + App.globalGet(global_dataset_total_rows))),

            Approve(),
        )
 
# # 3. Function to claim contributor token toke after being approved by enclave
# # This function also used in last step of the setup of the smart contract after init_contract()
    @Subroutine(TealType.none)
    def add_contributor_claim():
        #store senders asset holdings of contributor token to check for opting in 
        contributorOptIn = AssetHolding.balance(Txn.sender(), Txn.assets[0])
        box_contrib_assetID = ScratchVar()
        box_contrib_variables = ScratchVar()
        init = App.globalGet(global_init)
        return Seq(     
        #basic sanity checks
            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            program.check_rekey_zero(1),
            contributorOptIn,
            # this gets the content of the box storage and by default ensures there is box storage information for the sender
            box_contents := App.box_get(Txn.sender()), 
            box_contrib_assetID.store(ExtractUint64(box_contents.value(), Int(0))),
            box_contrib_variables.store(Extract(box_contents.value(),Int(8), Int(48))),
            Assert(
                And(
                    #check sender has opted in to contributor token
                    contributorOptIn.hasValue(),
                    #ensure asset references is the new_contributor_asset
                    Txn.assets[0] == box_contrib_assetID.load(),
                ),
             ),    
            #store asset in box storage with variables
            #by referencing the correct box name in the box array of the transaction and by only using
            # the global variable holding the asset ID, we inherently check that the correct
            # box reference is being used as the name for the box storage
            
            Pop(App.box_create(Itob(box_contrib_assetID.load()), Int(500))),
            App.box_replace(Itob(box_contrib_assetID.load()),Int(0),box_contrib_variables.load()),            
            
            #delete old pending contributor box
            Pop(App.box_delete(Txn.sender())),
            
            #transfer asset
            inner_asset_transfer_txn(Txn.assets[0], Int(1), Txn.sender()),
            
            #end initialisation if its the first contribution
            If(init == Int(0))
            .Then(
                App.globalPut(global_init, Int(1)),
                Pop(App.box_create(Concat(Itob(Txn.assets[1]),Global.current_application_address()), Int(1000))),
                
                App.box_replace(Concat(Itob(Txn.assets[1]),Global.current_application_address()), Int(0) ,Concat(App.globalGet(Itob(Txn.assets[1])), Itob(NAUTILUS_EXCHANGE_ID))),
                App.globalDel(Itob(Txn.assets[1])),
                Approve(),
            ).Else(
                Approve(),
            )
            # Approve(),
        )
 
# Function to claim royalty fee from the ownership of a contributor token
    @Subroutine(TealType.none)
    def claim_royalty_contributor(account: Expr, asset_id: Expr):
        accountAssetBalance = AssetHolding.balance(account, asset_id)
        royalty_fee = compute_royalty_box(asset_id)
        fees_change = ScratchVar()
        registered_owner = ScratchVar()
        
        init = App.globalGet(global_init)
        return Seq(
            accountAssetBalance,
            registered_owner.store(App.box_extract(Itob(asset_id), Int(16), Int(32))),
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), #ensure 1 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #check that the recevier of the token has opted in and has a balance of 1 contributor token
                    accountAssetBalance.hasValue(),
                    accountAssetBalance.value() == Int(1),
                    #ensure the correct amount of arguments
                    Txn.application_args.length() == Int(1), 
                    #ensure royalty fee is greater than zero
                    royalty_fee > Int(0),
                    #ensure royalty fee is less than or equal to the total
                    App.globalGet(global_total_fees) >= royalty_fee,
                    #check the registered owner is the one who is claiming the fees
                    registered_owner.load() == account,
                    
                    init != Int(0),
                )
            ),
            #App.globalPut(Bytes("registered_owner"), registered_owner.load()), works
            fees_change.store(royalty_fee),
            #transfer the amount
            inner_sendPayment(Txn.sender(), royalty_fee),
            #reset the box variables for contributor token ( as if the user has just conrtibuted )
            App.box_replace(Itob(asset_id), Int(0), Itob(App.globalGet(global_drt_payment_row_average))),
            #minus fee payout from total fees collected
            App.globalPut(global_total_fees, (App.globalGet(global_total_fees) - fees_change.load())),
    
            Approve(),
        ) 
   
   
   # Function to claim royalty fee from the ownership of a contributor token
    @Subroutine(TealType.none)
    def claim_royalty_nautilus():
        nautilus_payout = App.globalGet(global_nautilus_pool)
        
        init = App.globalGet(global_init)
        return Seq(
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(1), #ensure 1 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    #ensure the correct amount of arguments
                    Txn.application_args.length() == Int(1), 
                    #ensure nautilus payout is greater than zero
                    nautilus_payout > Int(0),
                    #ensure royalty fee is less than or equal to the total
                    App.globalGet(global_total_fees) >= nautilus_payout,
                    # check the sender is the stored nautilus account
                    Txn.sender() == App.globalGet(global_nautilus_address),
                    
                    init != Int(0),
                )
            ),
            #transfer the amount
            inner_sendPayment(Txn.sender(), nautilus_payout),
            #minus fee payout from total fees collected
            App.globalPut(global_total_fees, (App.globalGet(global_total_fees) - nautilus_payout)),
            #minus the fee payout from nautilus payout
            App.globalPut(global_nautilus_pool, (App.globalGet(global_nautilus_pool)- nautilus_payout)),

    
            Approve(),
        ) 
   
# Function to change the registered ownership of the DRT stored in the box storage
    @Subroutine(TealType.none)
    def drt_ownership_change():
        #transaction 1 transfer asset values
        assetTraded = Gtxn[0].xfer_asset() #asset id
        assetReceiver = Gtxn[0].asset_receiver() #account_encalve
        assetSender = Gtxn[0].sender() #account_2
        asset_creator = AssetParam.creator(Gtxn[0].xfer_asset()) #account_app
        assetAmountBought = Gtxn[0].asset_amount() #asset amount
        
        #transaction 2 payment values
        paymentAmount = Gtxn[1].amount() #traded amount
        paymentReceiver = Gtxn[1].receiver() # account_2
        paymentSender = Gtxn[1].sender() #account_enclave
        
        #trnasction 3 fees values 
        ownershipFees = Gtxn[2].amount() # 5% of paymentAMount
        feesReceiver = Gtxn[2].receiver() # Account_app
        feesSender = Gtxn[2].sender() #account_enclave
        
        #transaction 4 drt ownership change values
        newOwner = Gtxn[3].sender() #account_enclave
        asset_id = Gtxn[3].assets[0] # asset_id

        current_drt_box_name = Concat(Itob(assetTraded), Gtxn[0].sender()) #assetid + account_2
        current_owner_supply = ScratchVar()
        current_owner_new_supply = ScratchVar()
        new_owner_box_name = Concat(Itob(assetTraded), Gtxn[3].sender())

        
        init = App.globalGet(global_init)
        return Seq(
            #this function checks that the current DRT exists and that the sender of the DRT is the owner
            current_drt_variables := App.box_get(current_drt_box_name),
            current_owner_supply.store(ExtractUint64(current_drt_variables.value(),Int(0))),
            asset_creator,
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_self(
                group_size=Int(4), #ensure 1 transaction
                group_index=Int(0),
            ),
            program.check_rekey_zero(1),
            Assert(
                And(
                    # check assett traded is the same asset to update
                    assetTraded == asset_id,
                    # check new owner is equal to asset receiver
                    newOwner == assetReceiver,
                    # check the asset sender is equal to the payment receiver
                    assetSender == paymentReceiver,
                    #chek the payment sender is equal to the asset receiver
                    paymentSender == assetReceiver,
                    # fees sender is equal to the asset receiver
                    feesSender == newOwner,
                    # fees receiver is equal to the smart contract global address
                    feesReceiver == Global.current_application_address(),
                    #check the asset being sent's creator is the application address
                    asset_creator.value() == Global.current_application_address(),
                    # check that they are paying 5% of traded value to smart contract
                    ownershipFees == Div(paymentAmount*Int(5),Int(100)),
   
                    init != Int(0),
                )
            ),
            
            #change current supply of previous owner
            current_owner_new_supply.store(current_owner_supply.load() - assetAmountBought),
            #update existing supply of previous owner
            App.box_replace(current_drt_box_name, Int(0), Itob(current_owner_new_supply.load())),                
                             
            #then register new ownership in box storage
            App.box_put(new_owner_box_name, Itob(assetAmountBought)),
            
            # add fee payout from total fees collected
            App.globalPut(global_total_fees, (App.globalGet(global_total_fees) + ownershipFees)),
    
            Approve(),
        )  
     
# Function to change ownership of contributor in secondary market
    @Subroutine(TealType.none)
    def contributor_ownership_change():
        #transaction 1 transfer asset values
        contributorTraded = Gtxn[0].xfer_asset() #asset id
        contributorReceiver = Gtxn[0].asset_receiver() #account_encalve
        contributorSender = Gtxn[0].sender() #account_2
        contributor_creator = AssetParam.creator(Gtxn[0].xfer_asset()) #account_app
        contributorAmountBought = Gtxn[0].asset_amount() #asset amount
        
        #transaction 2 payment values
        paymentAmount = Gtxn[1].amount() #traded amount
        paymentReceiver = Gtxn[1].receiver() # account_2
        paymentSender = Gtxn[1].sender() #account_enclave
        
        #trnasction 3 fees values 
        ownershipFees = Gtxn[2].amount() # 5% of paymentAMount
        feesReceiver = Gtxn[2].receiver() # Account_app
        feesSender = Gtxn[2].sender() #account_enclave
        
        #transaction 4 drt ownership change values
        newContributor = Gtxn[3].sender() #account_enclave
        contributor_id = Gtxn[3].assets[0] # asset_id

        contributor_box_name = Itob(contributorTraded) #assetid + account_2
        contributor_owner = ScratchVar()
        init = App.globalGet(global_init)
        return Seq(
            #this function checks that the current contributor token exists
            contributor_owner.store(App.box_extract(contributor_box_name, Int(16), Int(32))),
            contributor_creator,
            #basic santiy checks
            defaultTransactionChecks(Int(0)),
            program.check_rekey_zero(1),
            Assert(
                And(
                    # check contributort traded is the same contributor to update
                    contributorTraded == contributor_id,
                    # check new owner is equal to contributor receiver
                    newContributor == contributorReceiver,
                    # check the contributor sender is equal to the payment receiver
                    contributorSender == paymentReceiver,
                    # #chek the payment sender is equal to the contributor receiver
                    paymentSender == contributorReceiver,
                    # # fees sender is equal to the contributor receiver
                    feesSender == newContributor,
                    # # fees receiver is equal to the smart contract global address
                    feesReceiver == Global.current_application_address(),
                    #check the contributor being sent's creator is the application address
                    contributor_creator.value() == Global.current_application_address(),
                    # check that they are paying 5% of traded value to smart contract
                    ownershipFees == Div(paymentAmount*Int(5),Int(100)),
                    
                    #current contributor owner equals to asset sender
                    contributor_owner.load() == contributorSender,
   
                    init != Int(0),
                )
            ),
            
            App.globalPut(Bytes("contributor_ID"),  Gtxn[0].xfer_asset()),
        
            #update existing contributor owner with new owner
            App.box_replace(contributor_box_name, Int(16), newContributor),    
            
            App.globalPut(Bytes("new_contributor"), App.box_extract(contributor_box_name, Int(16), Int(32))),    
            
            # add fee payout from total fees collected
            App.globalPut(global_total_fees, (App.globalGet(global_total_fees) + ownershipFees)),
    
            Approve(),
        )  

# Function to execute a DRT 
    @Subroutine(TealType.none)
    def execute_drt():
        #transaction 1 transfer asset values
        assetTraded = Gtxn[0].xfer_asset() #asset id
        assetReceiver = Gtxn[0].asset_receiver() #account_encalve
        assetSender = Gtxn[0].sender() #account_2
        asset_creator = AssetParam.creator(Gtxn[0].xfer_asset()) #account_app
        assetAmount = Gtxn[0].asset_amount() #asset amount
        
        #transaction 2 execution fee payment values
        paymentAmount = Gtxn[1].amount() #traded amount
        paymentReceiver = Gtxn[1].receiver() # account_2
        paymentSender = Gtxn[1].sender() #account_enclave
        
        
        #transaction 3 - this transaction
        registered_owner_box_name = Concat(Itob(assetTraded), Gtxn[0].sender()) #assetid + account_2
        # if App.box_get function runs, therefore the owner is registered
        registered_owner_supply = ScratchVar()
        new_registered_supply = ScratchVar()
    
        # get app ownership variables 
        app_box_name = Concat(Itob(assetTraded), Global.current_application_address())
        app_supply = ScratchVar()
        new_app_supply = ScratchVar()
        
        init = App.globalGet(global_init)
        
        return Seq(
             #basic sanity checks
            defaultTransactionChecks(Int(0)),  # Perform default transaction checks
            defaultTransactionChecks(Int(1)), # Perform default transaction checks
            program.check_rekey_zero(1),
            
            registered_owner_variables := App.box_get(registered_owner_box_name),
            registered_owner_supply.store(ExtractUint64(registered_owner_variables.value(),Int(0))),
            
            app_variables := App.box_get(app_box_name),
            app_supply.store(ExtractUint64(app_variables.value(),Int(8))),
            asset_creator,    
                
            Assert(
                And(
                    #check group size
                    Global.group_size() == Int(3),
                    # ensure receiver of payment and asset, creator of asset is the app
                    assetReceiver == Global.current_application_address(),
                    paymentReceiver == Global.current_application_address(),
                    assetSender == paymentSender,
                    asset_creator.value() == Global.current_application_address(),
                    assetAmount == Int(1),
                    
                    registered_owner_supply.load() >= Int(1),
                    app_supply.load() >= Int(1),
                    
                    paymentAmount == NAUTILUS_EXECUTION_FEE,
                    
                    init != Int(0),
                )
            ),
            # decrease current owners account by 1
            new_registered_supply.store(registered_owner_supply.load() - assetAmount),
            App.box_replace(registered_owner_box_name, Int(0) , Itob(new_registered_supply.load())),
            
            #increase supply back to current applications box
            new_app_supply.store(app_supply.load() + assetAmount),
            App.box_replace(app_box_name, Int(8) , Itob(new_app_supply.load())),

            
            # add fee paypout to nautilus pool fees
            App.globalPut(global_nautilus_pool, (paymentAmount + App.globalGet(global_nautilus_pool))),
            Approve(),
            
        )
   
       
# Check the transaction type and execute the corresponding code
# 1. If smart contract does not exist it will trigger the initialisation sequence contained in the "init" variable.
# 2. An Optin transaction is simply approved.
# 3. If the transaction type is a NoOp transaction, i.e. an Application Call, then it checks the first argument of the call which must be equal to one of the method call variables:
# "op_create_drt","op_update_drt_price", "op_buy_drt", "claim_royalty_contributor","op_init_contract"
# "op_drt_ownership_change",  " op_drt_to_box" "op_con_ownership_change", "op_de_list_drt", "op_list_drt", "op_execute_drt", "op_add_contributor_pending"
# "op_add_contributor_approved", "op_add_contributor_claim"

    return program.event(
        init=Seq( 
            [
                Assert(
                    # Check if it's an application call
                    Txn.type_enum() == TxnType.ApplicationCall,
                    # Check the arguments length
                    Txn.application_args.length() == Int(0),
                    # Check the accounts length 
                    Txn.accounts.length() == Int(2),
                    ),                  
                # Store nautilus company wallet address 
                App.globalPut(global_enclave_address, Txn.accounts[1]),
                App.globalPut(global_nautilus_address, Txn.accounts[2]),
                # Initialise global variables
                App.globalPut(global_drt_counter, Int(0)),
                App.globalPut(global_drt_payment_row_average, Int(0)),
                App.globalPut(global_dataset_total_rows, Int(0)), 
                App.globalPut(global_total_fees, Int(0)),
                App.globalPut(global_data_package_hash, Bytes("")),
                App.globalPut(global_nautilus_pool, Int(0)),
                #init variable
                App.globalPut(global_init, Int(0)),
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
                    Txn.application_args[0] == op_update_drt_price,
                    update_drt_price(),
                ],
                [
                    Txn.application_args[0] == op_buy_drt,
                    buy_drt(),
                ],
                [
                    Txn.application_args[0] == op_claim_royalty,
                    claim_royalty_contributor(Txn.sender(), Txn.assets[0])
                ],
                [
                    Txn.application_args[0] == op_init_contract,
                    init_contract()
                ],
                 [
                    Txn.application_args[0] == op_drt_ownership_change,
                    drt_ownership_change()
                ],
                [
                    Txn.application_args[0] == op_drt_to_box,
                    drt_to_box(Txn.assets[0])
                ],
                [
                    Txn.application_args[0] == op_con_ownership_change,
                    contributor_ownership_change()
                ],
                [
                    Txn.application_args[0] == op_de_list_drt,
                    de_list_drt()
                ],
                [
                    Txn.application_args[0] == op_list_drt,
                    list_drt()
                ],
                [
                    Txn.application_args[0] == op_execute_drt,
                    execute_drt()
                ],
                [
                    Txn.application_args[0] == op_add_contributor_pending,
                    add_contributor_pending()
                ],
                [
                    Txn.application_args[0] == op_add_contributor_approved,
                    add_contributor_approved()
                ],
                [
                    Txn.application_args[0] == op_add_contributor_claim,
                    add_contributor_claim()
                ],
                [
                    Txn.application_args[0] == op_claim_royalty_nautilus,
                    claim_royalty_nautilus()
                ]
                
            ),
            Reject(),
        ),
    )


def clear():
    return Approve()