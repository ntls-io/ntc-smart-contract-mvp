from typing import Tuple, List
import json

from algosdk.v2client.algod import AlgodClient
from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk import account, encoding
from pyteal import compileTeal, Mode
from contracts.naut_prototype.drt_demo import approval,clear
from pyteal_helpers.strings import itoa
from base64 import b64decode
from helpers.resources import getTemporaryAccount, optInToAsset, createDummyAsset


from helpers.account import Account
from helpers.util import (
    waitForTransaction,
    fullyCompileContract,
    getAppGlobalState,
)

APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""


def getContracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    """Get the compiled TEAL contracts for the auction.

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
        CLEAR_STATE_PROGRAM = fullyCompileContract(client,clear())

    return APPROVAL_PROGRAM, CLEAR_STATE_PROGRAM


def deployContract(
    client: AlgodClient,
    sender: Account,
    enclave: Account,
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
    dataPackageHash,
    appendDRTName,
    appendDRTUnitName,
    appendDRTPrice,
    
):
    """Finish setting up an auction.

    This operation funds the app auction escrow account, opts that account into
    the NFT, and sends the NFT to the escrow account, all in one atomic
    transaction group. The auction must not have started yet.

    The escrow account requires a total of 0.203 Algos for funding. See the code
    below for a breakdown of this amount.

    Args:
        client: An algod client.
        appID: The app ID of the auction.
        funder: The account providing the funding for the escrow account.
        nftHolder: The account holding the NFT.
        nftID: The NFT ID.
        nftAmount: The NFT amount being auctioned. Some NFTs has a total supply
            of 1, while others are fractional NFTs with a greater total supply,
            so use a value that makes sense for the NFT being auctioned.
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
        appendDRTPrice,  
    ]
    
    accounts = [
        funder.getAddress(),
    ]
    
    
    setupTxn = transaction.ApplicationCallTxn(
        sender=enclave.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        accounts=accounts,
        sp=suggestedParams,
    )

    signedSetupTxn = setupTxn.sign(enclave.getPrivateKey())
    txid = client.send_transaction(signedSetupTxn)
    #print("Successfully sent transaction with txID: {}".format(txid))
    try:
        response = waitForTransaction(client, txid)  
        appendDRT = response.innerTxns[0]['asset-index']
        contributorDRT_1 = response.innerTxns[1]['asset-index']
        result = [appendDRT, contributorDRT_1]
        print("Smart Contract successfully initialised.")
        return result
      
    except Exception as err:
        print(err)
        return


def claimContributor(
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
    suggestedParams = client.suggested_params()
    
    appArgs = [
        b"box_store_transfer", 
    ]
    
    assets = [
        contributorAssetID,
    ]
    
    claimTxn = transaction.ApplicationCallTxn(
        sender=contributorAccount.getAddress(),
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=appArgs,
        foreign_assets=assets,
        sp=suggestedParams,
        boxes=[[appID, str(contributorAssetID)]],
    )

    signedTxn = claimTxn.sign(contributorAccount.getPrivateKey())
    #print(signedTxn)

    txid = client.send_transaction(signedTxn)

    try:
        response = waitForTransaction(client, txid)  
        print("Initial contributor token successufully claimed by the creator.")
        return response
      
    except Exception as err:
        print(err)
        return

def completeDataPoolSetup(
    client: AlgodClient,
    creator: Account,
    enclave: Account,
    fundingAmount: int,
    noRowsContributed: int,
    dataPackageHash,
    appendDRTName,
    appendDRTUnitName,
    appendDRTPrice,
    ):
    appID = deployContract(
        client=client,
        sender=creator,
        enclave=enclave
    )

    actual = getAppGlobalState(client, appID)
    appAccount = get_application_address(appID)

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
        appendDRTPrice=appendDRTPrice,
    )

    optInToAsset(client, contributorDRT_1, creator)

    contributorClaim = claimContributor(client=client,appID=appID,contributorAccount=creator,contributorAssetID=contributorDRT_1)

    box_stored = b64decode(client.application_box_by_name(appID, bytes(str(contributorDRT_1), "utf-8"))['name']).decode("utf-8")
    contributor_transferred = client.account_asset_info(creator.getAddress(), contributorDRT_1)["asset-holding"]["asset-id"]

    assert int(box_stored) == contributorDRT_1
    assert contributor_transferred == contributorDRT_1
    
    print("Smart Contract has been successfully created.")
    return appID,appAccount,appendDRT,contributorDRT_1


# def placeBid(client: AlgodClient, appID: int, bidder: Account, bidAmount: int) -> None:
#     """Place a bid on an active auction.

#     Args:
#         client: An Algod client.
#         appID: The app ID of the auction.
#         bidder: The account providing the bid.
#         bidAmount: The amount of the bid.
#     """
#     appAddr = get_application_address(appID)
#     appGlobalState = getAppGlobalState(client, appID)

#     nftID = appGlobalState[b"nft_id"]

#     if any(appGlobalState[b"bid_account"]):
#         # if "bid_account" is not the zero address
#         prevBidLeader = encoding.encode_address(appGlobalState[b"bid_account"])
#     else:
#         prevBidLeader = None

#     suggestedParams = client.suggested_params()

#     payTxn = transaction.PaymentTxn(
#         sender=bidder.getAddress(),
#         receiver=appAddr,
#         amt=bidAmount,
#         sp=suggestedParams,
#     )

#     appCallTxn = transaction.ApplicationCallTxn(
#         sender=bidder.getAddress(),
#         index=appID,
#         on_complete=transaction.OnComplete.NoOpOC,
#         app_args=[b"bid"],
#         foreign_assets=[nftID],
#         # must include the previous lead bidder here to the app can refund that bidder's payment
#         accounts=[prevBidLeader] if prevBidLeader is not None else [],
#         sp=suggestedParams,
#     )

#     transaction.assign_group_id([payTxn, appCallTxn])

#     signedPayTxn = payTxn.sign(bidder.getPrivateKey())
#     signedAppCallTxn = appCallTxn.sign(bidder.getPrivateKey())

#     client.send_transactions([signedPayTxn, signedAppCallTxn])

#     waitForTransaction(client, appCallTxn.get_txid())




# def closeAuction(client: AlgodClient, appID: int, closer: Account):
    
    """Close an auction.

    This action can only happen before an auction has begun, in which case it is
    cancelled, or after an auction has ended.

    If called after the auction has ended and the auction was successful, the
    NFT is transferred to the winning bidder and the auction proceeds are
    transferred to the seller. If the auction was not successful, the NFT and
    all funds are transferred to the seller.

    Args:
        client: An Algod client.
        appID: The app ID of the auction.
        closer: The account initiating the close transaction. This must be
            either the seller or auction creator if you wish to close the
            auction before it starts. Otherwise, this can be any account.
    """
    appGlobalState = getAppGlobalState(client, appID)

    nftID = appGlobalState[b"nft_id"]

    accounts: List[str] = [encoding.encode_address(appGlobalState[b"seller"])]

    if any(appGlobalState[b"bid_account"]):
        # if "bid_account" is not the zero address
        accounts.append(encoding.encode_address(appGlobalState[b"bid_account"]))

    deleteTxn = transaction.ApplicationDeleteTxn(
        sender=closer.getAddress(),
        index=appID,
        accounts=accounts,
        foreign_assets=[nftID],
        sp=client.suggested_params(),
    )
    signedDeleteTxn = deleteTxn.sign(closer.getPrivateKey())

    client.send_transaction(signedDeleteTxn)

    waitForTransaction(client, signedDeleteTxn.get_txid())