import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.winfix_agent import WinFixAgent


class PiFallbackTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_ollama_falls_back_to_valid_diagnosis(self) -> None:
        agent = WinFixAgent()
        evidence, diagnosis = await agent.investigate("My PC is slow", ["performance"])

        self.assertEqual(len(evidence), 6)
        self.assertTrue(diagnosis.summary)
        self.assertGreaterEqual(diagnosis.overall_confidence, 0)
        self.assertLessEqual(diagnosis.overall_confidence, 1)
