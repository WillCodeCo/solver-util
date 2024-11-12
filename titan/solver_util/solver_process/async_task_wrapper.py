import typing
import asyncio
import logging


logger = logging.getLogger(__name__)



class AsyncTaskWrapper:
    
    def __init__(self, coro):
        self._coro = coro
        self._task = None

    @classmethod
    async def gracefully_cancel_awaitable(cls, task):
        try:
            if not task.done():
                task.cancel()
            await task
        except:
            pass

    def has_started(self):
        return (self._task is not None)

    def cancelled(self):
        if (not self.has_started()):
            raise asyncio.InvalidStateError(f"Cannot invoke {self.__class__.__name__}.cancelled() because it has not been started yet")
        return self._task.cancelled()

    def done(self):
        if (not self.has_started()):
            raise asyncio.InvalidStateError(f"Cannot invoke {cls.__class__.__name__}.done() because it has not been started yet")
        return self._task.done()

    def active(self):
        return self.has_started() and (not self.done())

    async def start(self):
        self._task = asyncio.create_task(self._coro)

    async def wait_closed(self):
        if (not self.has_started()):
            raise asyncio.InvalidStateError(f"Cannot invoke {cls.__class__.__name__}.wait_closed() because it has not been started yet")
        await asyncio.shield(self._task)

    async def close(self):
        """
        Cancel and wait for all tasks to finish
        """
        if (not self.has_started()):
            raise asyncio.InvalidStateError(f"Cannot invoke {cls.__class__.__name__}.close() because it has not been started yet")
        try:
            await asyncio.shield(self.gracefully_cancel_awaitable(self._task))
        except asyncio.CancelledError:
            await self.gracefully_cancel_awaitable(self._task)
            raise

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        close_task = asyncio.create_task(self.close())
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError:
            await close_task
            raise
        except Exception as e:
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")