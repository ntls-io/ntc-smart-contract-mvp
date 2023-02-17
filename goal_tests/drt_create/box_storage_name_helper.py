
from algosdk.encoding import decode_address, encode_address,base64
import sys

asset_id = 2423
address_1 = "ZGCOJQ6YDAMLLMCM2HUFNZQX7HDEDL36XA5PWTJP5G254K5QV3YKNU3PAU"
#address_2 = "423I7OHNZZVPDZRQ4RUHHFI6DXBX5GBBT3HQJDXAGDCZWGHZF52IWJOULM"
  
asset_bytes = asset_id.to_bytes(8, 'big')
print(asset_bytes)
pk = decode_address(address_1)
print(pk)
box_name = asset_bytes + pk
#pk_2 = decode_address(address_2)
#box_name_2 = asset_bytes + pk_2

box_name = base64.b64encode(box_name)
#box_name_2 = base64.b64encode(box_name_2)
print("asset_id + address_1")
print(box_name)
#print("asset_id + address_2")
#print(box_name_2)