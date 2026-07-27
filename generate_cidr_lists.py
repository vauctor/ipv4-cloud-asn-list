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


def get_prefixes(asn):
    """
    Get IPv4 prefixes from ASN
    """

    url = f"https://asn.ipinfo.app/api/text/list/{asn}"

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    lines = r.text.splitlines()

    ipv4 = [
        x.strip()
        for x in lines
        if x.strip()
        and ":" not in x
    ]

    return ipv4


def cidr_key(cidr):
    """
    Sort CIDRs properly
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


def cidr_to_ip(cidr):
    """
    Get first IP in CIDR
    """

    network = ipaddress.IPv4Network(
        cidr,
        strict=False
    )

    return str(network.network_address)


def get_country(ip):
    """
    ipinfo.io lookup
    """

    url = f"https://ipinfo.io/{ip}"

    r = requests.get(
        url,
        timeout=20
    )

    r.raise_for_status()

    data = r.json()

    return data.get("country")


def write_chunks(prefixes, prefix_name):

    chunks = [
        prefixes[i:i + MAX_LINES]
        for i in range(
            0,
            len(prefixes),
            MAX_LINES
        )
    ]

    for idx, chunk in enumerate(
        chunks,
        start=1
    ):

        filename = os.path.join(
            OUTPUT_DIR,
            f"{prefix_name}_{idx}.txt"
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
    # Read ASNs
    #
    with open(ASN_FILE, "r") as f:

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
    # Get all CIDRs
    #
    all_prefixes = set()


    for asn in asns:

        print(
            f"Processing {asn}"
        )

        try:

            prefixes = get_prefixes(asn)

            print(
                f"  Found {len(prefixes)} IPv4 CIDRs"
            )

            all_prefixes.update(prefixes)


        except Exception as e:

            print(
                f"Failed {asn}: {e}"
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
            f.write(cidr + "\n")


    print(
        f"\nWrote {ALL_CIDR_FILE}"
        f" ({len(sorted_prefixes)} entries)"
    )


    #
    # Check US locations
    #
    print(
        "\nChecking CIDRs against ipinfo.io..."
    )


    us_prefixes = []


    for count, cidr in enumerate(
        sorted_prefixes,
        start=1
    ):

        try:

            ip = cidr_to_ip(cidr)

            country = get_country(ip)


            print(
                f"{count}/{len(sorted_prefixes)} "
                f"{cidr} -> {country}"
            )


            if country == "US":
                us_prefixes.append(cidr)


            # slow down to avoid rate limits
            time.sleep(0.5)


        except Exception as e:

            print(
                f"Failed {cidr}: {e}"
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
