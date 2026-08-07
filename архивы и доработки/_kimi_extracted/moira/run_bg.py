import io
import os
import sys

root = os.path.dirname(os.path.abspath(__file__))
os.chdir(root)

fd = os.open(os.path.join(root, "bot.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
os.dup2(fd, 1)
os.dup2(fd, 2)
stream = io.TextIOWrapper(io.FileIO(1, "w"), encoding="utf-8", write_through=True)
sys.stdout = stream
sys.stderr = io.TextIOWrapper(io.FileIO(2, "w"), encoding="utf-8", write_through=True)

from bot.main import main  # noqa: E402
import asyncio  # noqa: E402

asyncio.run(main())
