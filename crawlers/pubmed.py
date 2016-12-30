import json
from urllib.parse import urlencode
from datetime import datetime
from xml.etree import ElementTree as ET

from bibdb import Author, Ref, RefJournal, Publication, clean_pii

import logging
logger = logging.getLogger(__name__)


def esearch(get, term):
    if isinstance(term, str):
        pass
    elif isinstance(term, Author):
        author = term
        if author.fname:
            term = "%s, %s[FAU] " % (author.lname, author.fname)
        elif author.fname_initials:
            term = "%s %s[AU]" % (author.lname, author.fname_initials)
        else:
            term = "%s[AU] " % author.lname
    else:
        raise TypeError('Only search by Author is implemented')

    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?' + urlencode([
            ('term', term),
            ('retmode', 'json'),
            ('retmax', '1000')
        ])
    res = json.loads(get(url).decode('utf-8'))['esearchresult']

    if int(res['count']) >= 400:
        logger.warning('Skipping %r, having more than 400 results.', term)
        return []

    return res['idlist']


def efetch(get, pubmedid):
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urlencode([
                ('id', pubmedid),
                ('db', 'pubmed'),
                ('retmode', 'xml')
            ])
    xmldoc = ET.fromstring(get(url))

    medart = xmldoc.find('PubmedArticle')
    if medart is None:
        return None # TODO: handle books

    medcite = medart.find('MedlineCitation')
    article = medcite.find('Article')
    journal = article.find('Journal')
    language = article.find('Language').text

    created = medcite.find('DateCreated')
    created = datetime(int(created.find('Year').text),
                    int(created.find('Month').text),
                    int(created.find('Day').text))

    pubtypes = [pubtype.text for pubtype in article.findall('PublicationTypeList/PublicationType')]
    if 'Journal Article' in pubtypes or 'Introductory Journal Article' in pubtypes:
        pubtype = 'ART'
    elif 'Case Reports' in pubtypes:
        pubtype = 'REPORT'
    else:
        pubtype = 'OTHER'

    refs = []
    for article_id in medart.findall('PubmedData/ArticleIdList/ArticleId'):
        reftype = article_id.get('IdType')
        ref = article_id.text.strip()
        if reftype == 'pii':
            ref = clean_pii(ref)
            if ref is None:
                continue
        refs.append(Ref(reftype, ref))

    language = article.find('Language').text[:2].lower()
    title = article.find('ArticleTitle').text
    abstract = ' '.join(at.text.strip() for at in  article.findall('Abstract/AbstractText') if at.text)
    if language == 'en':
        en_abstract = abstract
        if title is not None:
            refs.append(Ref('en_title', title))
    else:
        en_abstract = None
    if language == 'fr':
        fr_abstract = abstract
        if title is not None:
            refs.append(Ref('fr_title', title))
    else:
        fr_abstract = None

    pages = getattr(article.find('Pagination/MedlinePgn'), 'text', None)
    if pages is not None:
        issn = getattr(journal.find('ISSN'), 'text', None)
        journaltitle = journal.find('Title').text
        ji = journal.find('JournalIssue')
        issue = getattr(ji.find('Issue'), 'text', 1)
        volume = getattr(ji.find('Volume'), 'text', 1)

        refs.append(RefJournal(journaltitle, issn, issue, volume, pages))

    authors = []
    for auth in article.findall('AuthorList/Author'):
        lname = getattr(auth.find('LastName'), 'text', None)
        fname = getattr(auth.find('ForeName'), 'text', None)
        initials = getattr(auth.find('Initials'), 'text', None)
        if lname is None:
            if auth.find('CollectiveName') is None:
                logger.warn('Invalid Author format: %s', ET.tostring(auth, 'utf-8').decode('utf-8'))
            continue
        authors.append(Author(lname, fname, initials))

    #meshs = [e.text for e in medcite.findall('MeshHeadingList/MeshHeading/DescriptorName')]

    #keywords = [kw.text for kw in medcite.findall('KeywordList/Keyword')]

    pub = Publication(pubtype, authors, created, refs, en_abstract, fr_abstract)

    return pub

def pubmed_authorsearch(get, author):
    for pmid in esearch(get, author):
        pub = efetch(get, pmid)
        if pub is not None and author in pub.authors:
            yield pub
