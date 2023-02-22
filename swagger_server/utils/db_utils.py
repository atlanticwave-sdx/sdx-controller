import logging
import os

import pymongo

DB_NAME = os.environ.get("DB_NAME")
DB_CONFIG_TABLE_NAME = os.environ.get("DB_CONFIG_TABLE_NAME")
MONGODB_CONNSTRING = os.environ.get("MONGODB_CONNSTRING")


class DbUtils(object):
    def __init__(self):
        self.db_name = DB_NAME
        self.config_table_name = DB_CONFIG_TABLE_NAME
        self.mongo_client = pymongo.MongoClient(MONGODB_CONNSTRING)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def _initialize_db(self):
        self.logger.debug("Trying to load {} from DB".format(self.db_name))

        if self.db_name not in self.mongo_client.list_database_names():
            self.logger.debug(
                "No existing {} from DB, creating table".format(self.db_name)
            )
            self.sdxdb = self.mongo_client[self.db_name]
            self.logger.debug("DB {} initialized".format(self.db_name))

        self.sdxdb = self.mongo_client[self.db_name]
        config_col = self.sdxdb[self.config_table_name]
        self.logger.debug("DB {} initialized".format(self.db_name))

    def add_key_value_pair_to_db(self, key, value):
        obj = self.read_from_db(key)
        if obj is None:
            self.logger.debug("Adding key value pair {}:{} to DB.".format(key, value))
            return self.sdxdb[self.db_name][self.config_table_name].insert_one(
                {key: value}
            )

        query = {"_id": obj["_id"]}
        self.logger.debug("Updating DB entry {}:{}.".format(key, value))
        result = self.sdxdb[self.db_name][self.config_table_name].replace_one(
            query, {key: value}
        )
        return result

    def read_from_db(self, key):
        return self.sdxdb[self.db_name][self.config_table_name].find_one(
            {key: {"$exists": 1}}
        )
