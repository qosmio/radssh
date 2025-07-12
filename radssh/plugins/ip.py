#
# Copyright (c) 2014, 2016, 2018, 2020 LexisNexis Risk Data Management Inc.
#
# This file is part of the RadSSH software package.
#
# RadSSH is free software, released under the Revised BSD License.
# You are permitted to use, modify, and redsitribute this software
# according to the Revised BSD License, a copy of which should be
# included with the distribution as file LICENSE.txt
#

"""IP Lookup Plugin"""

import ipaddress

# Lookup function for plugins
# Return an iterator if we accept responsibility, or None to pass


# add static hints
def lookup(name: str):
    """Handle IPNetwork and IPGlob (and IPAddress) notation"""
    # Try as single IP address first
    try:
        ip = ipaddress.ip_address(name)
        return __generator([ip])
    except ValueError:
        pass

    # Try as network/subnet
    try:
        network = ipaddress.ip_network(name, strict=False)
        return __generator(
            network.hosts() if network.num_addresses > 1 else [network.network_address]
        )
    except ValueError:
        pass

    # Try as glob pattern - expand common patterns
    if "*" in name or "?" in name:
        try:
            # For glob patterns, we'll generate a basic range
            # This is a simplified implementation compared to netaddr.IPGlob
            parts = name.split(".")
            if len(parts) == 4:
                # Handle IPv4 glob patterns
                result = []
                ranges = []
                for part in parts:
                    if "*" in part:
                        ranges.append(range(0, 256))
                    elif "?" in part:
                        # Simple case: single digit wildcard
                        if len(part) == 1:
                            ranges.append(range(0, 10))
                        else:
                            ranges.append([int(part.replace("?", "0"))])
                    else:
                        try:
                            ranges.append([int(part)])
                        except ValueError:
                            return None

                # Generate all combinations (limited to avoid excessive memory usage)
                if any(len(r) > 16 for r in ranges):
                    return None  # Too many combinations

                for a in ranges[0]:
                    for b in ranges[1]:
                        for c in ranges[2]:
                            for d in ranges[3]:
                                try:
                                    ip = ipaddress.IPv4Address(f"{a}.{b}.{c}.{d}")
                                    result.append(ip)
                                except ValueError:
                                    pass
                if result:
                    return __generator(result)
        except Exception:
            pass

    return None


def __generator(x: list[ipaddress.IPv4Address | ipaddress.IPv6Address]):
    """Pass back 3-tuple (label, host, socket) - socket is None to defer actual connection til later"""
    for item in x:
        yield (item, str(item), None)
