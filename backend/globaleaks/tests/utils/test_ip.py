from twisted.trial import unittest
import ipaddress
from globaleaks.utils import ip


class TestIPUtils(unittest.TestCase):
    def test_check_ip(self):
        ip_str = "192.168.1.1,10.0.0.0/8,::1,2001:db8::/32"
        self.assertTrue(ip.check_ip("192.168.1.1", ip_str))

        ip_str = "192.168.1.2,10.0.0.0/8,::1,2001:db8::/32"
        self.assertFalse(ip.check_ip("192.168.1.1", ip_str))

        ip_str = "192.168.1.2,10.0.0.0/8,::1,2001:db8::/32"
        self.assertTrue(ip.check_ip("10.0.0.1", ip_str))

        ip_str = "192.168.1.2, 10.0.0.0/8, ::1,2001:db8::/32"
        self.assertTrue(ip.check_ip("2001:db8::2", ip_str))

    def test_check_ip_invalid_ip(self):
        """Test with an invalid IP address."""
        ip_str = "192.168.1.1,10.0.0.0/8"
        self.assertFalse(ip.check_ip("999.999.999.999", ip_str))

    def test_check_ip_invalid_filter(self):
        """Test with an invalid IP filter."""
        ip_str = "invalid_data"
        self.assertFalse(ip.check_ip("10.0.0.1", ip_str))

    def test_check_ip_empty_filter(self):
        """Test with an empty IP filter."""
        ip_str = ""
        self.assertFalse(ip.check_ip("10.0.0.1", ip_str))

    def test_check_ip_bytes_input(self):
        """Test with client IP as bytes."""
        ip_str = "10.0.0.0/8"
        self.assertTrue(ip.check_ip(b"10.0.0.1", ip_str))

    def test_check_ip_ipv6(self):
        """Test with IPv6 addresses."""
        ip_str = "::1,2001:db8::/32"
        self.assertTrue(ip.check_ip("2001:db8::2", ip_str))
        self.assertFalse(ip.check_ip("2001:dead::1", ip_str))

    def test_parse_csv_ip_ranges_to_ip_networks(self):
        """Test parsing valid IP and CIDR ranges."""
        ip_str = "192.168.1.1,10.0.0.0/8,::1,2001:db8::/32"
        expected = [
            ipaddress.ip_network("192.168.1.1/32"),
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("::1/128"),
            ipaddress.ip_network("2001:db8::/32")
        ]

        self.assertEqual(ip.parse_csv_ip_ranges_to_ip_networks(ip_str), expected)

    def test_parse_csv_ip_ranges_invalid_entries(self):
        """Test parsing invalid IPs and CIDR ranges."""
        invalid_ip_str = "invalid,300.300.300.300,10.0.0.1/33"
        with self.assertRaises(ValueError):
            ip.parse_csv_ip_ranges_to_ip_networks(invalid_ip_str)

    def test_parse_csv_ip_ranges_empty(self):
        """Test parsing an empty input."""
        self.assertEqual(ip.parse_csv_ip_ranges_to_ip_networks(""), [])

    def test_get_ip_identity(self):
        test = '192.168.1.42'
        expected = '192.168.1.42'
        result = ip.get_ip_identity(test)
        self.assertEqual(result, expected)

        test = '2001:0db8:85a3:0000:0000:8a2e:0370:7334'
        expected = '2001:db8:85a3::/64'  # normalized and /64 suffix
        result = ip.get_ip_identity(test)
        self.assertEqual(result, expected)

        test = '2001:db8:85a3::8a2e:370:7334'
        expected = '2001:db8:85a3::/64'
        result = ip.get_ip_identity(test)
        self.assertEqual(result, expected)

        test = '2001:db8:85a3::1'
        result = ip.get_ip_identity(test)
        self.assertEqual(result, '2001:db8:85a3::/64')
        self.assertEqual(result, ip.get_ip_identity('2001:db8:85a3::abcd'))

        invalid_ip = '300.300.300.300'
        with self.assertRaises(ValueError):
            ip.get_ip_identity(invalid_ip)
