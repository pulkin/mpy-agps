import urequests
import struct
import cellular

def group_stations(s):
    by_op = {}
    best = None
    best_count = 0
    for mcc, mnc, lac, cell_id, bsic, rx_full, rx_sub, arfcn in s:
        grp = mcc, mnc
        if grp not in by_op:
            by_op[grp] = []
        by_op[grp].append((lac, cell_id, rx_full))
        count = len(by_op[grp])
        if best is None or count > best_count:
            best_count = count
            best = grp

    return best[0], best[1], by_op[best]

def get_location_radiocells():
    s = cellular.stations()
    if len(s) == 0:
        raise ValueError("No stations reported by GSM module")
    c = dict(cellTowers=list(dict(cellId=cell_id, locationAreaCode=lac, mobileCountryCode=mcc, mobileNetworkCode=mnc) for mcc, mnc, lac, cell_id, bsic, rx_full, rx_sub, arfcn in s))
    r = urequests.post('https://backend.radiocells.org/', json=c)
    json = r.json()
    if "location" in json:
        return json["location"]["lng"], json["location"]["lat"]

def get_location_opencellid(api_key):
    s = cellular.stations()
    if len(s) == 0:
        raise ValueError("No stations reported by GSM module")
    mcc, mnc, cells = group_stations(s)
    c = dict(token=api_key, radio="gsm", mcc=mcc, mnc=mnc, cells=tuple(
        dict(cid=cid, lac=lac)
        for lac, cid, _ in cells
    ))
    r = urequests.post('https://eu1.unwiredlabs.com/v2/process.php', json=c)
    json = r.json()
    if "status" in json and json["status"] == "ok":
        return json["lon"], json["lat"]
    else:
        raise RuntimeError("Failed to fetch response: {}".format(json))

def __bin_search__(f, match, fmt, stride, l):
    table_head = f.tell()
    size = struct.calcsize(fmt)
    head = 0
    if l is None:
        _pos = f.tell()
        f.seek(0, 2)
        l = f.tell()
        f.seek(_pos)
        tail = (l - _pos) // stride - 1
    else:
        tail = l - 1
    head_val = struct.unpack(fmt, f.read(size))
    f.seek(table_head + tail * stride)
    tail_val = struct.unpack(fmt, f.read(size))

    if not head_val <= tail_val:
        raise ValueError("Corrupted table: {} </= {}".format(head_val, tail_val))

    if match < head_val or match > tail_val:
        f.seek(table_head)
        return None

    while True:
        if head > tail:
            f.seek(table_head)
            return None
        c = (head + tail) // 2
        f.seek(table_head + stride * c)
        c_val = struct.unpack(fmt, f.read(size))
        if c_val == match:
            result = f.read(stride - size)
            f.seek(table_head)
            return c, result
        elif head_val <= c_val < match <= tail_val:
            head = c + 1
            head_val = c_val
        elif head_val <= match < c_val <= tail_val:
            tail = c - 1
            tail_val = c_val
        else:
            raise ValueError("Corrupted table: {} </= {} </= {}".format(head_val, c_val, tail_val))


def get_location_local(fname):
    s = cellular.stations()
    if len(s) == 0:
        raise ValueError("No stations reported by GSM module")
    mcc, mnc, cells = group_stations(s)
    mnc //= 10
    x = y = n = 0
    with open(fname, 'rb') as f:
        if f.read(9) != b'agps-bin\x00':
            raise ValueError("Wrong file signature")
        byte_order = {b'>': '>', b'<': '<'}[f.read(1)]
        tab_l = struct.unpack(byte_order + "L", f.read(4))[0]
        tab_entry = __bin_search__(f, (mcc, mnc), byte_order + "HH", 8, tab_l)
        if tab_entry is None:
            raise ValueError("mcc/mnc not found")
        entry, offset = tab_entry
        offset = struct.unpack(byte_order + "L", offset)[0]
        table_head = f.tell()
        if entry < tab_l - 1:
            f.seek(table_head + 8 * (entry + 1) + 4)
            offset2 = struct.unpack(byte_order + "L", f.read(4))[0]
        else:
            offset2 = None
        table_head += tab_l * 8
        table_head += offset * 12
        f.seek(table_head)
        for lac, cid, dbm in cells:
            tab_entry = __bin_search__(f, (lac, cid), byte_order + "HH", 12, None if offset2 is None else offset2 - offset)
            if tab_entry is not None:
                _x, _y = struct.unpack(byte_order + "ff", tab_entry[1])
                w = 10 ** (0.1 * dbm)
                x += _x * w
                y += _y * w
                n += w
    if n == 0:
        raise ValueError("Failed to identify a single station")
    return x / n, y / n

