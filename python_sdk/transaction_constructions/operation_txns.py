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


def appendRedeemDRT_txn(
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
    """Redeem the append DRT function.

    This function constructs the group transaction that is used when a append DRT is redeemed. i.e when a user wants to contribute data to the pool
    Transaction 1 transfers the append DRT back to the smart contract
    Transaction 2 issues the "add_data_contributor" instruction to the smart contract sent from the enclaves account after validation

    Args:
        client: An algod client.
        appID: The app ID of the smart contract Data Pool
        redeemer: The account of the user redeeming the append DRT
        enclave: The account of the enclave validating the incoming data
        appendID: The asset ID of the append DRT
        assetAmount: The amount of assets of the append DRT being redeemed, always 1
        rowsContributed: The amount of rows of data contributed to the pool
        newHash: The new hash of the data pool including the incoming data provided by the enclave
        enclaveApproval: The payment amount sent to the smart contract to buy the DRT(s)
        
    """
    suggestedParams = client.suggested_params()
    appAddr = get_application_address(appID)
    
    assetTransferTxn = transaction.AssetTransferTxn(
        sender=redeemer.getAddress(),
        receiver=appAddr,
        index=appendID,
        amt=assetAmount,
        sp=client.suggested_params(),
    )
    
    
    appArgs = [
        b"add_data_contributor",
        rowsContributed,
        newHash,
        enclaveApproval,
    ]
    
    addContributorTxn =  transaction.ApplicationCallTxn(
        sender=enclave.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        accounts=[redeemer.getAddress()],
    )
    
    # get group id and assign it to transactions
    gid = transaction.calculate_group_id([assetTransferTxn, addContributorTxn])

    assetTransferTxn.group = gid
    addContributorTxn.group = gid


    return [assetTransferTxn, addContributorTxn]


def oldclaimContributor_txn(
    client: AlgodClient,
    appID: int,
    contributorAccount: Account,
    contributorAssetID: int,
):
    """Claim contributor token.

    Args:
        client: An algod client.
        appID: The app ID of the smart contract Data Pool
        contributorAccount: The account that contributor data and needs to claim their token
        contributorAssetID: The asset ID of the contributor token.

    Returns:
        success or err.
    """  
    suggestedParams = client.suggested_params()
    
    appArgs = [
        b"box_store_transfer", 
    ]
    
    assets = [
        contributorAssetID,
    ]
    
    contributorClaimTxn = transaction.ApplicationCallTxn(
        sender=contributorAccount.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        foreign_assets=assets,
        sp=suggestedParams,
        boxes=[[appID, str(contributorAssetID)]],
    )

    return contributorClaimTxn



def executeDRT_txn(
    client: AlgodClient,
    owner: Account,
    appID: int,
    assetID: int,
    assetAmount: int,
    paymentAmount: int,
):
    """Execute DRT.

    This function constructs the group transaction that is used when a user wants to execute a DRT they own.
    Transaction 1 transfers the DRT back to the smart contract
    Transaction 2 pays for the execution of the DRT
    Transaction 3 issues the "execute_drt" instruction to the smart contract sent from the current Owners account

    Args:
        client: An algod client.
        owner: the account of the owner of the DRT
        appID: The app ID of the smart contract Data Pool
        assetID: asset ID of DRT to execute
        assetAmount: total supply of asset to execute ( Always 1 )
        paymentAmount: fixed fee amount to the smart contract to execute the DRT
        
    """
    suggestedParams = client.suggested_params()
    appAddr = get_application_address(appID)
    
    #asset transfer Txn
    assetTransferTxn = transaction.AssetTransferTxn(
        sender=owner.getAddress(),
        receiver=appAddr,
        index=assetID,
        amt=assetAmount,
        sp=client.suggested_params(),
    )
    
    #payment transaction
    paymentTxn = transaction.PaymentTxn(
        sender=owner.getAddress(),
        receiver=appAddr,
        amt=paymentAmount,
        sp=client.suggested_params(),
    )
    
    #variables for "execute drt" transaction
    appArgs = [
        b"execute_drt",
    ]
    
    asset_bytes = assetID.to_bytes(8, 'big')
    pk_appAddr = decode_address(appAddr)
    pk_executer = decode_address(owner.getAddress())

    box_name_owner = asset_bytes + pk_executer
    box_name_app = asset_bytes + pk_appAddr
    
    executeDRTTxn =  transaction.ApplicationCallTxn(
        sender=owner.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        foreign_assets=[assetID],
        boxes=[[appID, box_name_app], [appID, box_name_owner]]
    )
    
    # get group id and assign it to transactions
    gid = transaction.calculate_group_id([assetTransferTxn, paymentTxn, executeDRTTxn])

    assetTransferTxn.group = gid
    paymentTxn.group = gid
    executeDRTTxn.group = gid


    return [assetTransferTxn, paymentTxn, executeDRTTxn]


def pendingContributor_txn(
    client: AlgodClient,
    appID: int,
    redeemer: Account,
    appendID: int,
    assetAmount: int,  
    paymentAmount: int,
):
    """Redeem the append DRT function.

    This function constructs the group transaction that is used when a append DRT is redeemed. i.e when a user wants to contribute data to the pool
    Transaction 1 transfers the append DRT back to the smart contract
    Transaction 2 sends payment to the smart contract for the execution fee
    Transaction 3 sends instruction to the smart contract to add user as a contributor pending approval from enclave

    Args:
        client: An algod client.
        appID: The app ID of the smart contract Data Pool
        redeemer: The account of the user redeeming the append DRT
        appendID: The asset ID of the append DRT
        assetAmount: The amount of assets of the append DRT being redeemed, always 1
    """
    suggestedParams = client.suggested_params()
    appAddr = get_application_address(appID)
    
    #txn 1
    assetTransferTxn = transaction.AssetTransferTxn(
        sender=redeemer.getAddress(),
        receiver=appAddr,
        index=appendID,
        amt=assetAmount,
        sp=client.suggested_params(),
    )
    
    #txn 2
    paymentTxn = transaction.PaymentTxn(
        sender=redeemer.getAddress(),
        receiver=appAddr,
        amt=paymentAmount,
        sp=client.suggested_params(),
    )
    
    #txn 3
    appArgs = [
        b"add_contributor_pending",
    ]
    
    box_name = decode_address(redeemer.getAddress())
    
    addPendingContributorTxn =  transaction.ApplicationCallTxn(
        sender=redeemer.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        boxes=[[appID, box_name]]
    )
    
    # get group id and assign it to transactions
    gid = transaction.calculate_group_id([assetTransferTxn, paymentTxn,addPendingContributorTxn])

    assetTransferTxn.group = gid
    paymentTxn.group = gid
    addPendingContributorTxn.group = gid


    return [assetTransferTxn, paymentTxn, addPendingContributorTxn]


def confirmContributor_txn(
    client: AlgodClient,
    appID: int,
    contributor: Account,
    enclave: Account,
    rowsContributed: int,
    newHash: str,
    enclaveApproval: int,
    
):
    """Confirm the contributors data contribution from enclave.

    This function confirms the data contribution from within the enclave
    
    Args:
        client: An algod client.
        appID: The app ID of the smart contract Data Pool
        contributor: The account of the user redeeming the append DRT
        enclave: The account of the enclave validating the incoming data
        appendID: The asset ID of the append DRT
        assetAmount: The amount of assets of the append DRT being redeemed, always 1
        rowsContributed: The amount of rows of data contributed to the pool
        newHash: The new hash of the data pool including the incoming data provided by the enclave
        enclaveApproval: The payment amount sent to the smart contract to buy the DRT(s)
        
    """
    suggestedParams = client.suggested_params()
    appAddr = get_application_address(appID)
    
    
    appArgs = [
        b"add_contributor_approved",
        rowsContributed,
        newHash,
        enclaveApproval,
    ]
    
    box_name = decode_address(contributor.getAddress())
    
    addConfirmContributorTxn =  transaction.ApplicationCallTxn(
        sender=enclave.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        sp=suggestedParams,
        accounts=[contributor.getAddress()],
        boxes=[[appID, box_name]]
    )
    


    return addConfirmContributorTxn


def claimContributor_txn(
    client: AlgodClient,
    appID: int,
    contributorAccount: Account,
    contributorAssetID: int,
):
    """Claim contributor token.

    Args:
        client: An algod client.
        appID: The app ID of the smart contract Data Pool
        contributorAccount: The account that contributor data and needs to claim their token
        contributorAssetID: The asset ID of the contributor token.

    Returns:
        success or err.
    """  
    suggestedParams = client.suggested_params()
    
    appArgs = [
        b"add_contributor_claim", 
    ]
    
    assets = [
        contributorAssetID,
    ]
    
    contributorClaimTxn = transaction.ApplicationCallTxn(
        sender=contributorAccount.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        foreign_assets=assets,
        sp=suggestedParams,
        boxes=[[appID, contributorAssetID.to_bytes(8, 'big')], [appID, decode_address(contributorAccount.getAddress())]],
    )

    return contributorClaimTxn

def claimRoyalties_contributortxn(
    client: AlgodClient,
    appID: int,
    contributorAccount: Account,
    contributorAssetID: int,
):
    """Claim contributor token.

    Args:
        client: An algod client.
        appID: The app ID of the smart contract Data Pool
        contributorAccount: The account that contributor data and needs to claim their token
        contributorAssetID: The asset ID of the contributor token.

    Returns:
        success or err.
        
    const txn = algosdk.makeApplicationCallTxnFromObject({
      from: contributorAddr,
      appIndex: Number(appID),
      suggestedParams: params,
      onComplete: onComplete,
      appArgs: appArgs,
      foreignAssets: [Number(contributorAssetID)],
      boxes: [
        {
          appIndex: Number(appID),
          name: algosdk.encodeUint64(contributorAssetID)
        }
      ]
    });
    """  
    suggestedParams = client.suggested_params()
    
    appArgs = [
        b"claim_royalty_contributor", 
    ]
    
    assets = [
        contributorAssetID,
    ]
    
    contributorRoyaltiesTxn = transaction.ApplicationCallTxn(
        sender=contributorAccount.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        foreign_assets=assets,
        sp=suggestedParams,
        boxes=[[appID, contributorAssetID.to_bytes(8, 'big')]],
    )

    return contributorRoyaltiesTxn

