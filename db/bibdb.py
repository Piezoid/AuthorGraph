import logging
logger = logging.getLogger(__name__)

from .table import Table

class BibDB:
    def __init__(self, con, drop_docs=False, drop_refs=False, drop_authors=False, drop_texts=False):
        self.con = con

        self.docTable = Table(con, 'docs', [
                'doc_id INTEGER PRIMARY KEY AUTOINCREMENT',
                'type CHAR(10) NOT NULL', # hal code : ART COMM COUV THESE UNDEFINED IMG OTHER REPORT OUV DOUV MEM POSTER HDR PATENT LECTURE VIDEO PRESCONF NOTE OTHERREPORT MAP SON SYNTHESE MINUTES
                'date TIMESTAMP'], recreate=drop_docs)

        doc_foreign = 'doc_id REFERENCES docs(doc_id) ON DELETE CASCADE NOT NULL'

        self.refTable = Table(con, 'refs', [
                doc_foreign,
                'reftype CHAR(16) NOT NULL',
                'ref TEXT NOT NULL'
            ], recreate=drop_refs or drop_docs)

        self.refJournalTable = Table(con, 'refs_journals', [
                doc_foreign,
                'title TEXT NOT NULL',
                'issue INTEGER NOT NULL',
                'pstart INTEGER NOT NULL',
                'pend INTEGER'
            ], recreate=drop_refs or drop_docs)

        self.refBookTable = Table(con, 'refs_books', [
                doc_foreign,
                'title TEXT NOT NULL',
                'isbn CHAR(17)',
                'pstart INTEGER NOT NULL',
                'pend INTEGER'
            ], recreate=drop_refs or drop_docs)

        self.authorTable = Table(con, 'authors', [
                'author_id INTEGER PRIMARY KEY AUTOINCREMENT',
                'fname TEXT',
                'lname TEXT NOT NULL',
                'fname_initials TEXT NOT NULL'
            ], recreate=drop_authors)

        author_foreign = 'author_id REFERENCES authors(author_id) ON DELETE CASCADE NOT NULL'
        self.authorship = Table(con, 'authorships', [
                doc_foreign,
                author_foreign,
                'quality CHAR(3)'
            ], recreate=drop_authors or drop_docs)

        self.textTable = Table(con, 'texts', [
                'text_id INTEGER PRIMARY KEY AUTOINCREMENT',
                doc_foreign,
                'type CHAR(8) NOT NULL', # fulltext, abstract
                'lang CHAR(2) NOT NULL',
                'content BLOB NOT NULL'
            ], recreate=drop_texts or drop_docs)

    def insert_ref(self, doc_id, reftype, ref):
        if reftype == 'journal':
            title, issue, pstart, pend = ref
            self.refJournalTable.insert(doc_id=doc_id, **ref)
        elif reftype == 'book':
            title, isbn, pstart, pend = ref
            self.refBookTable.insert(doc_id=doc_id, **ref)
        else:
            self.refTable.insert(doc_id=doc_id, reftype=reftype, ref=ref)


    def docid_byref(self, refs):
        if len(refs) == 0:
            return None

        values = {}
        unions = [] # list of SELECTs merged together

        for reftype, ref in refs:
            if reftype == 'journal':
                title, issue, pstart, pend = ref
                values['journal_title'] = title
                values['journal_issue'] = issue
                values['journal_pstart'] = pstart
                unions.append('SELECT doc_id FROM refs_journals WHERE '+\
                            'title=:journal_title AND issue=:journal_issue AND pstart=:journal_pstart')
            elif reftype == 'book':
                title, isbn, pstart, pend = ref
                values['book_title'] = title
                values['book_pstart'] = pstart
                unions.append('SELECT doc_id FROM refs_books WHERE ' +\
                            'title=:book_title AND pstart=:book_pstart')
            else:
                unions.append('SELECT doc_id FROM refs WHERE reftype="{0}" AND ref=:{0}'.format(reftype))
                values[reftype] = ref

        sql = '\nUNION\n'.join(unions)
        results = self.con.execute(sql, values).fetchall()
        if len(results) == 0:
            return None
        if not all(res == results[0] for res in results[1:]):
            print(results)
        return results[0][0]
