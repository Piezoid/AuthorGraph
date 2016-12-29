import json
from urllib.parse import urlencode
import dateutil.parser as dateparser

from bibdb import Author, Ref, RefJournal, RefBook, Publication, clean_pii

import logging
logger = logging.getLogger(__name__)

def getids(record):
    ids = list()
    def append(k, v):
        if k == 'pii': # Special handling for bad piis
            assert type(v) is str
            v = clean_pii(v)
            if v is not None:
                ids.apend(Ref(k, v))
        elif type(v) is list:
            ids.extend([Ref(k, item) for item in v])
        else:
            ids.append(Ref(k, v))

    for k, v in record.items():
        if k.endswith('Id_s'):
            if k not in ['europeanProjectCallId_s']:
                append(k[:-4], v)
        elif k.endswith('_title_s'):
            append(k[:-2], v)

    pages = record.get('page_s')
    if pages:
        journalTitle = record.get('journalTitle_s')
        issue = record.get('issue_s')
        issn = record.get('journalEissn_s')
        volume = record.get('volume_s')
        if journalTitle is not None and issue is not None:
            for issue in record['issue_s']:
                ids.append(RefJournal(journalTitle, issn, issue, volume, pages))

        bookTitle = record.get('conferenceTitle_s') or record.get('bookTitle_s')
        if bookTitle:
            ids.append(RefBook(bookTitle, record.get('isbn_s'), pages))

#     if len(ids) <= 2:
#         if 'citationRef_s' in record:
#             citeref = record['citationRef_s']
#             ids.add(Ref('cite', citeref))
#         print('!!!!', ids)
    return ids


def hal_authorsearch(get, author):
    if isinstance(author, Author):
        author = str(author)

    query = {'authFullName_t': author}
    fields = ['authFullName_s', 'producedDate_tdate', '*_abstract_s', 'language_s',
              #'files_s',
              # Identification
              '*_title_s', '*Id_s', 'isbn_s', 'bookTitle_s', 'docType_s',
              # Journal
              'journalTitle_s', 'journalEissn_s', 'issue_s', 'volume_s', 'page_s',
              #'conferenceTitle_s',
              # Classifications
              #'classification_s', 'domain_s', 'acm_s', 'jel_s', 'mesh_s', 'keyword_s',
              # 'authQuality_s', 'authOrganism_s', 'labStructAcronym_s', 'structName_s',  'collaboration_s',
              #'citationRef_s'
             ]
    params = [
        ('q', ' && '.join(field+':'+ value for field, value in query.items())),
        ('fl', ','.join(fields)),
        ('wt', 'json'),
        ('rows', 10000),
    ]
    params = urlencode(params)
    r = get('https://api.archives-ouvertes.fr/search/?' + params)
    r = json.loads(r.decode('utf-8'))

    if 'response' not in r:
        print(r)
    for record in r['response']['docs']:
        refs = getids(record)
        date = dateparser.parse(record['producedDate_tdate'])
        authors = [Author(author) for author in record['authFullName_s']]

        en_abstract = record.get('en_abstract_s')
        if en_abstract is not None:
            en_abstract = ' '.join(en_abstract)

        fr_abstract = record.get('fr_abstract_s')
        if fr_abstract is not None:
            fr_abstract = ' '.join(fr_abstract)
        doctype = record.get('docType_s', 'UNDEFINED')

        yield Publication(doctype, authors, date, refs, en_abstract=en_abstract, fr_abstract=fr_abstract)

