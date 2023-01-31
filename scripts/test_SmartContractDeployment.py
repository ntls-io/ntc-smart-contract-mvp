from time import time, sleep
from algosdk.encoding import decode_address, encode_address,base64
import pytest

from algosdk import account, encoding
from algosdk.logic import get_application_address

from operations import completeDataPoolSetup,deployContract, initialiseDataPool, claimContributor
from helpers.util import getBalances, getAppGlobalState, getLastBlockTimestamp
from helpers.setup import getAlgodClient
from helpers.resources import getTemporaryAccount, optInToAsset, createDummyAsset
from base64 import b64decode, b64encode



client = getAlgodClient()

creator = getTemporaryAccount(client)
enclave = getTemporaryAccount(client)
buyer = getTemporaryAccount(client)
contributor = getTemporaryAccount(client)

print("Alice (data pool creator account):", creator.getAddress())
print("Enclave (enclacve account):", enclave.getAddress())
print("Bob (buyer account):", buyer.getAddress())
print("Carla (data contributor account)", contributor.getAddress(), "\n")

appID,appAccount,appendDRT,contributorDRT_1 = completeDataPoolSetup(
    client=client, 
    creator=creator, 
    enclave=enclave, 
    fundingAmount=1000000, 
    noRowsContributed=5,
    dataPackageHash=b"DGVWUSNA--init--ASUDBQ",
    appendDRTName=b"Append_DRT",
    appendDRTUnitName=b"DRT",
    appendDRTPrice=1000000,
)

print("APP ID:", appID)
appAccount = get_application_address(appID)
print("APP ACCOUNT:",appAccount)
print("appendDRT ID:",appendDRT)
print("contributor 1 ID:",contributorDRT_1)

