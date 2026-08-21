import json
import tempfile
import unittest
from pathlib import Path

from surge_dae_dat.builder import build


class BuilderTests(unittest.TestCase):
    def test_local_build_writes_dat_and_manifest_mapping(self):
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as output_tmp:
            source = Path(source_tmp)
            (source / "Source/domainset").mkdir(parents=True)
            (source / "Source/non_ip").mkdir(parents=True)
            (source / "Source/ip").mkdir(parents=True)
            (source / "Source/domainset/reject.conf").write_text(".ads.example\n", encoding="utf-8")
            (source / "Source/non_ip/reject.conf").write_text("DOMAIN,exact.example\n", encoding="utf-8")
            (source / "Source/ip/reject.conf").write_text("IP-CIDR,192.0.2.0/24\n", encoding="utf-8")

            summary = build(Path(output_tmp), source_dir=source)
            manifest = json.loads((Path(output_tmp) / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(summary.domain_entries, 2)
            self.assertEqual(summary.ip_entries, 1)
            self.assertTrue((Path(output_tmp) / "surge-geosite.dat").stat().st_size > 0)
            tags = {entry["source"]: entry["tag"] for entry in manifest["entries"]}
            self.assertEqual(tags["Source/domainset/reject.conf"], "reject")
            self.assertEqual(tags["Source/non_ip/reject.conf"], "non-ip-reject")


if __name__ == "__main__":
    unittest.main()

