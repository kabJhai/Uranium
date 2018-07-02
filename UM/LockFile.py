# Copyright (c) 2018 Ultimaker B.V.
# Uranium is released under the terms of the LGPLv3 or higher.

import os
import time  # For timing lock file
from typing import Any

from UM.Logger import Logger


##  Manage a lock file for reading / writing in a directory.
#   \param filename the filename to use as lock file
#   \param timeout in seconds; if the file is too old by this amount, then it gets ignored
#   \param wait_msg the message to log when waiting for the lock file to disappear
#
#   example usage:
#   $ with LockFile("my_lock_file.lock"):
#   $   <do something in a directory>
class LockFile:
    ##  Creates the locker instance that will hold the lock file.
    #
    #   \param filename The name and path of the lockfile to create.
    #   \param timeout After this amount of seconds, the lock will break
    #   regardless of the state of the file system.
    #   \param wait_msg A message to log when the thread is blocked by the lock.
    #   It is intended that you modify this to better indicate what lock file is
    #   blocking the thread.
    def __init__(self, filename: str, timeout: int = 10, wait_msg: str = "Waiting for lock file to disappear...") -> None:
        self._filename = filename
        self._wait_msg = wait_msg
        self._timeout = timeout

    ##  Block the thread until the lock file no longer exists.
    #
    #   This is implemented using a spin loop.
    def _waitLockFileDisappear(self) -> None:
        now = time.time()
        try:
            while os.path.exists(self._filename) and now < os.path.getmtime(self._filename) + self._timeout and now > os.path.getmtime(self._filename):
                Logger.log("d", self._wait_msg)
                time.sleep(0.1)
                now = time.time()
        # Sometimes the file is deleted after checking "exists" and before checking "getmtime", and in this case this
        # function can't find the file. If the file doesn't exist, it dissapear so this can continue.
        except FileNotFoundError:
            pass

    ##  Creates the lock file on the file system.
    #
    #   The lock file is filled with the current process ID. Python's own GIL
    #   will ensure that this is thread-safe then.
    def _createLockFile(self) -> None:
        try:
            with open(self._filename, "w", encoding = "utf-8") as lock_file:
                lock_file.write("%s" % os.getpid())
        except:
            Logger.log("e", "Could not create lock file [%s]" % self._filename)

    ##  Deletes the lock file from the file system.
    def _deleteLockFile(self) -> None:
        try:
            os.remove(self._filename)
        except FileNotFoundError:
            #This can happen due to a leak in the thread-safety of this system.
            #We ignore this leak for now, but this is how it can happen:
            #   This thread              Other thread
            # 1 Check if lock exists     Check if lock exists
            # 2                          Create lock file
            # 3 Create lock file (fails)
            # 4 Do work                  Do work
            # 5                          Delete lock file
            # 6 Delete lock file (here)
            pass
        except:
            Logger.log("e", "Could not delete lock file [%s]" % self._filename)

    ##  Attempt to grab the lock file for personal use.
    def __enter__(self) -> None:
        self._waitLockFileDisappear()
        self._createLockFile()

    ##  Release the lock file so that other processes may use it.
    #
    #   \param exc_type The type of exception that was raised during the
    #   ``with`` block, if any. Use ``None`` if no exception was raised.
    #   \param exc_val The exception instance that was raised during the
    #   ``with`` block, if any. Use ``None`` if no exception was raised.
    #   \param exc_tb The traceback frames at the time the exception occurred,
    #   if any. Use ``None`` if no exception was raised.
    def __exit__(self, exc_type: type, exc_val: Exception, exc_tb: Any) -> None: #exc_tb is actually a traceback object which is not exposed in Python.
        self._deleteLockFile()
