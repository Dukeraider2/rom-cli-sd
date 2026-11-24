import json
import os
import ssl
import unittest
from unittest.mock import patch
from library.providers import search
from library.provider_http import Network, verified_tls_context


class ProviderTests(unittest.TestCase):
    def test_missing_loader_trust_paths_use_os_bundle_only_without_override(self):
        paths = ssl.get_default_verify_paths()._replace(cafile=None, capath=None)
        with patch("ssl.get_default_verify_paths", return_value=paths), patch.dict(os.environ, {}, clear=True), \
                patch("os.path.isfile", return_value=True), patch("ssl.create_default_context") as create:
            verified_tls_context()
            create.assert_called_once_with(cafile="/etc/ssl/cert.pem")
            os.environ[paths.openssl_cafile_env] = "/custom/trust.pem"
            verified_tls_context()
            create.assert_called_with()

    def test_directory_pagination(self):
        network=Network("http://127.0.0.1/roms",True)
        network.metadata=lambda *_: "".join(f'<a href="Game{i}.gba">Game</a>' for i in range(25))+'<a href="../Other.gba">bad</a>'
        one,more=search(network,"mirror","game","gba",1)
        two,end=search(network,"mirror","game","gba",2)
        self.assertTrue(more)
        self.assertFalse(end)
        self.assertEqual(len({r["id"] for r in one+two}),25)
        with self.assertRaises(ValueError):
            network.check("mirror","http://127.0.0.1/elsewhere")

    def test_archive_metadata(self):
        network=Network()
        values=iter([{"response":{"docs":[{"identifier":"demo"}],"numFound":2}},
                     {"metadata":{"title":"Demo"},"files":[{"name":"demo.chd","size":"12"},{"name":"x.zip"},{"name":"../demo.chd"}]}])
        network.metadata=lambda *_:json.dumps(next(values))
        rows,more=search(network,"archive","Demo",None,1)
        self.assertTrue(more)
        self.assertEqual(len(rows),1)
        self.assertIn("psx",rows[0]["systems"])

