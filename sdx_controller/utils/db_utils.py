import logging
import os

import pymongo
import json


COLLECTION_NAMES = ["topologies", "connections", "domains"]

class DbUtils(object):
    def __init__(self):
        self.db_name = os.environ.get("DB_NAME")
        if self.db_name is None:
            raise Exception("DB_NAME environment variable is not set")

        # self.config_table_name = os.environ.get("DB_CONFIG_TABLE_NAME")
        # if self.config_table_name is None:
        #     raise Exception("DB_CONFIG_TABLE_NAME environ variable is not set")

        mongo_connstring = os.environ.get("MONGODB_CONNSTRING")
        if mongo_connstring is None:
            raise Exception("MONGODB_CONNSTRING environment variable is not set")
        self.mongo_client = pymongo.MongoClient(mongo_connstring)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def initialize_db(self):
        self.logger.debug(f"Trying to load {self.db_name} from DB")

        if self.db_name not in self.mongo_client.list_database_names():
            self.logger.debug(f"No existing {self.db_name} from DB, creating table")
            self.sdxdb = self.mongo_client[self.db_name]
            self.logger.debug(f"DB {self.db_name} initialized")

        self.sdxdb = self.mongo_client[self.db_name]
        # config_col = self.sdxdb[self.config_table_name]
        for name in COLLECTION_NAMES:
            if name not in self.sdxdb.list_collection_names():
                self.sdxdb.create_collection(name)
    
        self.logger.debug(f"DB {self.db_name} initialized")

    def add_key_value_pair_to_db(self, collection, key, value):
        key = str(key)
        obj = self.read_from_db(collection, key)
        if obj is None:
            # self.logger.debug(f"Adding key value pair {key}:{value} to DB.")
            return self.sdxdb[collection].insert_one(
                {key: value}
            )

        query = {"_id": obj["_id"]}
        # self.logger.debug(f"Updating DB entry {key}:{value}.")
        result = self.sdxdb[collection].replace_one(
            query, {key: value}
        )
        return result

    def read_from_db(self, collection, key):
        key = str(key)
        return self.sdxdb[collection].find_one(
            {key: {"$exists": 1}}
        )

    def get_all_entries_in_collection(self, collection):
        db_collection = self.sdxdb[collection]
        all_entries = list(db_collection.find({}))
        return all_entries
