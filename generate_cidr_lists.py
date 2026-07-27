import ipaddress
import requests
import os


ASN_FILE = "asn.txt"

OUTPUT_DIR = "output"
US_ASN_FILE = os.path.join(OUTPUT_DIR, "US_asn.txt")
MASTER_FILE = os.path.join(OUTPUT_DIR, "all_US_cidr_list.txt")
MAX_LINES = 5000


def get_country(asn):
    """
    Returns the country code for an ASN using the BGPView API.
    Example input:
        AS15169
        15169
    Returns:
        US
    """
    asn_number = asn.upper().replace("AS", "")

    url = f"https://api.bgpview.io/asn/{asn_number}"

    r = requests.get(url, timeout=20)
    r.raise_for_status()

    data = r.json()

    return data["data"]["country_code"]


def get_prefixes(asn):
    """
    Downloads IPv4 prefixes from ipinfo.
    """
    url = f"https://asn.ipinfo.app/api/text/list/{asn}"

    r = requests.get(url, timeout=20)
    r.raise_for_status()

    lines = r.text.splitlines()

    return [x.strip() for x in lines if x.strip() and ":" not in x]


def cidr_key(cidr):
    try:
        return ipaddress.IPv4Network(cidr, strict=False)
    except Exception:
        return ipaddress.IPv4Network("0.0.0.0/0")


def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(ASN_FILE, "r") as f:
        asns = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    us_asns = []
    all_prefixes = set()

    print("Determining ASN countries...")

    for asn in asns:
        try:
            country = get_country(asn)

            print(f"{asn} -> {country}")

            if country == "US":
                us_asns.append(asn)

        except Exception as e:
            print(f"Failed country lookup for {asn}: {e}")

    # Write US ASN list
    with open(US_ASN_FILE, "w") as f:
        for asn in sorted(us_asns):
            f.write(asn + "\n")

    print(f"\nWrote {US_ASN_FILE} ({len(us_asns)} ASNs)")

    print("\nDownloading IPv4 prefixes...")

    for asn in us_asns:
        print(f"Processing {asn}")

        try:
            prefixes = get_prefixes(asn)
            all_prefixes.update(prefixes)

        except Exception as e:
            print(f"Failed {asn}: {e}")

    sorted_prefixes = sorted(all_prefixes, key=cidr_key)

    with open(MASTER_FILE, "w") as f:
        for prefix in sorted_prefixes:
            f.write(prefix + "\n")

    print(f"\nWrote {MASTER_FILE} ({len(sorted_prefixes)} prefixes)")

    chunks = [
        sorted_prefixes[i:i + MAX_LINES]
        for i in range(0, len(sorted_prefixes), MAX_LINES)
    ]

    for idx, chunk in enumerate(chunks, start=1):
        out_file = os.path.join(OUTPUT_DIR, f"cidr_list_{idx}.txt")

        with open(out_file, "w") as f:
            for prefix in chunk:
                f.write(prefix + "\n")

        print(f"Wrote {out_file} ({len(chunk)} prefixes)")

    print("\nDone.")


if __name__ == "__main__":
    main()
