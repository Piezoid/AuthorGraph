import logging

logger = logging.getLogger(__name__)

class Table(object):
    """
    A thin abstraction layer over SQLite3 tables. This is not an ORM.
    It handles table creation, insertion, and very simple select statement.
    """
    def __init__(self, con, name, fields_desc, recreate=False):
        self.con = con
        self.name = name
        self.fields = {field.partition(' ')[0].strip('`"\'') for field in fields_desc}
        if not self.exists:
            self.__create(fields_desc)
        elif recreate:
            c = con.cursor()
            c.execute('DROP TABLE %s' % name)
            self.__create(fields_desc, cursor=c)
            c.execute('VACUUM')

    def __str__(self): # For SQL
        return '"%s"' % self.name

    def __repr__(self):
        return '<Table %s>' % self

    @property
    def exists(self):
        c = self.con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s" % self)
        return c.fetchone() is not None

    def cursor(self, cursor=None):
        return self.con.cursor() if cursor is None else cursor

    def __create(self, fields_desc, cursor=None):
        logger.info('Creating table %s : %r', self, fields_desc)
        self.cursor(cursor).execute("CREATE TABLE %s (%s)" % (self, ', '.join(fields_desc)))

    def clear(self):
        logger.info('Truncating table %s', self)
        c = self.cursor()
        c.execute("DELETE FROM %s" % self)
        c.execute("VACUUM")

    def insert(self, cursor=None, return_id=False, replace=False, **kwargs):
        logger.debug('Inserting %r into %s', kwargs, self)

        fields = [ f for f in kwargs if f in self.fields ]

        sql = 'INSERT%s INTO `%s` (%s) VALUES (%s)' % (
            ' OR REPLACE' if replace else '',
            self.name,
            ', '.join(fields),
            ', '.join(':'+f for f in fields))

        print(sql, kwargs)
        cursor = self.cursor(cursor)
        cursor.execute(sql, kwargs)
        if return_id:
            cursor.execute('SELECT last_insert_rowid()')
            return cursor.fetchone()[0]

    def __select(self, cursor=None, fields=None, where=None, **kwargs):
        if fields is None:
            fields = '*'
        else:
            fields = ', '.join(fields)
        sql = 'SELECT %s FROM %s' % (fields, self)

        on = {f:v for f,v in kwargs.items() if f in self.fields}
        where_conjs = ['%s=:%s' % (f,f) for f in on.keys()]
        if where:
            where_conjs.append('(%s)' % where)

        if where_conjs:
            sql = '%s WHERE %s' % (sql, ' AND '.join(where_conjs))

        cursor = self.cursor(cursor)
        cursor.execute(sql, on)
        return cursor

    def selectone(self, **kwargs):
        cursor = self.__select(**kwargs)
        return cursor.fetchone()

    def selectall(self, **kwargs):
        cursor = self.__select(**kwargs)
        return cursor.fetchall()
