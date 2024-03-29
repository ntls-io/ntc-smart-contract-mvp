from typing import Tuple, List
import json
from algosdk.encoding import decode_address
from algosdk.v2client.algod import AlgodClient
from algosdk import transaction
from algosdk.logic import get_application_address
from algosdk import account, encoding
from pyteal import compileTeal, Mode
from contracts.naut_prototype.drt_demo import approval,clear
from contracts.pyteal_helpers.strings import itoa
from base64 import b64decode
from helpers.resources import getTemporaryAccount, optInToAsset, createDummyAsset


from helpers.account import Account
from helpers.util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
)
from python_sdk.helpers.util import PendingTxnResponse

APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""


def getContracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    """Get the compiled TEAL contracts for the blockchain.

    Args:
        client: An algod client that has the ability to compile TEAL programs.

    Returns:
        A tuple of 2 byte strings. The first is the approval program, and the
        second is the clear state program.
    """
    global APPROVAL_PROGRAM
    global CLEAR_STATE_PROGRAM

    if len(APPROVAL_PROGRAM) == 0:
        APPROVAL_PROGRAM = fullyCompileContract(client, approval())
        CLEAR_STATE_PROGRAM = fullyCompileContract(client, clear())

    return APPROVAL_PROGRAM, CLEAR_STATE_PROGRAM


def deployContract(
    client: AlgodClient,
    sender: Account,
    enclave: Account,
    nautilus: Account
) -> int:
    """Create a new auction.

    Args:
        client: An algod client.
        sender: The account that will create the auction application.
        seller: The address of the seller that currently holds the NFT being
            auctioned.


    Returns:
        The ID of the newly created auction app.
    """
    approval, clear = getContracts(client)


    globalSchema = transaction.StateSchema(num_uints=50, num_byte_slices=6)
    localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    accounts = [
        enclave.getAddress(),
        nautilus.getAddress()
    ]
    
    pages = 2

    txn = transaction.ApplicationCreateTxn(
        sender=sender.getAddress(),
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=globalSchema,
        local_schema=localSchema,
        accounts=accounts,
        sp=client.suggested_params(),
        extra_pages=pages,
    )

    signedTxn = txn.sign(sender.getPrivateKey())

    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    print("Smart Contract successfully deployed.")
    assert response.applicationIndex is not None and response.applicationIndex > 0
    return response.applicationIndex


def initialiseDataPool(
    client: AlgodClient,
    appID: int,
    funder: Account,
    fundingAmount: int,
    enclave: Account,
    noRowsContributed: int,
    dataPackageHash: str,
    appendDRTName: str,
    appendDRTUnitName: str,
    appendDRTSupply: int,
    appendDRTPrice: int,
    appendDRTBinaryUrl: str,
    appendDRTBinaryHash: str,
) -> Tuple[int, int]:
    """Initialise the data pool.

    This operation funds the app data pool account, initialises the variables for the data pool
    and creates the contributor token for the initial contribution. This is step 2 of 3 for the 
    complete creation of the data pool.

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        funder: The account providing the funding for the smart contract (creator).
        fundingAmount: The amount to fund the smart contract
        enclave: account of the enclave,
        noRowsContributed: numbner of rows contributed by the creator,
        dataPackageHash: the hash of the data package,
        appendDRTName: the name of the appendDRT,
        appendDRTUnitName: the unit name of the appendDRT,
        appendDRTSupply: the total supply of appendDRTs, 
        appendDRTPrice: the price of the appendDRT in microAlgos,
    """
    appAddr = get_application_address(appID)

    suggestedParams = client.suggested_params()


    fundAppTxn = transaction.PaymentTxn(
        sender=funder.getAddress(),
        receiver=appAddr,
        amt=fundingAmount,
        sp=suggestedParams,
    )

    signedfundTxn = fundAppTxn.sign(funder.getPrivateKey())
    client.send_transaction(signedfundTxn)
    waitForTransaction(client, signedfundTxn.get_txid())

    appArgs = [
        b"init_contract",
        noRowsContributed,
        dataPackageHash,
        appendDRTName,
        appendDRTUnitName,
        appendDRTSupply,
        appendDRTPrice,
        appendDRTBinaryUrl,
        appendDRTBinaryHash,
    ]
    
    accounts = [
        funder.getAddress(),
    ]
    
    
    box_name = decode_address(funder.getAddress())
    
    setupTxn = transaction.ApplicationCallTxn(
        sender=enclave.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        accounts=accounts,
        sp=suggestedParams,
        boxes=[[appID, box_name]],
        foreign_apps=[appID]
    )
    print(setupTxn)

    signedSetupTxn = setupTxn.sign(enclave.getPrivateKey())
    txid = client.send_transaction(signedSetupTxn)
   
    try:
        response = waitForTransaction(client, txid)
        appendDRT = response.innerTxns[0]['asset-index']
        contributorDRT_1 = response.innerTxns[1]['asset-index']
        print("Smart Contract successfully initialised.")
        return [appendDRT, contributorDRT_1]
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err


