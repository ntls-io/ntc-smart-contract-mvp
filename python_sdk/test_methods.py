from time import time, sleep
from pyteal import *
import struct
import bitstring
from algosdk.encoding import decode_address, encode_address,base64
import pytest
from methods.sc_methods import createAndClaimDRT_method, delistDRT_method, listDRT_method, buyDRT_method, redeemAppendDRT_method, claimContributor_method, joinDataPool_method, executeDRT_method, addPendingContributor_method, pendingContributorConfirm_method, claimRoyalties_contributor
from algosdk import account, encoding
from algosdk.logic import get_application_address
from algosdk import *

from methods.sc_create_method import completeDataPoolSetup, init_claimContributor
from helpers.util import getBalances, getAppGlobalState, getLastBlockTimestamp, hasOptedIn
from helpers.setup import getAlgodClient
from helpers.resources import getTemporaryAccount, optInToAsset, createDummyAsset
from base64 import b64decode, b64encode

client = getAlgodClient()

creator = getTemporaryAccount(client)
enclave = getTemporaryAccount(client)
buyer = getTemporaryAccount(client)
contributor = getTemporaryAccount(client)
nautilus = getTemporaryAccount(client)

print("\n","Alice (data pool creator account):", creator.getAddress())
print("Enclave (enclacve account):", enclave.getAddress())
print("Bob (buyer account):", buyer.getAddress())
print("Carla (data contributor account)", contributor.getAddress(), "\n")
print("Nautilus (company account)", nautilus.getAddress(), "\n")

print(".....create Data Pool.....", "\n")

appID, appAccount, appendDRT, contributorDRT_1 = completeDataPoolSetup(
    client=client, 
    creator=creator, 
    enclave=enclave,
    nautilus=nautilus,
    fundingAmount=2000000, 
    noRowsContributed=5,
    dataPackageHash=b"DGVWUSNA--init--ASUDBQ",
    appendDRTName=b"Append_DRT",
    appendDRTUnitName=b"DRT",
    appendDRTPrice=1000000,
    appendDRTSupply=10000,
    appendDRTBinaryUrl=b"https://code_binary_url",
    appendDRTBinaryHash=b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
)

print("APP ID:", appID)
appAccount = get_application_address(appID)
print("APP ACCOUNT:",appAccount)
print("appendDRT ID:",appendDRT)
print("contributor 1 ID:",contributorDRT_1, "\n")

print(".....create DRT.....","\n")

id_DRT, drtSupply, drtPrice = createAndClaimDRT_method(
    client=client,
    creator=creator, 
    appID=appID,
    drtName=b"ALEX_DRT_01",
    drtPrice=1000000,
    drtBinaryUrl=b"https://code_binary_url",
    drtBinaryHash=b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    drtSupply=100,
    drtNote=b"note hello new drt",
)

print("DRT Created and claimed")
print("DRT ID:", id_DRT)
print("DRT Supply:", drtSupply)
print("DRT Price (microAlgos):", drtPrice, "\n")


print(".....de-list DRT.....","\n")

delist_drt = delistDRT_method(
    client=client,
    creator=creator, 
    appID=appID,
    drtID=id_DRT
)
print("")

print(".....re-list DRT for sale.....","\n")

delist_drt = listDRT_method(
    client=client,
    creator=creator, 
    appID=appID,
    drtID=id_DRT
)
print("")
print(".....Buy DRT.....","\n")
buy_test = buyDRT_method(
    client=client, 
    appID=appID, 
    buyer=buyer, 
    drtID=id_DRT, 
    amountToBuy=1, 
    paymentAmount=1000000
    )

print("")


print(".....Execute DRT.....","\n")
execute_drt = executeDRT_method(
    client=client,
    owner=buyer,
    appID=appID,
    assetID=id_DRT,
    assetAmount=1,
    paymentAmount=3000000   
)
print("")
print(".....Execute DRT Successfull.....","\n")
print(".....Join Data Pool.....","\n")
print("1. Purchase Append DRT.....")
buy_append = buyDRT_method(
    client=client, 
    appID=appID, 
    buyer=contributor, 
    drtID=appendDRT, 
    amountToBuy=1, 
    paymentAmount=1000000
)

print("2. add pending contributor.....")
add_pending = addPendingContributor_method(
    client=client,
    redeemer=contributor,
    appID=appID,
    appendID=appendDRT,
    paymentAmount=3000000,
    assetAmount=1
)
print("3. confirm pending contributor from enclave.....")
contributor_confirm = pendingContributorConfirm_method(
    client=client,
    appID=appID,
    contributor=contributor,
    enclave=enclave,
    rowsContributed=3,
    newHash=b"DGVWUSNA--new_confirm--ASUDBQ",
    enclaveApproval=1
)
# print(contributor)
# retrieve the asset Id of the conrtibutor token from blockchain
box_name = decode_address(contributor.getAddress())
box_contents = client.application_box_by_name(application_id=appID,box_name=box_name)
box_contents = box_contents["value"]
bytes = base64.b64decode(box_contents)
box_values = struct.unpack('!qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqql', bytes)
contributor_ID = box_values[0]

print("4. claim contributor token.....")
contributor_claim = claimContributor_method(
    client=client,
    appID=appID,
    contributorAccount=contributor,
    contributorAssetID=contributor_ID
)

## claim royalties as a contributor - creator
print("4. claim royalties from creators .....")
royalyties_claim = claimRoyalties_contributor(
    client=client,
    appID=appID,
    contributorAccount=creator,
    contributorAssetID=contributorDRT_1 
)

