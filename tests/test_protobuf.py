import unittest

from surge_dae_dat.protobuf import Domain, GeoIp, GeoSite, Cidr, encode_geoip, encode_geosite


def read_varint(data, offset):
    value = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 128:
            return value, offset
        shift += 7


def read_entries(data):
    entries = []
    offset = 0
    while offset < len(data):
        key, offset = read_varint(data, offset)
        length, offset = read_varint(data, offset)
        entries.append(data[offset:offset + length])
        offset += length
    return entries


class ProtobufTests(unittest.TestCase):
    def test_geosite_is_length_delimited_entry_list(self):
        data = encode_geosite([GeoSite("reject", (Domain(2, "example.com"),))])
        self.assertEqual(len(read_entries(data)), 1)
        self.assertIn(b"reject", data)
        self.assertIn(b"example.com", data)

    def test_geoip_contains_packed_address_and_prefix(self):
        network = __import__("ipaddress").ip_network("192.0.2.0/24")
        data = encode_geoip([GeoIp("test", (Cidr(network),))])
        self.assertIn(b"test", data)
        self.assertIn(network.network_address.packed, data)


if __name__ == "__main__":
    unittest.main()

