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

# Delay between ipinfo requests
REQUEST_DELAY = 0.5


def get_prefixes(asn):
    """
    Get IPv4 prefixes announced by ASN
    """

    url = f"https://asn.ipinfo.app/api/text/list/{asn}"

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    lines = r.text.splitlines()

    return [
        x.strip()
        for x in lines
        if x.strip()
        and ":" not in x
    ]


def cidr_key(cidr):
    """
    Sort CIDRs correctly
    """

    try:
        return ipaddress.IPv4Network(
            cidr.strip(),
            strict=False
        )

    except Exception:
        return ipaddress.IPv4Network(
            "0.0.0.0/0"
        )


def sample_ips(cidr):
    """
    Select IPs to test inside CIDR
    """

    network = ipaddress.IPv4Network(
        cidr,
        strict=False
    )

    total = network.num_addresses

    # Small networks: check all
    if total <= 16:

        return [
            str(ip)
            for ip in network
        ]


    return [
        str(network.network_address),
        str(
            network.network_address +
            int(total / 2)
        ),
        str(network.broadcast_address)
    ]


def get_country(ip):
    """
    Query ipinfo.io
    """

    url = f"https://ipinfo.io/{ip}"

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    data = r.json()

    return data.get("country")


def write_chunks(prefixes, name):

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
            f"{name}_{index}.txt"
        )

        with open(
            filename,
            "w"
        ) as f:

            for cidr in chunk:
                f.write(cidr + "\n")


        print(
            f"Wrote {filename} "
            f"({len(chunk)} entries)"
        )


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
    # Get CIDRs from ASNs
    #
    all_prefixes = set()


    for asn in asns:

        print(
            f"Processing {asn}"
        )

        try:

            prefixes = get_prefixes(asn)

            print(
                f"  Found {len(prefixes)} IPv4 prefixes"
            )

            all_prefixes.update(prefixes)


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
    # Write full CIDR list
    #
    with open(
        ALL_CIDR_FILE,
        "w"
    ) as f:

        for cidr in sorted_prefixes:
            f.write(cidr + "\n")


    print(
        f"Wrote {ALL_CIDR_FILE}"
        f" ({len(sorted_prefixes)} entries)"
    )


    #
    # Check US location
    #
    us_prefixes = []


    print(
        "\nChecking CIDRs with ipinfo.io...\n"
    )


    for index, cidr in enumerate(
        sorted_prefixes,
        start=1
    ):

        try:

            samples = sample_ips(cidr)

            countries = []


            for ip in samples:

                country = get_country(ip)

                countries.append(country)

                print(
                    f"{index}/{len(sorted_prefixes)} "
                    f"{cidr} "
                    f"{ip} -> {country}"
                )

                time.sleep(
                    REQUEST_DELAY
                )


            #
            # Require ALL samples to be US
            #
            if all(
                c == "US"
                for c in countries
            ):

                us_prefixes.append(cidr)

                print(
                    f"KEEP {cidr}"
                )

            else:

                print(
                    f"SKIP {cidr}"
                )


        except Exception as e:

            print(
                f"{cidr} failed: {e}"
            )


    #
    # Write US CIDRs
    #
    with open(
        US_CIDR_FILE,
        "w"
    ) as f:

        for cidr in us_prefixes:
            f.write(cidr + "\n")


    print(
        f"\nWrote {US_CIDR_FILE}"
        f" ({len(us_prefixes)} entries)"
    )


    #
    # Split US CIDRs
    #
    write_chunks(
        us_prefixes,
        "US_cidr_list"
    )


    print(
        "\nDone."
    )


if __name__ == "__main__":
    main()
