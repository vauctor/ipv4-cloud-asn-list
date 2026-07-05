import requests
import os
import ipaddress

ASN_FILE = "asn.txt"
OUTPUT_FILE = "output/cidr.txt"


def get_prefixes(asn):
    url = f"https://asn.ipinfo.app/api/text/list/{asn}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()

    lines = r.text.splitlines()

    # IPv4 only filter
    ipv4 = [x.strip() for x in lines if x and ":" not in x]

    return ipv4


def cidr_key(cidr):
    try:
        return ipaddress.IPv4Network(cidr.strip(), strict=False)
    except Exception:
        # fallback so bad data never breaks the pipeline
        return ipaddress.IPv4Network("0.0.0.0/0")


def main():
    all_prefixes = set()

    # ensure output folder exists
    os.makedirs("output", exist_ok=True)

    # read ASN list safely
    with open(ASN_FILE, "r") as f:
        asns = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    for asn in asns:
        print(f"Processing {asn}")
        try:
            prefixes = get_prefixes(asn)
            all_prefixes.update(prefixes)
        except Exception as e:
            print(f"Failed {asn}: {e}")

    # IPv4-aware sorting
    sorted_prefixes = sorted(all_prefixes, key=cidr_key)

    # write output
    with open(OUTPUT_FILE, "w") as f:
        for p in sorted_prefixes:
            f.write(p + "\n")

    print(f"Done. Total IPv4 CIDRs: {len(sorted_prefixes)}")


if __name__ == "__main__":
    main()
