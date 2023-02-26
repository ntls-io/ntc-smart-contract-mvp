from typing import Tuple, List
import json
from algosdk.encoding import decode_address, encode_address,base64
from algosdk.v2client.algod import AlgodClient
from algosdk import transaction
from algosdk.logic import get_application_address
from algosdk import account, encoding
from pyteal import compileTeal, Mode
from contracts.naut_prototype.drt_demo import approval,clear
from contracts.pyteal_helpers.strings import itoa
from base64 import b64decode, encode
from helpers.resources import getTemporaryAccount, optInToAsset, createDummyAsset
from transaction_constructions.operation_txns import createDRT_txn, claimDRT_txn, delistDRT_txn, listDRT_txn, buyDRT_txn, appendRedeemDRT_txn, claimContributor_txn, executeDRT_txn


from helpers.account import Account
from helpers.util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
    hasOptedIn,
    getBalances,
)
from python_sdk.helpers.util import PendingTxnResponse


def createDRT_method(
    client: AlgodClient,
    appID: int,
    sender: Account,
    drtName: str,
    drtPrice: int,
    drtBinaryUrl: str,
    drtBinaryHash: str,
    drtSupply: int,
    drtNote: str,   
):
    """Create DRT.

    This operation creates a DRT (Digital Rights Token). 

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        sender: The account of the sender of the create DRT transaction (creator account).
        drtName: name of the DRT
        drtPrice: price of the DRT in microAlgos
        drtBinaryUrl: URL of the binary code that the DRT represents
        drtBinaryHash: hash of the binary code that the DRT represents
        drtSupply: Supply total of the DRT to create
        drtNote: note to be stored on the creation of the DRT transaction
        
    """

    createDRTTxn = createDRT_txn(
       client=client,
       appID=appID,
       sender=sender,
       drtName=drtName,
       drtPrice=drtPrice,
       drtBinaryUrl=drtBinaryUrl,
       drtBinaryHash=drtBinaryHash,
       drtSupply=drtSupply,
       drtNote=drtNote
    )

    ## this will need to replaced by the signing enclave function to sign the transaction
    signedcreateDRTTxn = createDRTTxn.sign(sender.getPrivateKey())
    
    
    txid = client.send_transaction(signedcreateDRTTxn)
   
    try:
        response = waitForTransaction(client, txid)  
        id_DRT = response.innerTxns[0]['asset-index']
        print("DRT succesfully created.")
        return id_DRT
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err

def claimDRT_method(
    client: AlgodClient,
    appID: int,
    sender: Account,
    drtID: int,
):
    """Claim DRT.

    This operation claims a DRT after it has been created and stores the DRT in box storage

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        sender: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

        
    """
    claimDRTTxn = claimDRT_txn(
        client=client,
        appID=appID,
        sender=sender,
        drtID=drtID
    )
    
    ## this will need to replaced by the signing enclave function to sign the transaction
    signedcreateDRTTxn = claimDRTTxn.sign(sender.getPrivateKey())
    
    txid = client.send_transaction(signedcreateDRTTxn)
   
    try:
        response = waitForTransaction(client, txid)
        print("DRT succesfully claimed.")
        return response.txn
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err

def createAndClaimDRT_method(
    client: AlgodClient,
    appID: int,
    creator: Account,
    drtName: str,
    drtPrice: int,
    drtBinaryUrl: str,
    drtBinaryHash: str,
    drtSupply: int,
    drtNote: str,   
):
    """Create and claim DRT.

    This operation combines the create and claim DRT method functions. 
    Args:
        client: An algod client.
        appID: The app ID of the auction.
        sender: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

        
    """
    
    appAddr = get_application_address(appID)
    
    try:
        id_DRT = createDRT_method(
            client=client,
            sender=creator, 
            appID=appID,
            drtName=drtName,
            drtPrice=drtPrice,
            drtBinaryUrl=drtBinaryUrl,
            drtBinaryHash=drtBinaryHash,
            drtSupply=drtSupply,
            drtNote=drtNote,
            )
    except Exception as err:
        print(err)
        return err
    
    try:
        claimDRT_method(
            client=client,
            sender=creator,
            appID=appID,
            drtID=id_DRT,
        )
    except Exception as err:
        print(err)
        return err
    
    drtOwnership = client.account_asset_info(appAddr, id_DRT)
    assert drtOwnership["asset-holding"]["amount"] == drtSupply    
    assert drtOwnership["asset-holding"]["asset-id"] == id_DRT     

    return id_DRT, drtSupply, drtPrice

