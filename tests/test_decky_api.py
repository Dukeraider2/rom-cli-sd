import unittest
from unittest.mock import Mock
from library.decky_api import Service


class ContractTests(unittest.TestCase):
    def test_closed_schema(self):
        api=Service(Mock())
        for op,args in [("shell",{}),("enqueue",{"confirmed":False,"token":"1"*32}),
                        ("list_games",{"page":True}),("get_progress",{"job":"/path"}),
                        ("search",{"url":"http://invalid"}),("list_platforms",{"user":"alternate"})]:
            self.assertEqual(api.request(1,op,args)["error"]["code"],"invalid_request")
        self.assertEqual(api.request(2,"list_platforms",{})["error"]["code"],"version")
        self.assertEqual(api.request(1,"enqueue",dict(token="0"*32,confirmed=True))["error"]["code"],"expired")