def init_claimContributor(
    client: AlgodClient,
    appID: int,
    contributorAccount: Account,
    contributorAssetID: int,
    appendAssetID: int
):
    """Claim contributor token.

    Args:
        client: An algod client.
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
        appendAssetID,
    ]
    
    appAddr = get_application_address(appID)
    asset_bytes = appendAssetID.to_bytes(8, 'big')
    pk = decode_address(appAddr)
    

    box_name = asset_bytes + pk
    
    claimTxn = transaction.ApplicationCallTxn(
        sender=contributorAccount.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        foreign_assets=assets,
        sp=suggestedParams,
        boxes=[[appID, contributorAssetID.to_bytes(8, 'big')],[appID, box_name], [appID, decode_address(contributorAccount.getAddress())]],
    )

    signedTxn = claimTxn.sign(contributorAccount.getPrivateKey())

    txid = client.send_transaction(signedTxn)

    try:
        response = waitForTransaction(client, txid)  
        print("Initial contributor token successufully claimed by the creator.")
        return response
      
    except Exception as err:
        print("Uknown error..")
        print(err)
        return err

def completeDataPoolSetup(
    client: AlgodClient,
    creator: Account,
    enclave: Account,
    nautilus: Account,
    fundingAmount: int,
    noRowsContributed: int,
    dataPackageHash: str,
    appendDRTName: str,
    appendDRTUnitName: str,
    appendDRTPrice: int,
    appendDRTSupply:int,
    appendDRTBinaryUrl: str,
    appendDRTBinaryHash: str,
    ):
     
    try:
        appID = deployContract(
         client=client,
         sender=creator,
         enclave=enclave,
         nautilus=nautilus) 
    except Exception as err:
        print("Deploy Contract err")
        print(err)
        return err

    appAccount = get_application_address(appID)


    try:
       appendDRT,contributorDRT_1 = initialiseDataPool(
        client=client,
        appID=appID,
        funder=creator,
        fundingAmount=fundingAmount,
        enclave=enclave,
        noRowsContributed=noRowsContributed,
        dataPackageHash=dataPackageHash,
        appendDRTName=appendDRTName,
        appendDRTUnitName=appendDRTUnitName,
        appendDRTSupply=appendDRTSupply,
        appendDRTPrice=appendDRTPrice,
        appendDRTBinaryUrl=appendDRTBinaryUrl,
        appendDRTBinaryHash=appendDRTBinaryHash
    ) 
    except Exception as err:
        print("Intialise Data Pool err")
        print(err)
        return err
    

    optInToAsset(client, contributorDRT_1, creator)

    try:
        contributorClaim = init_claimContributor(
            client=client,
            appID=appID,
            contributorAccount=creator,
            contributorAssetID=contributorDRT_1,
            appendAssetID=appendDRT
            )
    except Exception as err:
        print("Claim Contributor Error")
        print(err)
        return err

    #box_stored = b64decode(client.application_box_by_name(appID, bytes(contributorDRT_1.to_bytes(8, 'big'), "utf-8"))['name']).decode("utf-8")
    contributor_transferred = client.account_asset_info(creator.getAddress(), contributorDRT_1)["asset-holding"]["asset-id"]

    #assert int(box_stored) == contributorDRT_1
    assert contributor_transferred == contributorDRT_1
    
    print("Smart Contract has been successfully created.")
    return appID,appAccount,appendDRT,contributorDRT_1

