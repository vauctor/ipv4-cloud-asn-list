import ipaddress
import requests
import os

ASN_FILE = "asn.txt"

OUTPUT_DIR = "output"

US_ASN_FILE = os.path.join(OUTPUT_DIR, "US_asn.txt")
MASTER_FILE = os.path.join(OUTPUT_DIR, "all_US_cidr_list.txt")

MAX_LINES = 5000


def normalize_asn(asn):
    asn = asn.strip().upper()

    if not asn.startswith("AS"):
        asn = "AS" + asn

    return asn


def get_asn_holder(asn):
    """
    Gets ASN organization name from RIPE Stat
    """

    asn_number = asn.replace("AS", "")

    url = (
        "https://stat.ripe.net/data/as-overview/"
        f"data.json?resource=AS{asn_number}"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    holder = (
        data
        .get("data", {})
        .get("holder", "")
    )

    print(f"{asn}: {holder}")

    return holder


def get_prefixes(asn):
    """
    Gets IPv4 prefixes from ASN
    """

    url = f"https://asn.ipinfo.app/api/text/list/{asn}"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    lines = response.text.splitlines()

    ipv4 = [
        line.strip()
        for line in lines
        if line.strip()
        and ":" not in line
    ]

    return ipv4


def cidr_key(cidr):
    try:
        return ipaddress.IPv4Network(
            cidr,
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
    # Identify US organizations
    #
    us_asns = []


    us_keywords = [
        "GOOGLE",
        "AMAZON",
        "MICROSOFT",
        "CLOUDFLARE",
        "META",
        "ORACLE",
        "DIGITALOCEAN",
        "FASTLY",
        "AKAMAI",
        "IBM",
        "VULTR",
        "LINODE",
        "HEWLETT",
        "HPE"
    ]


    print("\nChecking ASN owners...\n")


    for asn in asns:

        try:

            holder = get_asn_holder(asn)

            if any(
                keyword in holder.upper()
                for keyword in us_keywords
            ):

                us_asns.append(asn)


        except Exception as e:

            print(
                f"{asn} lookup failed: {e}"
            )


    #
    # Write US ASN list
    #
    with open(US_ASN_FILE, "w") as f:

        for asn in sorted(us_asns):
            f.write(asn + "\n")


    print(
        f"\nCreated {US_ASN_FILE}"
        f" ({len(us_asns)} ASNs)"
    )


    #
    # Pull CIDRs
    #
    all_prefixes = set()


    print("\nDownloading CIDRs...\n")


    for asn in us_asns:

        print(f"Processing {asn}")

        try:

            prefixes = get_prefixes(asn)

            print(
                f"  Found {len(prefixes)} IPv4 CIDRs"
            )

            all_prefixes.update(prefixes)


        except Exception as e:

            print(
                f"{asn} prefix lookup failed: {e}"
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
    with open(MASTER_FILE, "w") as f:

        for cidr in sorted_prefixes:
            f.write(cidr + "\n")


    print(
        f"\nCreated {MASTER_FILE}"
        f" ({len(sorted_prefixes)} CIDRs)"
    )


    #
    # Split into 5000 line files
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
            f"Created {filename}"
            f" ({len(chunk)} CIDRs)"
        )


    print("\nComplete.")



if __name__ == "__main__":
    main()
