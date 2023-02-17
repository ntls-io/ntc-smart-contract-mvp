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
from transaction_constructions.operation_txns import createDRT_txn, claimDRT_txn, delistDRT_txn, listDRT_txn, buyDRT_txn


from helpers.account import Account
from helpers.util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
    hasOptedIn,
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

def buyDRT_method(
    client: AlgodClient,
    appID: int,
    buyer: Account,
    drtID: int,
    amountToBuy: int,
    paymentAmount: int
):
    """list DRT.

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
    buyDRTTxn, paymentTxn = buyDRT_txn(
        client=client,
        appID=appID,
        buyer=buyer,
        drtID=drtID,
        amountToBuy=amountToBuy,
        paymentAmount=paymentAmount,
    )
    
    # # sign transactions
    signedcreateDRTTxn = buyDRTTxn.sign(buyer.getPrivateKey())
    signedpaymentTxn = paymentTxn.sign(buyer.getPrivateKey())

    # # send them over network (note that the accounts need to be funded for this to work)
    txid = client.send_transactions([signedcreateDRTTxn, signedpaymentTxn])
    
    try:
        response = waitForTransaction(client, txid)
        print("DRT succesfully bought.")
        
        return response.txn
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err
