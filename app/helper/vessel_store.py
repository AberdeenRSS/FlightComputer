from typing import Union, cast
# from plyer import uniqueid
# from plyer.facades import UniqueID
from kivy.storage.jsonstore import JsonStore
from uuid import uuid4

# id = cast(UniqueID, uniqueid)

store = JsonStore('vessel_info.json')

def get_vessel_id():
    if not store.exists('vessel_id'):
        new_id = str(uuid4())
        store.put('vessel_id', id=new_id)
        return new_id
    
    return store.get('vessel_id')['id']


def get_vessel_name():
    if not store.exists('vessel_name'):
        return None
    
    return store.get('vessel_name')['name']

def set_vessel_name(name: str):
    store.put('vessel_name', name=name)

def get_vessel_auth_code() -> Union[str, None]:
    if not store.exists('auth_code'):
        return None
    
    return store.get('auth_code')['auth_code']

def set_vessel_auth_code(code: str):
    store.put('auth_code', auth_code = code)
