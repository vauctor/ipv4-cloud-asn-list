import ipaddress
import requests
import os


ASN_FILE = "asn.txt"


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
        return ipaddress.IPv4Network("0.0.0.0/0")


def main():
    all_prefixes = set()

    os.makedirs("output", exist_ok=True)

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

    sorted_prefixes = sorted(all_prefixes, key=cidr_key)

    # -------------------------------
    # SPLIT INTO 25K FILES
    # -------------------------------
    MAX_LINES = 25000

    chunks = [
        sorted_prefixes[i:i + MAX_LINES]
        for i in range(0, len(sorted_prefixes), MAX_LINES)
    ]

    for idx, chunk in enumerate(chunks, start=1):
        out_file = f"output/cidr_lists_{idx}.txt"

        with open(out_file, "w") as f:
            for cidr in chunk:
                f.write(cidr + "\n")

        print(f"Wrote {out_file} with {len(chunk)} entries")

    print(f"Done. Total CIDRs: {len(sorted_prefixes)}")


if __name__ == "__main__":
    main()
