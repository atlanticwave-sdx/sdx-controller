import dataset
import _pickle as pickle
import dataset
import logging
import os

DB_CONFIG_TABLE_NAME = os.environ.get('DB_CONFIG_TABLE_NAME')

class DbUtils(object):
    def __init__(self):
        # self.table_name
        self.config_table = DB_CONFIG_TABLE_NAME
        self.logger = logging.getLogger(__name__)
    
    def _initialize_db(self, db_filename, db_tables_tuples,
                       print_table_on_load=False):
        # DB related utils
        # Details on the setup:
        # https://dataset.readthedocs.io/en/latest/api.html
        # https://github.com/g2p/bedup/issues/38#issuecomment-43703630
        self.logger.debug("Connection to DB: %s" % db_filename)
        self.db = dataset.connect('sqlite:///' + db_filename, 
                                  engine_kwargs={'connect_args':
                                                 {'check_same_thread':False}})

        # Load the tables, create table if table does not.
        for (name, table) in db_tables_tuples:
            if table in self.db: #https://github.com/pudo/dataset/issues/281
                self.logger.debug("Trying to load {} from DB".format(name))
                t = self.db.load_table(table)
                if print_table_on_load:
                    entries = t.find()
                    self.logger.debug ("\n\n&&&&& ENTRIES in %s &&&&&" % name)
                    for e in entries:
                        self.logger.debug ("\n%s" % str(e))
                    self.logger.debug ("&&&&& END ENTRIES &&&&&\n\n")
                setattr(self, name, t)
                
            else:
                # If load_table() fails, that's fine! It means that the
                # table doesn't yet exist. So, create it.
                self.logger.debug("No existing {} from DB, creating table".format(name))
                t = self.db[table]
                setattr(self, name, t)

    def read_from_db(self, key):
        # Returns the manifest filename if it exists or None if it does not.
        d = self.config_table.find_one(key=key)
        if d == None:
            return None
        value = d['value']
        self.logger.debug("DB return value: " + str(value))
        return value

    def add_key_value_pair_to_db(self, key, value):
        # Pushes key-value to DB.
        if self.read_from_db(key) == None:
            self.logger.debug("Adding key value pair {}:{} to DB.".format(key, value))
            self.config_table.insert({'key':key, 'value':value})
        else:
            # Update entry if already exists.
            self.logger.debug("Updating DB entry {}:{}.".format(key, value))
            self.config_table.update({'key':key, 'value':value},
                                     ['key'])