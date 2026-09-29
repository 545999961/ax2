import asyncio
import tempfile
import unittest
from pathlib import Path

from live_concurrency import LiveConcurrency


class LiveConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "concurrency.txt"
        self.path.write_text("1\n")
        self.gate = LiveConcurrency(1, str(self.path), poll_seconds=0.01)
        self.tasks = []

    async def asyncTearDown(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.assertEqual(self.gate.active, 0)

    def worker(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def run():
            async with self.gate:
                started.set()
                await finish.wait()

        task = asyncio.create_task(run())
        self.tasks.append(task)
        return started, finish, task

    async def entered(self, event):
        await asyncio.wait_for(event.wait(), timeout=1)

    async def test_live_increase_decrease_pause_and_resume(self):
        async with self.gate.monitor():
            first, finish_first, task_first = self.worker()
            second, finish_second, task_second = self.worker()
            third, _, _ = self.worker()
            await self.entered(first)
            self.assertFalse(second.is_set())
            self.path.write_text("2\n")
            await self.entered(second)
            self.assertFalse(third.is_set())

            self.path.write_text("1\n")
            self.gate.refresh()
            self.assertEqual(self.gate.active, 2)
            finish_first.set()
            await task_first
            await asyncio.sleep(0)
            self.assertFalse(third.is_set())

            self.path.write_text("0\n")
            self.gate.refresh()
            finish_second.set()
            await task_second
            await asyncio.sleep(0)
            self.assertEqual(self.gate.active, 0)
            self.assertFalse(third.is_set())
            self.path.write_text("1\n")
            await self.entered(third)

    async def test_cancellation_releases_only_acquired_slots(self):
        first, _, task_first = self.worker()
        second, _, task_second = self.worker()
        third, _, _ = self.worker()
        await self.entered(first)
        task_second.cancel()
        await asyncio.gather(task_second, return_exceptions=True)
        self.assertEqual(self.gate.active, 1)
        self.assertFalse(second.is_set())
        task_first.cancel()
        await self.entered(third)
        self.assertEqual(self.gate.active, 1)

    async def test_invalid_or_missing_file_preserves_limit(self):
        for value in ["", "-1", "2.5", "bad"]:
            self.path.write_text(value)
            self.gate.refresh()
            self.assertEqual(self.gate.limit, 1)
        self.path.unlink()
        self.gate.refresh()
        self.assertEqual(self.gate.limit, 1)

    async def test_initial_zero_and_monitor_cleanup(self):
        self.path.write_text("0\n")
        async with self.gate.monitor():
            started, _, _ = self.worker()
            await asyncio.sleep(0)
            self.assertFalse(started.is_set())
        self.assertFalse(any(
            task.get_coro().__name__ == "_watch"
            for task in asyncio.all_tasks()
        ))


if __name__ == "__main__":
    unittest.main()
