import geoip2.database
import ipaddress
import requests
import os


ASN_FILE = "asn.txt"

GEOIP_DB = "GeoLite2-Country.mmdb"

OUTPUT_DIR = "output"

ALL_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "all_cidr_list.txt"
)

US_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "all_US_cidr_list.txt"
)

MAX_LINES = 5000


# -------------------------
# GeoLite2 Database
# -------------------------

reader = geoip2.database.Reader(
    GEOIP_DB
)


def get_country(ip):
    """
    Lookup IP country locally
    """

    try:

        result = reader.country(ip)

        return result.country.iso_code

    except Exception:

        return None



# -------------------------
# RIPEstat ASN Prefix Lookup
# -------------------------

def get_prefixes(asn):
    """
    Get announced IPv4 prefixes from RIPEstat
    """

    url = (
        "https://stat.ripe.net/data/"
        "announced-prefixes/data.json?"
        f"resource={asn}"
    )


    r = requests.get(
        url,
        timeout=30
    )

    r.raise_for_status()


    data = r.json()


    prefixes = []


    for item in data["data"]["prefixes"]:

        prefix = item["prefix"]


        # IPv4 only
        if ":" not in prefix:

            prefixes.append(
                prefix
            )


    return prefixes



# -------------------------
# CIDR Sorting
# -------------------------

def cidr_key(cidr):

    return ipaddress.IPv4Network(
        cidr,
        strict=False
    )



# -------------------------
# Sample IPs in CIDR
# -------------------------

def sample_ips(cidr):

    network = ipaddress.IPv4Network(
        cidr,
        strict=False
    )

    total = network.num_addresses


    # Small ranges: check all
    if total <= 16:

        return [
            str(ip)
            for ip in network
        ]


    # Large ranges
    return [

        str(network.network_address),

        str(
            network.network_address +
            int(total / 2)
        ),

        str(network.broadcast_address)

    ]



# -------------------------
# Write split files
# -------------------------

def write_chunks(prefixes):

    chunks = [

        prefixes[i:i + MAX_LINES]

        for i in range(
            0,
            len(prefixes),
            MAX_LINES
        )

    ]


    for index, chunk in enumerate(
        chunks,
        start=1
    ):


        filename = os.path.join(
            OUTPUT_DIR,
            f"US_cidr_list_{index}.txt"
        )


        with open(
            filename,
            "w"
        ) as f:


            for cidr in chunk:

                f.write(
                    cidr + "\n"
                )


        print(
            f"Wrote {filename} "
            f"({len(chunk)} entries)"
        )



# -------------------------
# Main
# -------------------------

def main():


    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


    #
    # Load ASNs
    #

    with open(
        ASN_FILE,
        "r"
    ) as f:


        asns = [

            line.strip()

            for line in f

            if line.strip()

            and not line.startswith("#")

        ]


    print(
        f"Loaded {len(asns)} ASNs"
    )



    #
    # Get CIDRs
    #

    all_prefixes = set()



    for asn in asns:


        print(
            f"\nProcessing {asn}"
        )


        try:


            prefixes = get_prefixes(
                asn
            )


            print(
                f"Found {len(prefixes)} IPv4 prefixes"
            )


            all_prefixes.update(
                prefixes
            )


        except Exception as e:


            print(
                f"{asn} failed: {e}"
            )



    #
    # Sort CIDRs
    #

    sorted_prefixes = sorted(
        all_prefixes,
        key=cidr_key
    )



    #
    # Write all CIDRs
    #

    with open(
        ALL_CIDR_FILE,
        "w"
    ) as f:


        for cidr in sorted_prefixes:

            f.write(
                cidr + "\n"
            )


    print()

    print(
        f"Wrote {ALL_CIDR_FILE}"
    )

    print(
        f"Total CIDRs: {len(sorted_prefixes)}"
    )



    #
    # Geo filtering
    #

    us_prefixes = []


    print(
        "\nChecking GeoLite2 locations...\n"
    )



    for count, cidr in enumerate(
        sorted_prefixes,
        start=1
    ):


        try:


            samples = sample_ips(
                cidr
            )


            countries = []


            for ip in samples:


                country = get_country(
                    ip
                )


                countries.append(
                    country
                )



            #
            # KEEP if ANY IP is US
            #

            if "US" in countries:


                us_prefixes.append(
                    cidr
                )


                print(
                    f"KEEP {cidr} {countries}"
                )


            else:


                print(
                    f"SKIP {cidr} {countries}"
                )



        except Exception as e:


            print(
                f"{cidr} failed: {e}"
            )



    #
    # Write US file
    #

    with open(
        US_CIDR_FILE,
        "w"
    ) as f:


        for cidr in us_prefixes:

            f.write(
                cidr + "\n"
            )



    print()

    print(
        "=============================="
    )

    print(
        f"Wrote {US_CIDR_FILE}"
    )

    print(
        f"US CIDRs: {len(us_prefixes)}"
    )

    print(
        "=============================="
    )



    #
    # Split
    #

    write_chunks(
        us_prefixes
    )


    reader.close()


    print(
        "\nDone."
    )



if __name__ == "__main__":

    main()
