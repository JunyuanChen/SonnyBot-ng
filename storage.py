# coding: utf-8

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
        bar = property("bar")
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
            logger.error(f"Failed to destroy user {user.id}")
            raise StorageError(f"Failed to delete user {user.id}") from e

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
            "dmojUsername": None
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
                except ValueError as e:
                    logger.warn(f"Invalid data file ignored: {data_file}")
                except KeyError:
                    # data file corrupted
                    # already logged by cls.load()
                    pass
        return result


def commit(commit_message):
    try:
        subprocess.run(["git", "add", "--all"], cwd=STORAGE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", commit_message],
                       cwd=STORAGE_DIR, check=True)
        subprocess.run(["git", "push", REMOTE_NAME],
                       cwd=STORAGE_DIR, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed with {e.returncode}: {e.cmd}")
        logger.debug(f"Git output:\nSTDOUT:\n{e.output}\nSTDERR:\n{e.stderr}")
        raise StorageError("Failed to save - see logs for details") from e


def sync():
    # Flush lazily committed data first
    try:
        commit("Flush lazily committed data")
    except StorageError:
        # Nothing to commit, no problem.
        pass

    try:
        subprocess.run(["git", "reset", "--hard", "HEAD~1"],
                       cwd=STORAGE_DIR, check=True)
        subprocess.run(["git", "pull", REMOTE_NAME],
                       cwd=STORAGE_DIR, check=True)
        logger.info("Synchronized storage from remote")
        User._LOADED = {}
        logger.info("Cleared User cache")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed with {e.returncode}: {e.cmd}")
        logger.debug(f"Git output:\nSTDOUT:\n{e.output}\nSTDERR:\n{e.stderr}")
        logger.error("Failed to synchronize with remote")
        raise StorageError("Failed to sync - see logs for details") from e
