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

REQUEST_DELAY = 0.5


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

    return [
        x.strip()
        for x in r.text.splitlines()
        if x.strip()
        and ":" not in x
    ]


def cidr_key(cidr):
    """
    Sort CIDRs properly
    """

    return ipaddress.IPv4Network(
        cidr.strip(),
        strict=False
    )


def sample_ips(cidr):
    """
    Pick sample IPs inside CIDR
    """

    network = ipaddress.IPv4Network(
        cidr,
        strict=False
    )

    total = network.num_addresses


    # Small blocks: check all IPs
    if total <= 16:

        return [
            str(ip)
            for ip in network
        ]


    # Larger blocks: sample first/middle/last
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
    # Pull CIDRs
    #

    all_prefixes = set()


    for asn in asns:

        print(
            f"\nProcessing {asn}"
        )


        try:

            prefixes = get_prefixes(asn)

            print(
                f"Found {len(prefixes)} IPv4 CIDRs"
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
    # Save full list
    #

    with open(
        ALL_CIDR_FILE,
        "w"
    ) as f:

        for cidr in sorted_prefixes:
            f.write(cidr + "\n")


    print(
        f"\nCreated {ALL_CIDR_FILE}"
    )

    print(
        f"Total CIDRs: {len(sorted_prefixes)}"
    )


    #
    # Check countries
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
            # KEEP if ANY sample is US
            #

            if "US" in countries:

                us_prefixes.append(cidr)

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
    # Save US list
    #

    with open(
        US_CIDR_FILE,
        "w"
    ) as f:

        for cidr in us_prefixes:
            f.write(cidr + "\n")


    print(
        "\n===================="
    )

    print(
        f"Created {US_CIDR_FILE}"
    )

    print(
        f"US CIDRs: {len(us_prefixes)}"
    )

    print(
        "===================="
    )


    #
    # Split files
    #

    write_chunks(
        us_prefixes
    )


    print(
        "\nDone."
    )


if __name__ == "__main__":
    main()
