async def find_token_by_websocket(mapping, websocket_obj):
    for token, data in mapping.items():
        if data[0] == websocket_obj:
            return token
    return None


async def swap_dict_keys(d, key1, key2):
    keys = list(d.keys())
    i1, i2 = keys.index(key1), keys.index(key2)
    keys[i1], keys[i2] = keys[i2], keys[i1]
    return {k: d[k] for k in keys}

