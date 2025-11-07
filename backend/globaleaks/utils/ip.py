import ipaddress


def parse_csv_ip_ranges_to_ip_networks(ip_str):
    """Parse a list of IP addresses and/or CIDRs

    :param ip_str: the string of comma separated IP
    :return: the list of parsed IPs
    """
    # Handle empty input
    if not ip_str:
        return []

    # strip all white spaces
    ip_str = "".join(ip_str.split())

    ip_network_list = []

    for ip_network_str in ip_str.split(','):
        # We want to normalize to IPvXNetwork, so we can run in comparsions on
        # IP ranges for authentications. However, we may get IP addresses, CIDR
        # ranges, or garbage. Python does provide strict=True with the ipaddress
        # methods; however, it will accept any integer is which *not* what we want
        # so we need to handle this carefully.

        # If it has a /, we'll assume it's a CIDR address, otherwise, a raw IP
        if "/" in ip_network_str:
            ip_net_obj = ipaddress.ip_network(ip_network_str, strict=True)
            ip_network_list.append(ip_net_obj)
        else:
            # Let's try and see if we can work with this
            ip_addr_obj = ipaddress.ip_address(ip_network_str)

            # If we got here, it is, convert it to a proper /32 (or /128)
            cidr_len = ip_addr_obj.max_prefixlen
            ip_network = ipaddress.ip_network(ip_network_str + '/' + str(cidr_len))
            ip_network_list.append(ip_network)

    return ip_network_list


def check_ip(client_ip, ip_filter):
    try:
        ip_networks = parse_csv_ip_ranges_to_ip_networks(ip_filter)

        if isinstance(client_ip, bytes):
            client_ip = client_ip.decode()

        client_ip_obj = ipaddress.ip_address(client_ip)

        for ip_network in ip_networks:
            if client_ip_obj in ip_network:
                return True
    except:
        return False

    return False


def get_ip_identity(client_ip):
    ip = ipaddress.ip_address(client_ip)
    if ip.version == 4:
        return str(ip)  # full IPv4
    else:
        # For IPv6, use /64 subnet
        network = ipaddress.ip_network(client_ip + '/64', strict=False)
        return str(network.network_address) + '/64'
