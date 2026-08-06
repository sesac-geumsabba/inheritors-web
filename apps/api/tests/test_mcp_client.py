import asyncio
import unittest

from app.mcp_client import KoreanLawMCPClient


class TestKoreanLawMCPClient(unittest.TestCase):
    def setUp(self):
        self.client = KoreanLawMCPClient()

    def test_search_law(self):
        async def run():
            res = await self.client.search_law("민법", timeout=5.0)
            self.assertIsInstance(res, list)
            self.assertGreater(len(res), 0)
            self.assertEqual(res[0]["source_type"], "statute")
        asyncio.run(run())

    def test_search_decisions(self):
        async def run():
            res = await self.client.search_decisions("손해배상", timeout=5.0)
            self.assertIsInstance(res, list)
            self.assertGreater(len(res), 0)
            self.assertEqual(res[0]["source_type"], "case_law")
        asyncio.run(run())

    def test_verify_citations(self):
        async def run():
            res = await self.client.verify_citations("민법 제750조에 따른 손해배상", timeout=5.0)
            self.assertIn("verified", res)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
