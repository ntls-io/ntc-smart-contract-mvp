

from algosdk.encoding import decode_address, encode_address,base64

asset_id = 63
  
asset_bytes = asset_id.to_bytes(8, 'big')

#account_app = KRI4UNYE3S6H4OC3T3I2JPG4475D7AJNXGQJKWWBEBJW7KJSBMWTY3R5MM
#acccount_1 = EM7HQ6AR6K3CRJZPTSMDQUPE6BWESSTXLDO72DQYVGTTZ65LXAVQHRJUOM
# account_2 = 423I7OHNZZVPDZRQ4RUHHFI6DXBX5GBBT3HQJDXAGDCZWGHZF52IWJOULM
# account_enclave = 7ZNAPIHJ22E4AF2XFTDLUVXFLESFRBXTZBK6YT6BEY6XIKCS4YGXA2PQ5A

address_owner = "7ZNAPIHJ22E4AF2XFTDLUVXFLESFRBXTZBK6YT6BEY6XIKCS4YGXA2PQ5A"
buyer = "423I7OHNZZVPDZRQ4RUHHFI6DXBX5GBBT3HQJDXAGDCZWGHZF52IWJOULM"

pk = decode_address(address_owner)
box_name = asset_bytes + pk
pk_2 = decode_address(buyer)
buyer_name = asset_bytes + pk_2

box_name = base64.b64encode(box_name)
buyer_name = base64.b64encode(buyer_name)
print("owner+asset_id")
print(box_name)
print("buyer+asset_id")
print(buyer_name)
