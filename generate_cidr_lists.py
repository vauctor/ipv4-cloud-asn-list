import ipaddress
import requests
import json
import time
import os


ASN_FILE = "asn.txt"

OUTPUT_DIR = "output"

IPINFO_TOKEN = os.environ.get("IPINFO_TOKEN")

BATCH_SIZE = 1000

ALL_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "all_cidr_list.txt"
)

US_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "US_cidr_list.txt"
)

NON_US_CA_PR_VI_CIDR_FILE = os.path.join(
    OUTPUT_DIR,
    "non_US_CA_PR_VI_cidr_list.txt"
)

EXCLUDED_COUNTRIES = {"US", "CA", "PR", "VI"}

CACHE_FILE = os.path.join(
    OUTPUT_DIR,
    "cidr_country_cache.json"
)


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
        json.dump(cache, f, indent=2)


# -------------------------
# ASN Prefix Lookup
# -------------------------

def get_prefixes(asn):

    url = f"https://asn.ipinfo.app/api/text/list/{asn}"

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

    return str(network.network_address)


# -------------------------
# IPinfo Lite Batch Lookup
# -------------------------

def get_countries_batch(ips):

    url = (
        "https://api.ipinfo.io/batch/lite"
        f"?token={IPINFO_TOKEN}"
    )

    headers = {
        "Accept": "application/json"
    }

    try:

        r = requests.post(
            url,
            json=ips,
            headers=headers,
            timeout=120
        )

        r.raise_for_status()

        return r.json()

    except Exception as e:

        print(f"Batch lookup failed: {e}")

        return {}


# -------------------------
# Main
# -------------------------

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    if not IPINFO_TOKEN:

        raise Exception(
            "Missing IPINFO_TOKEN GitHub secret"
        )

    cache = load_cache()

    print(
        f"Loaded {len(cache)} cached records"
    )

    # -------------------------
    # Load ASN List
    # -------------------------

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

    # -------------------------
    # Get CIDRs from ASNs
    # -------------------------

    all_prefixes = set()

    for asn in asns:

        print(
            f"Processing {asn}"
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

    # -------------------------
    # Sort CIDRs
    # -------------------------

    sorted_prefixes = sorted(
        all_prefixes,
        key=cidr_key
    )

    # -------------------------
    # Write Master CIDR File
    # -------------------------

    with open(ALL_CIDR_FILE, "w") as f:

        for cidr in sorted_prefixes:
            f.write(cidr + "\n")

    print(
        f"Wrote {ALL_CIDR_FILE}"
    )

    print(
        f"Total CIDRs: {len(sorted_prefixes)}"
    )

    # -------------------------
    # IPinfo Country Checks
    # -------------------------

    print()
    print("Starting IPinfo batch lookups...")
    print()

    us_prefixes = []
    non_us_ca_pr_vi_prefixes = []

    ip_to_cidr = {}
    ips = []

    for cidr in sorted_prefixes:

        ip = cidr_to_ip(cidr)

        ips.append(ip)
        ip_to_cidr[ip] = cidr

    total_batches = (
        len(ips) + BATCH_SIZE - 1
    ) // BATCH_SIZE

    for batch_number, start in enumerate(
        range(0, len(ips), BATCH_SIZE),
        start=1
    ):

        batch = ips[
            start:start + BATCH_SIZE
        ]

        print(
            f"Batch {batch_number}/{total_batches} "
            f"({len(batch)} IPs)"
        )

        results = get_countries_batch(batch)

        for ip, data in results.items():

            cidr = ip_to_cidr.get(ip)

            if not cidr:
                continue

            country = data.get("country_code")

            old_country = None

            if cidr in cache:
                old_country = cache[cidr].get("country")

            if old_country != country:

                print(
                    f"CHANGE {cidr}: "
                    f"{old_country} -> {country}"
                )

            # Update cache

            cache[cidr] = {
                "country": country,
                "checked": time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            # Categorize CIDRs

            if country == "US":

                us_prefixes.append(cidr)

            elif (
                country is not None
                and country not in EXCLUDED_COUNTRIES
            ):

                non_us_ca_pr_vi_prefixes.append(cidr)

        # Small pause between batches

        time.sleep(1)

    # -------------------------
    # Save Updated Cache
    # -------------------------

    save_cache(cache)

    print(
        f"Saved {len(cache)} cache records"
    )

    # -------------------------
    # Write US CIDR List
    # -------------------------

    us_prefixes = sorted(
        us_prefixes,
        key=cidr_key
    )

    with open(US_CIDR_FILE, "w") as f:

        for cidr in us_prefixes:
            f.write(cidr + "\n")

    print()
    print("==============================")
    print(f"Wrote {US_CIDR_FILE}")
    print(f"US CIDRs: {len(us_prefixes)}")
    print("==============================")

    # -------------------------
    # Write Non-US/CA/PR/VI CIDR List
    # -------------------------

    non_us_ca_pr_vi_prefixes = sorted(
        non_us_ca_pr_vi_prefixes,
        key=cidr_key
    )

    with open(NON_US_CA_PR_VI_CIDR_FILE, "w") as f:

        for cidr in non_us_ca_pr_vi_prefixes:
            f.write(cidr + "\n")

    print(
        f"Wrote {NON_US_CA_PR_VI_CIDR_FILE}"
    )

    print(
        "Non-US/CA/PR/VI CIDRs: "
        f"{len(non_us_ca_pr_vi_prefixes)}"
    )

    print()
    print("Done.")


if __name__ == "__main__":
    main()
