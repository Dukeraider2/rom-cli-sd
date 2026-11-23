import json
import unittest
from library.providers import search
from library.provider_http import Network


class ProviderTests(unittest.TestCase):
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

