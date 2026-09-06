from globaleaks import DATABASE_VERSION, FIRST_DATABASE_VERSION_SUPPORTED
from globaleaks.db.appdata import load_appdata
from globaleaks.utils.log import log
from globaleaks.utils.utility import snake_case


class MigrationBase(object):
    """
    This is the base class used by every Updater
    """
    skip_model_migration = {}
    skip_count_check = {}

    # Columns renamed between the two schemas: {model: {new_column: old_column}}
    renamed_attrs = {}

    # Columns whose value is computed from the old object rather than copied:
    # {model: {column: callable(old_obj)}}; a conversion takes precedence over
    # the copy and the rename of the column
    converted_attrs = {}

    # Configuration variables renamed between the two schemas:
    # {old_var_name: new_var_name}
    renamed_config = {}

    # Configuration values converted between the two schemas, by the new name
    # of the variable: {var_name: callable(value)}
    converted_config = {}

    def __init__(self, migration_mapping, start_version, session_old, session_new):
        self.appdata = load_appdata()

        self.migration_mapping = migration_mapping
        self.start_version = start_version

        self.session_old = session_old
        self.session_new = session_new

        self.model_from = {}
        self.model_to = {}
        self.entries_count = {}

        expected = DATABASE_VERSION + 1 - FIRST_DATABASE_VERSION_SUPPORTED
        for model_name, model_history in migration_mapping.items():
            length = len(model_history)
            if length != expected:
                raise TypeError('Number of status mismatch for table {}, expected:{} actual:{}'.format(model_name, expected, length))

            self.model_from[model_name] = model_history[start_version - FIRST_DATABASE_VERSION_SUPPORTED]
            self.model_to[model_name] = model_history[start_version + 1 - FIRST_DATABASE_VERSION_SUPPORTED]

            if self.model_from[model_name] is None or self.model_to[model_name] is None:
                self.entries_count[model_name] = 0
            else:
                self.entries_count[model_name] = self.session_old.query(self.model_from[model_name]).count()

        self.session_new.commit()

    def commit(self):
        self.session_new.commit()

    def close(self):
        self.session_old.close()
        self.session_new.close()

    def prologue(self):
        pass

    def epilogue(self):
        pass

    def mapping(self, model_name, old_obj):
        """
        Return the values of the new object corresponding to an old object:
        the columns the old object has, renamed and converted as declared

        :param model_name: The model name
        :param old_obj: The object of the old schema
        :return: A dictionary {column: value}
        """
        renamed = self.renamed_attrs.get(model_name, {})
        converted = self.converted_attrs.get(model_name, {})
        column_keys = [c.key for c in self.model_to[model_name].__table__.columns]

        mapping = {key: getattr(old_obj, renamed.get(key, key)) for key in column_keys if hasattr(old_obj, renamed.get(key, key))}

        for key, convert in converted.items():
            mapping[key] = convert(old_obj)

        if model_name == 'Config':
            self.convert_config(mapping)

        return mapping

    def copy(self, model_name, old_obj):
        """
        Return a new object holding the values of an old object, for the
        migrations that need to complete it before adding it

        :param model_name: The model name
        :param old_obj: The object of the old schema
        :return: The object of the new schema, not yet added to the session
        """
        new_obj = self.model_to[model_name]()

        for key, value in self.mapping(model_name, old_obj).items():
            setattr(new_obj, key, value)

        return new_obj

    def add_entry(self, model_name, new_obj):
        """
        Add to the new database an object not corresponding to any object of
        the old one, accounting for it in the integrity check of the counts

        :param model_name: The model name
        :param new_obj: The object to add
        """
        self.session_new.add(new_obj)
        self.entries_count[model_name] += 1

    def generic_migration_function(self, model_name):
        mappings = [self.mapping(model_name, old_obj)
                    for old_obj in self.session_old.query(self.model_from[model_name]).yield_per(1000)]

        if mappings:
            self.session_new.bulk_insert_mappings(self.model_to[model_name], mappings)

    def convert_config(self, mapping):
        """
        Apply to a configuration variable the rename and the conversion of
        its value declared by the migration
        """
        var_name = self.renamed_config.get(mapping['var_name'], mapping['var_name'])
        mapping['var_name'] = var_name

        if var_name in self.converted_config:
            mapping['value'] = self.converted_config[var_name](mapping['value'])

    def migrate_model(self, model_name):
        if self.entries_count[model_name] <= 0 or self.skip_model_migration.get(model_name, False):
            return

        log.info(' * %s [#%d]' % (model_name, self.entries_count[model_name]))

        specific_migration_function = getattr(self, 'migrate_' + snake_case(model_name), None)
        if specific_migration_function is None:
            self.generic_migration_function(model_name)
        else:
            specific_migration_function()
