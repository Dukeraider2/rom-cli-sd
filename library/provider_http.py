"""Origin-scoped HTTP. Connect to a checked address, retaining the TLS hostname."""
import http.client
import ipaddress
import re
import socket
import ssl
from contextlib import contextmanager
from urllib.parse import urljoin, urlsplit, unquote
from .transfer import origin


class Network:
    def __init__(self, mirror=None, allow_private=False):
        self.mirror = mirror.rstrip("/")+"/" if mirror else None
        self.private = allow_private is True
        if mirror:
            self.check("mirror", self.mirror)

    def check(self, provider, url):
        scheme, host, port = origin(url)
        parts = urlsplit(url)
        if parts.fragment or len(url)>4096 or any(ord(c)<32 for c in url):
            raise ValueError("invalid source URL")
        if provider == "archive":
            if scheme!="https" or port not in (None,443) or not (host=="archive.org" or host.endswith(".archive.org")):
                raise ValueError("unexpected Archive origin")
        elif provider == "mirror" and self.mirror:
            path = unquote(parts.path)
            if (origin(self.mirror)!=origin(url) or not path.startswith(unquote(urlsplit(self.mirror).path))
                    or any(chunk in (".","..") for chunk in path.split("/"))
                    or "\\" in path or "%" in path or parts.query):
                raise ValueError("outside configured mirror directory")
        else:
            raise ValueError("source unavailable")
        return parts

    @contextmanager
    def open(self, provider, url):
        for _ in range(5):
            parts = self.check(provider,url)
            host = parts.hostname
            port = parts.port or (443 if parts.scheme=="https" else 80)
            addresses = socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
            if not addresses:
                raise OSError("source host unavailable")
            family, kind, proto, _, endpoint = addresses[0]
            address = ipaddress.ip_address(endpoint[0])
            if address.version==6 and address.ipv4_mapped:
                address=address.ipv4_mapped
            private_ok = (provider=="mirror" and self.private and
                          (address.is_loopback or any(address in net for net in PRIVATE if net.version==address.version)))
            if (not address.is_global and not private_ok) or address.is_multicast or address.is_link_local:
                raise ValueError("address outside authorized network")
            conn = http.client.HTTPConnection(host,port,timeout=12)
            try:
                conn.sock = socket.socket(family,kind,proto)
                conn.sock.settimeout(12)
                conn.sock.connect(endpoint)
                if parts.scheme=="https":
                    conn.sock = ssl.create_default_context().wrap_socket(conn.sock,server_hostname=host)
                path = parts.path or "/"
                conn.request("GET",path+("?"+parts.query if parts.query else ""),headers={"User-Agent":"rom-cli-sd/2"})
                response = conn.getresponse()
                if response.status in (301,302,303,307,308):
                    redirect=response.getheader("Location")
                    if not redirect:
                        raise ValueError("missing redirect destination")
                    url=urljoin(url,redirect)
                    continue
                if response.status!=200 or response.getheader("Content-Encoding","identity")!="identity":
                    raise ValueError(f"unsupported HTTP response ({response.status})")
                size=response.getheader("Content-Length")
                yield response, int(size) if size is not None else None
                return
            finally:
                conn.close()
        raise ValueError("too many redirects")

    def metadata(self,provider,url):
        with self.open(provider,url) as (stream,length):
            limit=1024*1024
            if length is not None and not 0<=length<=limit:
                raise ValueError("metadata size limit exceeded")
            data=stream.read(limit+1)
            if len(data)>limit or length is not None and len(data)!=length:
                raise ValueError("incomplete or oversized metadata")
            return data.decode("utf8")

PRIVATE=tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","fc00::/7"))

