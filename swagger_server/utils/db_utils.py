import dataset

class DbUtils(object):
    def _initialize_db(self, db_filename, db_tables_tuples,
                       print_table_on_load=False):
        # DB related utils
        # Details on the setup:
        # https://dataset.readthedocs.io/en/latest/api.html
        # https://github.com/g2p/bedup/issues/38#issuecomment-43703630
        print("Connection to DB: %s" % db_filename)
        self.db = dataset.connect('sqlite:///' + db_filename, 
                                  engine_kwargs={'connect_args':
                                                 {'check_same_thread':False}})

        #Try loading the tables, if they don't exist, create them.
        for (name, table) in db_tables_tuples:
            if table in self.db: #https://github.com/pudo/dataset/issues/281
                print("Trying to load %s from DB" % name)
                t = self.db.load_table(table)
                if print_table_on_load:
                    entries = t.find()
                    print ("\n\n&&&&& ENTRIES in %s &&&&&" % name)
                    for e in entries:
                        print ("\n%s" % str(e))
                    print ("&&&&& END ENTRIES &&&&&\n\n")
                    
                setattr(self, name, t)
                
            else:
                # If load_table() fails, that's fine! It means that the
                # table doesn't yet exist. So, create it.
                print("Failed to load %s from DB, creating table" %
                                 name)
                t = self.db[table]
                setattr(self, name, t)