def delistDRT_method(
    client: AlgodClient,
    appID: int,
    creator: Account,
    drtID: int,
):
    """delist DRT.

    This operation delists a drt

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        creator: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

        
    """

    delistDRTTxn = delistDRT_txn(
        client=client,
        appID=appID,
        creator=creator,
        drtID=drtID
    )
 
    ## this will need to replaced by the signing enclave function to sign the transaction
    signedcreateDRTTxn = delistDRTTxn.sign(creator.getPrivateKey())
    
    txid = client.send_transaction(signedcreateDRTTxn)
   
    try:
        response = waitForTransaction(client, txid)
        
        print("DRT succesfully delisted.")
        return response.txn
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err

def listDRT_method(
    client: AlgodClient,
    appID: int,
    creator: Account,
    drtID: int,
):
    """list DRT.

    This operation re-lists a drt for sale.

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        creator: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

    """
    
    listDRTTxn = listDRT_txn(
        client=client,
        appID=appID,
        creator=creator,
        drtID=drtID
    )
    
    ## this will need to replaced by the signing enclave function to sign the transaction
    signedcreateDRTTxn = listDRTTxn.sign(creator.getPrivateKey())
    
    txid = client.send_transaction(signedcreateDRTTxn)
   
    try:
        response = waitForTransaction(client, txid)

        print("DRT succesfully re-listed.")
        return response.txn
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err


def redeemAppendDRT_method(
    client: AlgodClient,
    appID: int,
    redeemer: Account,
    enclave: Account,
    appendID: int,
    assetAmount: int,
    rowsContributed: int,
    newHash: str,
    enclaveApproval: int,
):
    """Redeem append DRT.

    This method issues the redeem append DRT transaction to the blockchain. 

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        redeemer: The account of the user redeeming the append DRT
        enclave: The account of the enclave validating the incoming data
        appendID: The asset ID of the append DRT
        assetAmount: The amount of assets of the append DRT being redeemed, always 1
        rowsContributed: The amount of rows of data contributed to the pool
        newHash: The new hash of the data pool including the incoming data provided by the enclave
        enclaveApproval: The payment amount sent to the smart contract to buy the DRT(s)
        
    """
    assetTransferTxn, addContributorTxn = appendRedeemDRT_txn(
        client=client,
        appID=appID,
        redeemer=redeemer,
        enclave=enclave,
        appendID=appendID,
        assetAmount=assetAmount,
        rowsContributed=rowsContributed,
        newHash=newHash,
        enclaveApproval=enclaveApproval
   
    )
    
    # # sign transactions inside enclave
    signedassetTransferTxn = assetTransferTxn.sign(redeemer.getPrivateKey())
    signedaddContributorTxn = addContributorTxn.sign(enclave.getPrivateKey())

    # # send them over network (note that the accounts need to be funded for this to work)
    txid = client.send_transactions([signedassetTransferTxn , signedaddContributorTxn])
    
    try:
        response = waitForTransaction(client, txid)
        app_state = getAppGlobalState(client=client, appID=appID)
        assert redeemer.getAddress() == encode_address(app_state[b'new_contributor_address'])
        print("Append DRT successfully redeemed and data contributor token created.")
        
        return response, app_state[b'new_contributor_asset']
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err

def claimContributor_method(
    client: AlgodClient,
    appID: int,
    contributorAccount: Account,
    contributorAssetID: int,
):
    """Claim contributor token.

    Args:
        client: An algod client.
        contributorAccount: The account that contributor data and needs to claim their token
        contributorAssetID: The asset ID of the contributor token.

    Returns:
        success or err.
    """
    appAddr = get_application_address(appID)
    #check user has opted in to asset
    optedIn = hasOptedIn(client=client, account=contributorAccount.getAddress() ,assetID=contributorAssetID)
    if optedIn == None:
        optInToAsset(client=client,assetID=contributorAssetID, account=contributorAccount)
    
      
    claimTxn = claimContributor_txn(
        client=client,
        appID=appID,
        contributorAccount=contributorAccount,
        contributorAssetID=contributorAssetID
    )

    signedTxn = claimTxn.sign(contributorAccount.getPrivateKey())

    txid = client.send_transaction(signedTxn)

    try:
        response = waitForTransaction(client, txid)  
        print("Contributor claimed asset, ", contributorAssetID)
        
        assert response.innerTxns[0]["txn"]["txn"]["snd"] == appAddr
        assert response.innerTxns[0]["txn"]["txn"]["arcv"] == contributorAccount.getAddress()
        assert response.innerTxns[0]["txn"]["txn"]["xaid"] == contributorAssetID
        return response
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err

