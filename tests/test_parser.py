import ipaddress
import unittest

from surge_dae_dat.parser import parse_domainset, parse_ruleset


class ParserTests(unittest.TestCase):
    def test_domainset_maps_suffix_and_full(self):
        result = parse_domainset("# comment\n.Example.COM.\nexact.example.com\n.Example.COM")
        self.assertEqual([(d.type, d.value) for d in result.domains], [(2, "example.com"), (3, "exact.example.com")])

    def test_ruleset_maps_domains_wildcards_and_cidr(self):
        result = parse_ruleset(
            "DOMAIN,Example.COM\nDOMAIN-SUFFIX,foo.example\n"
            "DOMAIN-KEYWORD,tracker\nDOMAIN-WILDCARD,*.ads?.example\n"
            "IP-CIDR,192.0.2.5/24,no-resolve\nIP-CIDR6,2001:db8::1/64"
        )
        self.assertEqual([(d.type, d.value) for d in result.domains[:3]], [
            (3, "example.com"), (2, "foo.example"), (0, "tracker")
        ])
        self.assertEqual(result.domains[3].type, 1)
        self.assertEqual(str(result.cidrs[0].network), "192.0.2.0/24")
        self.assertEqual(str(result.cidrs[1].network), "2001:db8::/64")

    def test_unsupported_rules_are_reported(self):
        result = parse_ruleset("URL-REGEX,^https://example.com/ads\nGEOIP,CN")
        self.assertEqual(result.domains, [])
        self.assertTrue(any("URL-REGEX" in warning for warning in result.warnings))
        self.assertTrue(any("GEOIP" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()

