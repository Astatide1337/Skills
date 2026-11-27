import unittest

from scheduler.queue import JobQueue


class QueueTests(unittest.TestCase):
    def test_priority_first(self):
        q = JobQueue()
        q.submit("low", 1)
        q.submit("high", 9)
        self.assertEqual(q.next_jobs(1), ["high"])

    def test_equal_priority_keeps_submission_order(self):
        q = JobQueue()
        q.submit("urgent", 9)
        q.submit("backup", 5)
        q.submit("reindex", 5)
        self.assertEqual(q.next_jobs(3), ["urgent", "backup", "reindex"])


if __name__ == "__main__":
    unittest.main()
