import ipaddress
import requests
import json
import time
import os


ASN_FILE = "asn.txt"
OUTPUT_DIR = "output"
IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN")

ALL_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "all_cidr_list.txt"
)

US_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "all_US_cidr_list.txt"
)

CACHE_FILE = os.path.join(
    OUTPUT_DIR,
    "cidr_country_cache.json"
)

MAX_LINES = 5000

REQUEST_DELAY = 1

MAX_RETRIES = 3



# -------------------------
# Cache Functions
# -------------------------

def load_cache():

    if os.path.exists(CACHE_FILE):

        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    return {}



def save_cache(cache):

    with open(CACHE_FILE, "w") as f:

        json.dump(
            cache,
            f,
            indent=2
        )



# -------------------------
# ASN Prefix Lookup
# -------------------------

def get_prefixes(asn):

    url = (
        f"https://asn.ipinfo.app/api/text/list/{asn}"
    )

    r = requests.get(
        url,
        timeout=30
    )

    r.raise_for_status()


    return [

        x.strip()

        for x in r.text.splitlines()

        if x.strip()
        and ":" not in x

    ]



# -------------------------
# CIDR Sorting
# -------------------------

def cidr_key(cidr):

    return ipaddress.IPv4Network(
        cidr,
        strict=False
    )



# -------------------------
# First IP in CIDR
# -------------------------

def cidr_to_ip(cidr):

    network = ipaddress.IPv4Network(
        cidr,
        strict=False
    )

    return str(
        network.network_address
    )



# -------------------------
# ipinfo Lookup
# -------------------------

# -------------------------
# IPinfo Lite Lookup
# -------------------------

def get_country(ip):

    url = (
        f"https://api.ipinfo.io/lite/{ip}"
        f"?token={IPINFO_TOKEN}"
    )


    headers = {

        "User-Agent": "Mozilla/5.0",

        "Accept": "application/json"

    }


    for attempt in range(MAX_RETRIES):

        try:

            r = requests.get(
                url,
                headers=headers,
                timeout=20
            )


            r.raise_for_status()


            data = r.json()


            return data.get(
                "country_code"
            )


        except Exception as e:

            print(
                f"{ip} lookup failed: {e}"
            )

            time.sleep(5)



    return None


# -------------------------
# Split ALL CIDRs
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
            f"cidr_list_{index}.txt"
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


    cache = load_cache()


    print(
        f"Loaded {len(cache)} cached CIDRs"
    )



    # Load ASNs

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



    # Collect CIDRs

    all_prefixes = set()



    for asn in asns:


        print(
            f"Processing {asn}"
        )


        try:

            prefixes = get_prefixes(
                asn
            )


            print(
                f"Found {len(prefixes)} IPv4 CIDRs"
            )


            all_prefixes.update(
                prefixes
            )


        except Exception as e:


            print(
                f"{asn} failed: {e}"
            )



    # Sort CIDRs

    sorted_prefixes = sorted(
        all_prefixes,
        key=cidr_key
    )



    # Write master list

    with open(
        ALL_CIDR_FILE,
        "w"
    ) as f:


        for cidr in sorted_prefixes:

            f.write(
                cidr + "\n"
            )


    print(
        f"Wrote {ALL_CIDR_FILE}"
    )


    print(
        f"Total CIDRs: {len(sorted_prefixes)}"
    )



    # Split ALL CIDRs

    write_chunks(
        sorted_prefixes
    )



    # Check countries

    us_prefixes = []


    print()
    print(
        "Starting country lookups..."
    )
    print()



    for count, cidr in enumerate(
        sorted_prefixes,
        start=1
    ):


        ip = cidr_to_ip(
            cidr
        )


        if cidr in cache:


            country = cache[cidr]["country"]


            print(
                f"CACHE {count}/{len(sorted_prefixes)} "
                f"{cidr} -> {country}"
            )


        else:


            print(
                f"LOOKUP {count}/{len(sorted_prefixes)} "
                f"{cidr} -> {ip}"
            )


            country = get_country(
                ip
            )


            cache[cidr] = {

                "country": country,

                "checked": time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            }


            save_cache(
                cache
            )


            time.sleep(
                REQUEST_DELAY
            )



        if country == "US":

            us_prefixes.append(
                cidr
            )



    # Write US only list

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


    print(
        "Done."
    )



if __name__ == "__main__":

    main()
