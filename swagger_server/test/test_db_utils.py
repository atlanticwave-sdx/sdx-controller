import os
import unittest

import pymongo

from swagger_server.utils.db_utils import DbUtils


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
        os.environ["MONGODB_CONNSTRING"] = self.env.get("MONGODB_CONNSTRING")

        # This should not raise an exception.
        dbutils = DbUtils()
        dbutils.initialize_db()

    def test_db_updates(self):
        # Set up the necessary environment variables.
        os.environ["DB_NAME"] = self.env.get("DB_NAME")
        os.environ["DB_CONFIG_TABLE_NAME"] = self.env.get("DB_CONFIG_TABLE_NAME")
        os.environ["MONGODB_CONNSTRING"] = self.env.get("MONGODB_CONNSTRING")

        dbutils = DbUtils()
        dbutils.initialize_db()

        # Try inserting empty strings as key:value
        key = ""
        val = ""
        res = dbutils.add_key_value_pair_to_db(key, val)
        self.assertTrue(
            isinstance(res, pymongo.results.InsertOneResult)
            or isinstance(res, pymongo.results.UpdateResult)
        )

        # Try reading back
        res = dbutils.read_from_db(key)
        self.assertEqual(res.get(key), val)

        res = dbutils.sdxdb[self.env.get("DB_CONFIG_TABLE_NAME")].delete_one({key: val})

        # Try inserting non-empty strings as key:value
        key = "test-key"
        val = "test-val"
        res = dbutils.add_key_value_pair_to_db(key, val)
        self.assertTrue(
            isinstance(res, pymongo.results.InsertOneResult)
            or isinstance(res, pymongo.results.UpdateResult)
        )

        # Try reading back
        res = dbutils.read_from_db(key)
        self.assertEqual(res.get(key), val)

        res = dbutils.sdxdb[self.env.get("DB_CONFIG_TABLE_NAME")].delete_one({key: val})

        res = dbutils.sdxdb[self.env.get("DB_CONFIG_TABLE_NAME")].drop()
