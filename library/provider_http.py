"""Origin-scoped HTTP. Connect to a checked address, retaining the TLS hostname."""
import http.client
import ipaddress
import os
import socket
import ssl
import threading
import time
from contextlib import contextmanager
from urllib.parse import urljoin, urlsplit, unquote
from .transfer import origin


def verified_tls_context():
    paths = ssl.get_default_verify_paths()
    explicit_store = paths.openssl_cafile_env in os.environ or paths.openssl_capath_env in os.environ
    # Decky's frozen OpenSSL searches /usr/lib/ssl on SteamOS.
    if not explicit_store and not paths.cafile and not paths.capath and os.path.isfile("/etc/ssl/cert.pem"):
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return ssl.create_default_context()


class Network:
    def __init__(self, mirror=None, allow_private=False):
        self.mirror = mirror.rstrip("/")+"/" if mirror else None
        self.private = allow_private is True
        self.stopped=threading.Event()
        self.lock=threading.Lock()
        self.connections={}
        self.resolvers=threading.BoundedSemaphore(3)
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
    def open(self, provider, url, seconds=7200, scope=None):
        deadline=time.monotonic()+seconds
        for _ in range(5):
            if self.stopped.is_set() or time.monotonic()>=deadline:
                raise InterruptedError("Source request stopped or timed out")
            parts = self.check(provider,url)
            host = parts.hostname
            port = parts.port or (443 if parts.scheme=="https" else 80)
            addresses = self.resolve(host,port,min(deadline,time.monotonic()+12))
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
            control=None
            timer=None
            try:
                conn.sock = socket.socket(family,kind,proto)
                conn.sock.settimeout(12)
                conn.sock.connect(endpoint)
                if parts.scheme=="https":
                    conn.sock = verified_tls_context().wrap_socket(conn.sock,server_hostname=host)
                control=socket.socket(fileno=socket.dup(conn.sock.fileno()))
                with self.lock:
                    if self.stopped.is_set():
                        raise InterruptedError("Source request stopped")
                    self.connections[control]=scope
                timer=threading.Timer(max(0,deadline-time.monotonic()),self.interrupt,args=(control,))
                timer.daemon=True
                timer.start()
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
                if timer:
                    timer.cancel()
                if control:
                    with self.lock:
                        self.connections.pop(control,None)
                    control.close()
                conn.close()
        raise ValueError("too many redirects")

    def metadata(self,provider,url):
        with self.open(provider,url,seconds=20) as (stream,length):
            limit=1024*1024
            if length is not None and not 0<=length<=limit:
                raise ValueError("metadata size limit exceeded")
            data=stream.read(limit+1)
            if len(data)>limit or length is not None and len(data)!=length:
                raise ValueError("incomplete or oversized metadata")
            return data.decode("utf8")

    @staticmethod
    def interrupt(sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def stop(self):
        self.stopped.set()
        self.abort()

    def abort(self,scope=None):
        with self.lock:
            for sock,owner in self.connections.items():
                if scope is None or scope==owner:
                    self.interrupt(sock)

    def resolve(self,host,port,deadline):
        if not self.resolvers.acquire(blocking=False):
            raise OSError("Source name resolver busy")
        done=threading.Event()
        result=[]
        def lookup():
            try:
                result.extend(socket.getaddrinfo(host,port,type=socket.SOCK_STREAM))
            except OSError:
                pass
            finally:
                self.resolvers.release()
                done.set()
        threading.Thread(target=lookup,daemon=True).start()
        while not done.wait(.1):
            if self.stopped.is_set() or time.monotonic()>=deadline:
                raise TimeoutError("Source lookup timed out")
        return result

PRIVATE=tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","fc00::/7"))

