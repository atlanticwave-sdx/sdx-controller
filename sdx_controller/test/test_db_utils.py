import os
import unittest

import pymongo

from sdx_controller.utils.db_utils import DbUtils
from sdx_controller.utils.constants import MongoCollections


class DbUtilsTests(unittest.TestCase):
    def setUp(self):
        # Make a backup of the existing environment.
        self.env = os.environ.copy()
        # Clear all environment variables
        os.environ.clear()

    def tearDown(self):
        # Restore environment from backup.
        os.environ = self.env

    def test_instance_with_empty_env(self):
        # This should raise an exception.
        with self.assertRaises(Exception):
            DbUtils()

    def test_instance_with_env_vars(self):
        # Set up the necessary environment variables.
        os.environ["DB_NAME"] = self.env.get("DB_NAME")
        os.environ["DB_CONFIG_TABLE_NAME"] = self.env.get("DB_CONFIG_TABLE_NAME")

        os.environ["MONGO_HOST"] = self.env.get("MONGO_HOST")
        os.environ["MONGO_PORT"] = self.env.get("MONGO_PORT")
        os.environ["MONGO_USER"] = self.env.get("MONGO_USER")
        os.environ["MONGO_PASS"] = self.env.get("MONGO_PASS")

        # This should not raise an exception.
        dbutils = DbUtils()
        dbutils.initialize_db()

    def test_db_updates(self):
        # Set up the necessary environment variables.
        os.environ["DB_NAME"] = self.env.get("DB_NAME")
        os.environ["DB_CONFIG_TABLE_NAME"] = MongoCollections.TOPOLOGIES

        os.environ["MONGO_HOST"] = self.env.get("MONGO_HOST")
        os.environ["MONGO_PORT"] = self.env.get("MONGO_PORT")
        os.environ["MONGO_USER"] = self.env.get("MONGO_USER")
        os.environ["MONGO_PASS"] = self.env.get("MONGO_PASS")

        dbutils = DbUtils()
        dbutils.initialize_db()

        # Try inserting empty strings as key:value
        key = ""
        val = ""
        res = dbutils.add_key_value_pair_to_db(
            self.env.get("DB_CONFIG_TABLE_NAME"), key, val
        )
        self.assertTrue(
            isinstance(res, pymongo.results.InsertOneResult)
            or isinstance(res, pymongo.results.UpdateResult)
        )

        # Try reading back
        res = dbutils.read_from_db(self.env.get("DB_CONFIG_TABLE_NAME"), key)
        self.assertEqual(res.get(key), val)

        res = dbutils.sdxdb[self.env.get("DB_CONFIG_TABLE_NAME")].delete_one({key: val})

        # Try inserting non-empty strings as key:value
        key = "test-key"
        val = "test-val"
        res = dbutils.add_key_value_pair_to_db(
            self.env.get("DB_CONFIG_TABLE_NAME"), key, val
        )
        self.assertTrue(
            isinstance(res, pymongo.results.InsertOneResult)
            or isinstance(res, pymongo.results.UpdateResult)
        )

        # Try reading back
        res = dbutils.read_from_db(self.env.get("DB_CONFIG_TABLE_NAME"), key)
        self.assertEqual(res.get(key), val)

        res = dbutils.sdxdb[self.env.get("DB_CONFIG_TABLE_NAME")].delete_one({key: val})

        res = dbutils.sdxdb[self.env.get("DB_CONFIG_TABLE_NAME")].drop()
