"""Small protobuf encoder for the V2Ray geodata messages used by dae.

The messages are deliberately encoded here instead of depending on a generated
protobuf module. The geodata schema is stable and the encoder only needs the
length-delimited and varint wire types used by GeoSiteList and GeoIPList.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Network, IPv6Network
from typing import Iterable


def _varint(value: int) -> bytes:
    if value < 0:
        value &= (1 << 64) - 1
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _field_bytes(number: int, value: bytes) -> bytes:
    return _varint((number << 3) | 2) + _varint(len(value)) + value


def _field_varint(number: int, value: int) -> bytes:
    return _varint(number << 3) + _varint(value)


@dataclass(frozen=True, order=True)
class Domain:
    """A V2Ray Domain message.

    type is 0=Plain, 1=Regex, 2=RootDomain, 3=Full.
    """

    type: int
    value: str

    def encode(self) -> bytes:
        # Enum zero is the protobuf default and need not be emitted. Emitting
        # it is valid too, but omitting it makes output smaller and canonical.
        result = bytearray()
        if self.type:
            result += _field_varint(1, self.type)
        result += _field_bytes(2, self.value.encode("utf-8"))
        return bytes(result)


@dataclass(frozen=True, order=True)
class GeoSite:
    tag: str
    domains: tuple[Domain, ...]

    def encode(self) -> bytes:
        result = bytearray(_field_bytes(1, self.tag.encode("utf-8")))
        for domain in self.domains:
            result += _field_bytes(2, domain.encode())
        return bytes(result)


@dataclass(frozen=True, order=True)
class Cidr:
    network: IPv4Network | IPv6Network

    def encode(self) -> bytes:
        result = bytearray(_field_bytes(1, self.network.network_address.packed))
        result += _field_varint(2, self.network.prefixlen)
        return bytes(result)


@dataclass(frozen=True, order=True)
class GeoIp:
    tag: str
    cidrs: tuple[Cidr, ...]

    def encode(self) -> bytes:
        result = bytearray(_field_bytes(1, self.tag.encode("utf-8")))
        for cidr in self.cidrs:
            result += _field_bytes(2, cidr.encode())
        return bytes(result)


def encode_geosite(entries: Iterable[GeoSite]) -> bytes:
    return b"".join(_field_bytes(1, entry.encode()) for entry in entries)


def encode_geoip(entries: Iterable[GeoIp]) -> bytes:
    return b"".join(_field_bytes(1, entry.encode()) for entry in entries)