def joinDataPool_method(
    client: AlgodClient,
    appID: int,
    redeemer: Account,
    enclave: Account,
    appendID: int,
    assetAmount: int,
    rowsContributed: int,
    newHash: str,
    enclaveApproval: int,   
):
    """Join Data Pool Method.

    This operation combines the redeem Append DRT and claim contributor DRT method functions. 
    Args:
        client: An algod client.
        appID: The app ID of the auction.
        redeemer: The account of the user redeeming the append DRT
        enclave: The account of the enclave validating the incoming data
        appendID: The asset ID of the append DRT
        assetAmount: The amount of assets of the append DRT being redeemed, always 1
        rowsContributed: The amount of rows of data contributed to the pool
        newHash: The new hash of the data pool including the incoming data provided by the enclave
        enclaveApproval: The payment amount sent to the smart contract to buy the DRT(s)

    """
    
    appAddr = get_application_address(appID)
    
    try:
        response, contributorAssetID = redeemAppendDRT_method(
            client=client,
            appID=appID,
            redeemer=redeemer,
            enclave=enclave,
            appendID=appendID,
            assetAmount=assetAmount,
            rowsContributed=rowsContributed,
            newHash=newHash,
            enclaveApproval=enclaveApproval
            )
    except Exception as err:
        print(err)
        return err
    
    try:
        claimContributor_method(
            client=client,
            contributorAccount=redeemer,
            appID=appID,
            contributorAssetID=contributorAssetID
        )
    except Exception as err:
        print(err)
        return err    

    return contributorAssetID

def buyDRT_method(
    client: AlgodClient,
    appID: int,
    buyer: Account,
    drtID: int,
    amountToBuy: int,
    paymentAmount: int
):
    """Execute DRT Method.

    This operation configures a group transaction that purchases a DRT
    Transaction 1 ensures the account has opted into the Asset. 
    Transaction 2 issues the "buy_drt" application call
    Transaction 3 sends the payment amount to the application

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        buyer: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT
        amountToBuy: The amount of tokens the buyer wishes to buy of the single DRT
        paymentAmount: The payment amount sent to the smart contract to buy the DRT(s)
        
    """
    #check user has opted in to asset
    optedIn = hasOptedIn(client=client, account=buyer.getAddress() ,assetID=drtID)
    if optedIn == None:
        optInToAsset(client=client,assetID=drtID, account=buyer)
    
    buyDRTTxn, paymentTxn = buyDRT_txn(
        client=client,
        appID=appID,
        buyer=buyer,
        drtID=drtID,
        amountToBuy=amountToBuy,
        paymentAmount=paymentAmount,
    )
    
    # # sign transactions
    signedbuyDRTTxn = buyDRTTxn.sign(buyer.getPrivateKey())
    signedpaymentTxn = paymentTxn.sign(buyer.getPrivateKey())

    # # send them over network (note that the accounts need to be funded for this to work)
    txid = client.send_transactions([signedbuyDRTTxn, signedpaymentTxn])
    
    try:
        response = waitForTransaction(client, txid)
        buyerBalances = getBalances(client=client,account=buyer.getAddress())
        assert buyerBalances[drtID] == amountToBuy

        print("DRT succesfully bought and transferred.")
        
        return response.txn
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err
    

def executeDRT_method(
    client: AlgodClient,
    owner: Account,
    appID: int,
    assetID: int,
    assetAmount: int,
    paymentAmount: int,
):
    """Buy DRT Method.

    This operation makes use of the executeDRT_txn builder to build and sign the group transaction
    to execute a DRT

    Args:
        client: An algod client.
        owner: the account of the owner of the DRT
        appID: The app ID of the smart contract Data Pool
        assetID: asset ID of DRT to execute
        assetAmount: total supply of asset to execute ( Always 1 )
        paymentAmount: fixed fee amount to the smart contract to execute the DRT
        
    """
    
    executerBalances_start = getBalances(client=client,account=owner.getAddress())
    appAddr = get_application_address(appID)
    appBalances_start = getBalances(client=client,account=appAddr)
    
    assetTransferTxn, paymentTxn, executeDRTTxn = executeDRT_txn(
        client=client,
        owner=owner,
        appID=appID,
        assetID=assetID,
        assetAmount=assetAmount,
        paymentAmount=paymentAmount,
    )
    
    # # sign transactions
    signedassetTransferTxn = assetTransferTxn.sign(owner.getPrivateKey())
    signedpaymentTxn = paymentTxn.sign(owner.getPrivateKey())
    signedexecuteDRTTxn = executeDRTTxn.sign(owner.getPrivateKey())

    # # send them over network (note that the accounts need to be funded for this to work)
    txid = client.send_transactions([signedassetTransferTxn, signedpaymentTxn, signedexecuteDRTTxn])
    
    try:
        response = waitForTransaction(client, txid)
        
        executerBalances_end = getBalances(client=client,account=owner.getAddress())
        appBalances_end = getBalances(client=client,account=appAddr)

        assert executerBalances_end[assetID] < executerBalances_start[assetID]
        assert appBalances_end[assetID] > appBalances_start[assetID]

        print("DRT executed, asset ID:", assetID)
        
        return response.txn
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err
