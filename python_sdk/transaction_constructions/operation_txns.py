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


from helpers.account import Account
from helpers.util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
    hasOptedIn,
)
from python_sdk.helpers.util import PendingTxnResponse


def createDRT_txn(
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

    This operation creates a the transaction for the DRT (Digital Rights Token). 

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

    suggestedParams = client.suggested_params()

    appArgs = [
        b"create_drt",
        drtName,
        drtSupply,
        drtBinaryUrl,
        drtBinaryHash,
        drtPrice
    ]
    
    createDRTTxn =  transaction.ApplicationCallTxn(
        sender=sender.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        note=drtNote
    )

    return createDRTTxn

def claimDRT_txn(
    client: AlgodClient,
    appID: int,
    sender: Account,
    drtID: int,
):
    """Claim DRT.

    This function creates the claim DRT transaction after it has been created and stores the DRT in box storage

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        sender: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

        
    """
    suggestedParams = client.suggested_params()
    
    appAddr = get_application_address(appID)
    asset_bytes = drtID.to_bytes(8, 'big')
    pk = decode_address(appAddr)

    box_name = asset_bytes + pk
    
    appArgs = [
        b"drt_to_box",
    ]

    claimDRTTxn =  transaction.ApplicationCallTxn(
        sender=sender.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        foreign_assets=[drtID],
        boxes=[[appID, box_name]],
    )

    return claimDRTTxn


def delistDRT_txn(
    client: AlgodClient,
    appID: int,
    creator: Account,
    drtID: int,
):
    """delist DRT.

    This function creates the delist transaction for a DRT.

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        creator: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

        
    """
    suggestedParams = client.suggested_params()
    
    appAddr = get_application_address(appID)
    asset_bytes = drtID.to_bytes(8, 'big')
    pk = decode_address(appAddr)

    box_name = asset_bytes + pk
    
    appArgs = [
        b"de_list_drt",
    ]

    deListDRTTxn =  transaction.ApplicationCallTxn(
        sender=creator.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        foreign_assets=[drtID],
        boxes=[[appID, box_name]],
    )

    return deListDRTTxn

def listDRT_txn(
    client: AlgodClient,
    appID: int,
    creator: Account,
    drtID: int,
):
    """list DRT.

    This function creates the re-listing transaction for a DRT.

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        creator: The account of the sender of the create DRT transaction (creator account).
        drtID: The asset ID of the newly created DRT

        
    """
    suggestedParams = client.suggested_params()
    
    appAddr = get_application_address(appID)
    asset_bytes = drtID.to_bytes(8, 'big')
    pk = decode_address(appAddr)

    box_name = asset_bytes + pk
    
    appArgs = [
        b"list_drt",
    ]

    listDRTTxn =  transaction.ApplicationCallTxn(
        sender=creator.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        foreign_assets=[drtID],
        boxes=[[appID, box_name]],
    )

    
    return listDRTTxn

def buyDRT_txn(
    client: AlgodClient,
    appID: int,
    buyer: Account,
    drtID: int,
    amountToBuy: int,
    paymentAmount: int
):
    """Buy DRT.

    This function configures a group transaction that purchases a DRT
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
    suggestedParams = client.suggested_params()
    appAddr = get_application_address(appID)
    
    
    asset_bytes = drtID.to_bytes(8, 'big')
    pk_appAddr = decode_address(appAddr)
    pk_buyer = decode_address(buyer.getAddress())

    box_name_existing = asset_bytes + pk_appAddr
    box_name_new = asset_bytes + pk_buyer
    
    #check user has opted in
    optedIn = hasOptedIn(client=client, account=buyer.getAddress() ,assetID=drtID)
    if optedIn == None:
        optInToAsset(client=client,assetID=drtID, account=buyer)
    
    appArgs = [
        b"buy_drt",
        amountToBuy,
    ]
    
    buyDRTTxn =  transaction.ApplicationCallTxn(
        sender=buyer.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        foreign_assets=[drtID],
        boxes=[[appID, box_name_existing],[appID, box_name_new]],
    )

    
    paymentTxn = transaction.PaymentTxn(
        sender=buyer.getAddress(),
        receiver=appAddr,
        amt=paymentAmount,
        sp=client.suggested_params(),
    )
    
    # get group id and assign it to transactions
    gid = transaction.calculate_group_id([buyDRTTxn, paymentTxn])

    buyDRTTxn.group = gid
    paymentTxn.group = gid


    return [buyDRTTxn, paymentTxn]
