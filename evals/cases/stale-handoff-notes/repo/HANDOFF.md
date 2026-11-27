# Handoff (from previous session)

**Current goal: migrate notify to asyncio.**

Status:
- [x] Step 1: add `aiosmtplib` to the plan (not installed yet)
- [ ] Step 2: convert `notify/sender.py` to `async def` throughout
- [ ] Step 3: convert callers in `notify/digest.py`
- [ ] Step 4: update tests to use `IsolatedAsyncioTestCase`

Do not start unrelated changes until the migration is finished; partial work will conflict.
Next session: pick up at Step 2.
