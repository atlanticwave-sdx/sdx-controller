import logging
import os
import time
from urllib.parse import urlparse

import pymongo
from sdx_datamodel.constants import MongoCollections

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
        self.logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "DEBUG")))

        # Log DB URI, without a password.
        self.logger.info(f"[DB] Using {obfuscate_password_in_uri(mongo_connstring)}")

        self.mongo_client = pymongo.MongoClient(mongo_connstring)

    def initialize_db(self):
        """
        Creates collections if not exist in DB
        """
        self.logger.debug(f"Trying to load {self.db_name} from DB")

        if self.db_name not in self.mongo_client.list_database_names():
            self.logger.debug(f"No existing {self.db_name} from DB, creating table")
            self.sdxdb = self.mongo_client[self.db_name]
            self.logger.debug(f"DB {self.db_name} initialized")

        self.sdxdb = self.mongo_client[self.db_name]
        # config_col = self.sdxdb[self.config_table_name]
        for key, collection in MongoCollections.__dict__.items():
            if (
                not key.startswith("__")
                and collection not in self.sdxdb.list_collection_names()
            ):
                self.sdxdb.create_collection(collection)

        self.logger.debug(f"DB {self.db_name} initialized")

    def add_key_value_pair_to_db(self, collection, key, value, max_retries=3):
        """
        Adds or replaces a key-value pair in the database.
        """
        key = str(key)
        retry_count = 0

        while retry_count < max_retries:
            try:
                obj = self.read_from_db(collection, key)

                if obj is None:
                    # Document doesn't exist, create a new one
                    document = {key: value}
                    result = self.sdxdb[collection].insert_one(document)

                    if result.acknowledged and result.inserted_id:
                        return result
                    logging.error("Insert operation not acknowledged")

                else:
                    # Document exists, replace with new key-value pair
                    new_document = {key: value}
                    new_document["_id"] = obj["_id"]

                    query = {"_id": obj["_id"]}
                    result = self.sdxdb[collection].replace_one(query, new_document)

                    if result.acknowledged and result.modified_count == 1:
                        return result
                    logging.error(
                        f"Replace operation not successful: modified_count={result.modified_count}"
                    )

            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logging.error(
                        f"Failed to add key-value pair after {max_retries} attempts. Collection: {collection}, Key: {key}. Error: {str(e)}"
                    )
                    return None

                time.sleep(0.5 * (2**retry_count))
                logging.warning(
                    f"Retry {retry_count}/{max_retries} for adding key-value pair. Collection: {collection}, Key: {key}"
                )

        return None

    def update_field_in_json(self, collection, key, field_name, field_value):
        """
        Updates a single field in a JSON object.
        """
        key = str(key)

        try:
            # Update a nested field directly
            # Format: {key}.{field_name} targets a specific field within a JSON object
            update_query = {"$set": {f"{key}.{field_name}": field_value}}

            # Perform atomic update operation
            result = self.sdxdb[collection].update_one(
                {key: {"$exists": True}},  # Find document where the key exists
                update_query,
            )

            if result.matched_count == 0:
                logging.error(
                    f"Document with key '{key}' not found in collection '{collection}'"
                )
                return None

            return result

        except Exception as e:
            logging.error(
                f"Failed to update field. Collection: {collection}, Key: {key}, Field: {field_name}. Error: {str(e)}"
            )
            return None

    def read_from_db(self, collection, key):
        """
        Reads a document from the database using the specified key.
        """
        key = str(key)
        try:
            # Find document where the key exists and not marked as deleted
            result = self.sdxdb[collection].find_one(
                {key: {"$exists": 1}, "deleted": {"$ne": True}}
            )
            return result
        except Exception as e:
            logging.error(
                f"Error reading from database. Collection: {collection}, Key: {key}. Error: {str(e)}"
            )
            return None

    def get_value_from_db(self, collection, key):
        """
        Gets just the value for a specific key from the database.
        """
        document = self.read_from_db(collection, key)

        if document and key in document:
            return document[key]
        return None

    def get_all_entries_in_collection(self, collection):
        """
        Gets all entries in a Mongo collection
        """
        db_collection = self.sdxdb[collection]
        # MongoDB has an ObjectId for each item, so need to exclude the ObjectIds
        all_entries = db_collection.find({"deleted": {"$ne": True}}, {"_id": 0})
        return all_entries

    def mark_deleted(self, collection, key):
        """
        Marks an entry deleted
        """
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
        """
        Actually deletes one entry
        """
        key = str(key)
        db_collection = self.sdxdb[collection]
        db_collection.delete_one({key: {"$exists": True}})
