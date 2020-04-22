micropython-agps
----------------

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
(78.86739615869062, 3.484547378491735)
```

### Location using local database:

Create a binary database of GSM cells:

```bash
~ ./bs-dl.py --mcc 234 --mnc 10 --circle=51.509865,-0.118092,3 -v --token api-token # Please visit https://opencellid.org for getting your API token
Target: 234-10.bin
Downloading https://opencellid.org/ocid/downloads?token=[token]&type=mcc&file=234.csv.gz ...
Unzipping ...
Parsing ...
Filtering ...
 - mcc: 322671 -> 322671
 - mnc: 322671 -> 99367
 - circle: 99367 -> 2749
Sorting ...
Items total: 2749
Preparing tables ...
Saving ...
Total size: 33010 bytes
Done
```

Filtering is done through entries `mcc` - mobile country code, `mnc` - mobile network code and `circle` - location and radius of a circle with cells.
All entries are optional, however, the full worldwide database is as large as 1Gb.
Providing `mcc` and `mnc` will reduce the databse size down to few Mb.
Providing a `circle` will further filter data towards the circular area specified: 3 km of urban area results in around 10Kb of data.

Note that the token is optional: without a proper token, the script will fall back to a git mirror which may contain outdated data.

Then, upload the database to the module (note the file name):

```bash
ampy --port /dev/ttyUSB0 put 234-10.bin
```

Finally, determine the location (no data connection needed):

```python
# Get location
import agps
import cellular
agps.get_location_local(cellular.agps_station_data(), "234-10.bin")
(51.54547378491735, -0.11739615869062)
```

Raw data
--------

Please find [here](https://github.com/pulkin/agps-data).

