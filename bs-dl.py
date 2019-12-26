#!/usr/bin/env python3
# Downloads base station information
# Author: pulkin

import urllib.request
import io
import csv
import gzip
import struct
import numpy
from numpy.lib import recfunctions

import inspect
import argparse

earth_radius = 6.3781e6

def download_and_repack(country_code=None, network_code=None, circle=None, token=None, source=None, destination=None, byte_order="b", verbose=False):
    """
    Downloads and packs the base station data.
    Args:
        country_code (int): the country code;
        network_code (int): the network code;
        circle (tuple): longitude, latitude (degrees) and radius in km;
        token (str): service token;
        source (str): downloaded file name;
        destination (str): destination file name;
        mnc_block_size (int): the size of the mnc block;
        mcc_block_size (int): the size of the mcc block;
        byte_order (str): byte order;
        verbose (bool): prints verbose output;
    """
    def v(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    byte_order = byte_order.lower()
    if byte_order not in "bl":
        raise ValueError("Unknown byte order: {}".format(byte_order))
    byte_order = dict(b=">", l="<")[byte_order]

    if destination is None:
        if country_code is None:
            destination = "all.bin"
        else:
            if network_code is None:
                destination = "{country_code}.bin".format(country_code=country_code)
            else:
                destination = "{country_code}-{network_code}.bin".format(country_code=country_code, network_code=network_code)

    v("Target: {}".format(destination))

    if source is None:
        if token is None:
            raise ValueError("Either token or source file name have to be specified")
        if country_code is None:
            url = "https://opencellid.org/ocid/downloads?token={token}&type=full&file=cell_towers.csv.gz".format(token=token)
        else:
            url = "https://opencellid.org/ocid/downloads?token={token}&type=mcc&file={country_code}.csv.gz".format(token=token, country_code=country_code)
        v("Downloading {} ...".format(url))
        response = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}))
        buf = io.BytesIO(response.read())

    else:
        v("Reading {} ...".format(source))
        buf = open(source, 'rb')

    v("Unzipping ...")
    buf_raw = gzip.GzipFile(fileobj=buf, mode='rb')
    buf_txt = io.TextIOWrapper(buf_raw)

    v("Parsing ...")
    dtype = [
        ('radio_type', 'S4'),
        ('mcc', byte_order + 'u2'),
        ('mnc', byte_order + 'u2'),
        ('area_code', byte_order + 'u2'),
        ('cell', byte_order + 'u2'),
        ('lon', byte_order + 'f4'),
        ('lat', byte_order + 'f4'),
    ]
    data = numpy.genfromtxt(buf_txt, dtype=dtype, skip_header=1, delimiter=",", usecols=(0, 1, 2, 3, 4, 6, 7))

    v("Filtering ...")
    data = data[data["radio_type"] == b"GSM"][["mcc", "mnc", "area_code", "cell", "lon", "lat"]]
    if country_code is not None:
        v(" - mcc: {:d}".format(len(data)), end="")
        data = data[data["mcc"] == country_code]
        v(" -> {:d}".format(len(data)))
    if network_code is not None:
        v(" - mnc: {:d}".format(len(data)), end="")
        data = data[data["mnc"] == network_code]
        v(" -> {:d}".format(len(data)))
    if circle is not None:
        v(" - circle: {:d}".format(len(data)), end="")
        phi0, theta0, r0 = circle
        theta = (data["lat"] - theta0) * numpy.pi / 180
        phi = (data["lon"] - phi0) * numpy.pi / 180
        mask = (theta ** 2 + phi ** 2 * numpy.cos(theta0) ** 2) < (r0 * 1e3 / earth_radius) ** 2
        data = data[mask]
        v(" -> {:d}".format(len(data)))

    if len(data) == 0:
        raise ValueError("No data to save")

    v("Sorting ...")
    data = numpy.sort(data, order=("mcc", "mnc", "area_code", "cell"))
    v("Items total: {:d}".format(len(data)))

    v("Preparing tables ...")
    keys = "mcc", "mnc"
    mask = numpy.zeros(len(data), dtype=bool)
    mask[0] = True
    for k in keys:
        mask[1:] |= data[k][1:] != data[k][:-1]
    table_ptrs = numpy.where(mask)[0]
    table_data = recfunctions.repack_fields(data[table_ptrs][list(keys)])

    v("Saving ...")
    with open(destination, 'wb') as f:
        f.write(b'agps-bin')
        f.write(b'\x00')
        f.write({">": b">", "<": b"<"}[byte_order])
        f.write(struct.pack(byte_order + "L", len(table_ptrs)))
        for _d, _p in zip(table_data, table_ptrs):
            f.write(struct.pack(byte_order + "HHL", *_d, _p))
        recfunctions.repack_fields(data[["area_code", "cell", "lon", "lat"]]).tofile(f)

        v("Total size: {:d} bytes".format(f.tell()))
    v("Done")


if __name__ == "__main__":
    spec = inspect.getfullargspec(download_and_repack)
    defaults = dict(zip(spec.args[-len(spec.defaults):], spec.defaults))

    def s2c(s):
        if s is None:
            return None
        return tuple(map(float, s.split(",")))

    def c2s(c):
        if c is None:
            return None
        return "{:.8f},{:.8f},{:.3f}".format(*c)

    parser = argparse.ArgumentParser(description="Downloads and unpacks base station data")
    parser.add_argument("--mcc", help="mobile country code", metavar="INT", type=int, default=defaults["country_code"])
    parser.add_argument("--mnc", help="mobile network code", metavar="INT", type=int, default=defaults["network_code"])
    parser.add_argument("--circle", help="limit stations to a circle", metavar="LON,LAT,R", default=c2s(defaults["circle"]))
    parser.add_argument("--token", help="access token", metavar="TOKEN", type=str, default=defaults["token"])
    parser.add_argument("--source", help="a file name to unpack from", metavar="FILENAME", type=str, default=defaults["source"])
    parser.add_argument("--destination", help="a file name to unpack to", metavar="FILENAME", type=str, default=defaults["destination"])
    parser.add_argument("-o", "--byteorder", help="byteorder: big or little Endian", metavar="B/L", type=str, default=defaults["byte_order"])
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    options = parser.parse_args()

    download_and_repack(
        country_code=options.mcc,
        network_code=options.mnc,
        circle=s2c(options.circle),
        token=options.token,
        source=options.source,
        destination=options.destination,
        byte_order=options.byteorder,
        verbose=options.verbose,
    )

