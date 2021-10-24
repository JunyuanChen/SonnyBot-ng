# coding: utf-8

"""
Storage for user data.

Ideally we should use SQLite3 database or something similar,
but replit.com apparently causes committed data to disappear
randomly, which is totally unacceptable.

This is an attempt to workaround this replit.com issue, by
storing data in a git repository and pushing to GitHub.
Obviously, GitHub's storage is pretty reliable, since none
of my code on GitHub is disappearing.

To keep git happy, we choose to use text format JSON to
serialize data, instead of a binary blob.  We also have one
file for each user, instead of a single huge file.  This
will give us smaller commit/delta, and usable diffs.

Each user's data is serialized to a JSON file, {id}.json,
where id is the user's Discord ID.  All these JSON files are
stored in a git repository at {STORAGE_DIR} ("data repo").
The data repo have a remote named {REMOTE_NAME}, pointing to
GitHub.

If replit.com messes up our data, sync() will fetch remote
{REMOTE_NAME} (i.e. GitHub), and then switch to it.  All
local changes caused by replit.com are discarded.
"""

import os
import copy
import json
import subprocess

import logger


STORAGE_DIR = "data"
REMOTE_NAME = "origin"


class StorageError(Exception):
    """ Raised when storage operations fail. """


def field(field_name, doc=None, read_only=False):
    """
    Map a dict field to a class property.

    Example usage:
    ```
    class Foo:
        bar = field("bar")
    ```
    is equivalent to

    ```
    class Foo:
        @property
        def bar(self):
            return self._data["bar"]

        @bar.setter
        def bar(self, value):
            self._data["bar"] = value
    ```
    """
    def getter(self):
        return self._data[field_name]

    if not read_only:
        def setter(self, value):
            self._data[field_name] = value

        return property(getter, setter, doc=doc)
    return property(getter, doc=doc)


class User:
    _LOADED = {}

    def __init__(self, id, data):
        self._id = id
        self._snap = data
        self._data = copy.deepcopy(data)
        self._filename = f"{STORAGE_DIR}/{id}.json"

    @property
    def id(self):
        return self._id

    exp = field("exp", "EXP at current level")
    level = field("level")
    coins = field("coins")
    msg_count = field("msgCount")
    dmoj_username = field("dmojUsername")
    ccc_progress = field("cccProgress")

    def save(self):
        self._snap = copy.deepcopy(self._data)
        with open(self._filename, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4)

    def destroy(self):
        try:
            os.remove(self._filename)
            commit(f"Delete user {self.id}")
            logger.info(f"User {self.id} destroyed")
            del self._LOADED[self.id]
        except StorageError as e:
            logger.error(f"Failed to destroy user {self.id}")
            raise StorageError(f"Failed to delete user {self.id}") from e

    @classmethod
    def load(cls, id):
        """ Load a User from storage.  Raise KeyError if not found. """
        if id not in cls._LOADED:
            filename = f"{STORAGE_DIR}/{id}.json"
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    user = User(id, json.load(f))
                    cls._LOADED[id] = user
                    return user
            except FileNotFoundError as e:
                raise KeyError(id) from e
            except json.JSONDecodeError as e:
                logger.warn(f"Failed to load user {id}: Corrupted data")
                logger.warn(f"Ignoring existing data for user {id}")
                logger.debug(f"JSONDecodeError: {e}")
                raise KeyError(id) from e

        user = cls._LOADED[id]
        user._data = copy.deepcopy(user._snap)
        return user

    @classmethod
    def create(cls, id):
        """ Create a new User. """
        user = User(id, {
            "exp": 0,
            "level": 1,
            "coins": 0,
            "msgCount": 0,
            "dmojUsername": None,
            "cccProgress": {}
        })

        try:
            user.save()
            commit(f"Create new user {id}")
            logger.info(f"New user {id} created")
            cls._LOADED[id] = user
            return user
        except StorageError as e:
            logger.error(f"Failed to create user {id}")
            raise StorageError(f"Failed to create user {id}") from e

    @classmethod
    def load_or_create(cls, id):
        """ Load a User from storage.  Create one if not found. """
        try:
            return cls.load(id)
        except KeyError:
            return cls.create(id)

    @classmethod
    def all(cls):
        result = []
        for data_file in os.listdir(STORAGE_DIR):
            filename = f"{STORAGE_DIR}/{data_file}"
            if data_file.endswith(".json") and os.path.isfile(filename):
                try:
                    id = int(data_file[:-5])
                    user = cls.load(id)
                    result.append(user)
                except ValueError:
                    logger.warn(f"Invalid data file ignored: {data_file}")
                except KeyError:
                    # data file corrupted
                    # already logged by cls.load()
                    pass
        return result

    @classmethod
    def clear_cache(cls):
        cls._LOADED = {}
        logger.info(f"Cleared {cls.__name__} cache")


def commit(commit_message, no_error=False):
    try:
        subprocess.run(["git", "add", "--all"], cwd=STORAGE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", commit_message],
                       cwd=STORAGE_DIR, check=True)
        subprocess.run(["git", "push", REMOTE_NAME],
                       cwd=STORAGE_DIR, check=True)
    except subprocess.CalledProcessError as e:
        if not no_error:
            logger.error(f"Git operation failed with {e.returncode}: {e.cmd}")
            raise StorageError("Failed to save - see logs for details") from e


def sync():
    # Flush lazily committed data first
    commit("Flush lazily committed data", no_error=True)

    try:
        subprocess.run(["git", "fetch", REMOTE_NAME],
                       cwd=STORAGE_DIR, check=True)
        subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"],
                       cwd=STORAGE_DIR, check=True)
        User.clear_cache()
        logger.info("Synchronized storage from remote")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed with {e.returncode}: {e.cmd}")
        logger.error("Failed to synchronize with remote")
        raise StorageError("Failed to sync - see logs for details") from e
