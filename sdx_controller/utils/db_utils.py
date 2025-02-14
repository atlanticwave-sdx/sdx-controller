import logging
import os
from urllib.parse import urlparse
from constants import MongoCollections

import pymongo


pymongo_logger = logging.getLogger("pymongo")
pymongo_logger.setLevel(logging.INFO)


def obfuscate_password_in_uri(uri: str) -> str:
    """
    Replace password field in URIs with a `*`, for logging.
    """
    parts = urlparse(uri)
    if parts.password:
        return uri.replace(parts.password, "*")
    else:
        return uri


class DbUtils(object):
    def __init__(self):
        self.db_name = os.environ.get("DB_NAME")
        if self.db_name is None:
            raise Exception("DB_NAME environment variable is not set")

        # self.config_table_name = os.environ.get("DB_CONFIG_TABLE_NAME")
        # if self.config_table_name is None:
        #     raise Exception("DB_CONFIG_TABLE_NAME environ variable is not set")

        mongo_user = os.getenv("MONGO_USER") or "guest"
        mongo_pass = os.getenv("MONGO_PASS") or "guest"
        mongo_host = os.getenv("MONGO_HOST")
        mongo_port = os.getenv("MONGO_PORT") or 27017

        if mongo_host is None:
            mongo_connstring = os.getenv("MONGODB_CONNSTRING")
            if mongo_connstring is None:
                raise Exception("Neither MONGO_HOST nor MONGODB_CONNSTRING is set")
        else:
            mongo_connstring = (
                f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:{mongo_port}/"
            )

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Log DB URI, without a password.
        self.logger.info(f"[DB] Using {obfuscate_password_in_uri(mongo_connstring)}")

        self.mongo_client = pymongo.MongoClient(mongo_connstring)

    def initialize_db(self):
        self.logger.debug(f"Trying to load {self.db_name} from DB")

        if self.db_name not in self.mongo_client.list_database_names():
            self.logger.debug(f"No existing {self.db_name} from DB, creating table")
            self.sdxdb = self.mongo_client[self.db_name]
            self.logger.debug(f"DB {self.db_name} initialized")

        self.sdxdb = self.mongo_client[self.db_name]
        # config_col = self.sdxdb[self.config_table_name]
        for collection in MongoCollections:
            if collection not in self.sdxdb.list_collection_names():
                self.sdxdb.create_collection(collection.value)

        self.logger.debug(f"DB {self.db_name} initialized")

    def add_key_value_pair_to_db(self, collection, key, value):
        key = str(key)
        obj = self.read_from_db(collection, key)
        if obj is None:
            return self.sdxdb[collection].insert_one({key: value})

        query = {"_id": obj["_id"]}
        result = self.sdxdb[collection].replace_one(query, {key: value})
        return result

    def read_from_db(self, collection, key):
        key = str(key)
        return self.sdxdb[collection].find_one(
            {key: {"$exists": 1}, "deleted": {"$ne": True}}
        )

    def get_all_entries_in_collection(self, collection):
        db_collection = self.sdxdb[collection]
        # MongoDB has an ObjectId for each item, so need to exclude the ObjectIds
        all_entries = db_collection.find({"deleted": {"$ne": True}}, {"_id": 0})
        return all_entries

    def mark_deleted(self, collection, key):
        db_collection = self.sdxdb[collection]
        key = str(key)
        item_to_delete = self.read_from_db(collection, key)
        if item_to_delete is None:
            return False
        filter = {"_id": item_to_delete["_id"]}
        update = {"$set": {"deleted": True}}
        db_collection.update_one(filter, update)
        return True

    def delete_one_entry(self, collection, key):
        key = str(key)
        db_collection = self.sdxdb[collection]
        db_collection.delete_one({key: {"$exists": True}})
