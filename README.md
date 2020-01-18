mpy-agps

For use with [micropython on GPRS module A9/A9G](https://github.com/pulkin/micropython/tree/master/ports/gprs_a9).

Examples
--------

### Location over internet connection:

```python
# Enable data connection
import cellular
cellular.gprs("apn", "user", "pass")

# Get location
import agps
agps.get_location_opencellid(cellular.agps_station_data(), "api-token") # Please visit https://opencellid.org for getting your API token
(3.484547378491735, 78.86739615869062)
```

### Location using local database:

Create a binary database of GSM cells:

```bash
./bs-dl.py --mcc 234 --mnc 3 --circle=-0.118092,51.509865,3 -v --token api-token # Please visit https://opencellid.org for getting your API token
```

Filtering is done through entries `mcc` - mobile country code, `mnc` - mobile network code and `circle` - location and radius of a circle with cells.
All entries are optional, however, the full worldwide database is as large as 1Gb.
Providing `mcc` and `mnc` will reduce the databse size down to few Mb.

Then, upload the database to the module (note the file name):

```bash
ampy --port /dev/ttyUSB0 put 234-3.bin
```

Finally, determine the location (no data connection needed):

```python
# Get location
import agps
import cellular
agps.get_location_local(cellular.agps_station_data(), "234-3.bin")
(3.484547378491735, 78.86739615869062)
```

