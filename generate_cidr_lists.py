import ipaddress
import requests
import time
import os


ASN_FILE = "asn.txt"

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

REQUEST_DELAY = 0.25

MAX_RETRIES = 5


# -------------------------
# Get ASN prefixes
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
# Sort CIDRs
# -------------------------

def cidr_key(cidr):

    return ipaddress.IPv4Network(
        cidr,
        strict=False
    )



# -------------------------
# Get first IP in CIDR
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
# ipinfo lookup
# -------------------------

def get_country(ip):

    url = (
        f"https://ipinfo.io/{ip}"
    )


    for attempt in range(MAX_RETRIES):

        try:

            r = requests.get(
                url,
                timeout=20
            )


            if r.status_code == 429:

                wait = (
                    5 * (attempt + 1)
                )

                print(
                    f"Rate limited. "
                    f"Sleeping {wait}s"
                )

                time.sleep(
                    wait
                )

                continue


            r.raise_for_status()


            data = r.json()


            return data.get(
                "country"
            )


        except Exception as e:


            if attempt == MAX_RETRIES - 1:

                print(
                    f"{ip} lookup failed: {e}"
                )

                return None


            time.sleep(3)



# -------------------------
# Split files
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
    # Load ASN list
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
    # Collect CIDRs
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
                f"Found {len(prefixes)} IPv4 CIDRs"
            )


            all_prefixes.update(
                prefixes
            )


        except Exception as e:


            print(
                f"{asn} failed: {e}"
            )



    #
    # Sort
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
    # Filter US
    #

    us_prefixes = []


    print(
        "\nChecking IP locations..."
    )


    for index, cidr in enumerate(
        sorted_prefixes,
        start=1
    ):


        ip = cidr_to_ip(
            cidr
        )


        country = get_country(
            ip
        )


        print(
            f"{index}/{len(sorted_prefixes)} "
            f"{cidr} -> {ip} -> {country}"
        )


        if country == "US":

            us_prefixes.append(
                cidr
            )


        time.sleep(
            REQUEST_DELAY
        )



    #
    # Write US CIDRs
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
        "======================="
    )

    print(
        f"Wrote {US_CIDR_FILE}"
    )

    print(
        f"US CIDRs: {len(us_prefixes)}"
    )

    print(
        "======================="
    )


    #
    # Split
    #

    write_chunks(
        us_prefixes
    )


    print(
        "Done."
    )



if __name__ == "__main__":

    main()
