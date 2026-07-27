import ipaddress
import os
import requests

ASN_FILE = "asn.txt"

OUTPUT_DIR = "output"

US_ASN_FILE = os.path.join(OUTPUT_DIR, "US_asn.txt")
MASTER_FILE = os.path.join(OUTPUT_DIR, "all_US_cidr_list.txt")

MAX_LINES = 5000


def normalize_asn(asn):
    """
    Ensures ASN is formatted as AS12345
    """
    asn = asn.strip().upper()

    if not asn.startswith("AS"):
        asn = "AS" + asn

    return asn


def get_country(asn):
    """
    Gets ASN country from BGPView
    """

    asn_number = asn.replace("AS", "")

    url = f"https://api.bgpview.io/asn/{asn_number}"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    asn_data = data.get("data", {})

    country = asn_data.get("country_code")

    print(f"{asn} country: {country}")

    return country


def get_prefixes(asn):
    """
    Gets IPv4 prefixes from ipinfo ASN API
    """

    url = f"https://asn.ipinfo.app/api/text/list/{asn}"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    lines = response.text.splitlines()

    ipv4 = [
        line.strip()
        for line in lines
        if line.strip() and ":" not in line
    ]

    return ipv4


def cidr_key(cidr):
    """
    Sort IPv4 CIDRs properly
    """

    try:
        return ipaddress.IPv4Network(
            cidr.strip(),
            strict=False
        )

    except Exception:
        return ipaddress.IPv4Network("0.0.0.0/0")


def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    #
    # Read ASN list
    #
    with open(ASN_FILE, "r") as f:
        asns = [
            normalize_asn(line)
            for line in f
            if line.strip()
            and not line.startswith("#")
        ]


    print(f"Loaded {len(asns)} ASNs")


    #
    # Find US ASNs
    #
    us_asns = []

    print("\nChecking ASN countries...\n")


    for asn in asns:

        try:

            country = get_country(asn)

            if country and country.upper() == "US":
                us_asns.append(asn)

        except Exception as e:
            print(f"{asn} lookup failed: {e}")


    #
    # Write US ASN list
    #
    with open(US_ASN_FILE, "w") as f:

        for asn in sorted(us_asns):
            f.write(asn + "\n")


    print(
        f"\nCreated {US_ASN_FILE} "
        f"with {len(us_asns)} ASNs"
    )


    #
    # Get CIDRs
    #
    all_prefixes = set()


    print("\nDownloading IPv4 prefixes...\n")


    for asn in us_asns:

        print(f"Processing {asn}")

        try:

            prefixes = get_prefixes(asn)

            print(
                f"  Found {len(prefixes)} IPv4 prefixes"
            )

            all_prefixes.update(prefixes)


        except Exception as e:

            print(
                f"Failed getting prefixes for {asn}: {e}"
            )


    #
    # Sort CIDRs
    #
    sorted_prefixes = sorted(
        all_prefixes,
        key=cidr_key
    )


    #
    # Write master file
    #
    with open(MASTER_FILE, "w") as f:

        for cidr in sorted_prefixes:
            f.write(cidr + "\n")


    print(
        f"\nCreated {MASTER_FILE} "
        f"with {len(sorted_prefixes)} CIDRs"
    )


    #
    # Split files
    #
    chunks = [
        sorted_prefixes[i:i + MAX_LINES]
        for i in range(
            0,
            len(sorted_prefixes),
            MAX_LINES
        )
    ]


    for index, chunk in enumerate(chunks, start=1):

        filename = os.path.join(
            OUTPUT_DIR,
            f"cidr_list_{index}.txt"
        )

        with open(filename, "w") as f:

            for cidr in chunk:
                f.write(cidr + "\n")


        print(
            f"Created {filename} "
            f"({len(chunk)} entries)"
        )


    print("\nCompleted successfully.")



if __name__ == "__main__":
    main()
