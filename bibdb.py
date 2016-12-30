from collections import defaultdict
from functools import lru_cache
import re
import unicodedata

from lattice_containers import DeduplicatedKeysDict, DeduplicatedKeysDictOfSets, DeduplicatedSet

import logging
logger = logging.getLogger(__name__)


# Clean PIIs:
re_pii_humanchar = re.compile(r'[\(\)-/]') # Match caracter to help reading by humans
def clean_pii(pii):
    pii = re_pii_humanchar.sub(' ', pii)
    if len(pii) == 17 and pii[0] in 'SB':
        return pii
    else:
        return None

# Some text utilities :
@lru_cache(maxsize=1024)
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    ascii_form = ''.join(c for c in nfkd_form if not unicodedata.combining(c))
    if ascii_form == input_str:
        return input_str # Avoid string duplication in the cache
    else:
        return ascii_form

re_notalphanum = re.compile(r'([^\s\w]|_)+')

uninformative_name_parts = {'Mr', 'Mme', 'Mrs'}
lname_particles = {'De', 'Da', 'Le', 'El', 'Van', 'Del', 'Von', 'Zu', 'Of'}

class Author:
    def __init__(self, lname, fname=None, fname_initials=None):
        lname = re_notalphanum.sub(' ', lname)
        if fname is None and ' ' in lname:
            # By default, last name is only the last word :
            # Often the first name is in multple parts and lname in one part
            fname, sep, lname = lname.rpartition(' ')

        lname = remove_accents(lname).title()

        if fname is not None:
            fname = remove_accents(fname)

            in_fname = True
            fname_parts = []
            lname_parts = []
            initial_parts = []
            # First name is split into parts, some are kept in last name
            for name_part in fname.title().replace('-', ' ').split(' '):
                if not name_part or name_part in uninformative_name_parts:
                    continue

                initial = name_part[0]
                if len(name_part) == 1:
                    initial_parts.append(initial)
                else:
                    if name_part in lname_particles:
                        in_fname = False

                    if in_fname:
                        initial_parts.append(initial)
                        fname_parts.append(name_part)
                    else:
                        lname_parts.append(name_part)

            fname = ' '.join(fname_parts) if fname_parts else None
            if fname_initials is None:
                fname_initials = ''.join(initial_parts)

            if lname_parts: # Recovered last name parts from fname
                lname_parts.append(lname)
                lname = ' '.join(lname_parts)

        self.lname = lname
        self.fname = fname
        self.fname_initials = fname_initials

    def __str__(self):
        if self.fname:
            return '%s %s' % (self.fname, self.lname)
        elif self.fname_initials:
            return '%s. %s' % (self.fname_initials, self.lname)
        else:
            return self.lname

    __repr__ = lambda self: '<Author %s (%s.) %s>' % (self.fname, self.fname_initials, self.lname)

    def __eq__(self, other):
        if self is other: return True
        if self.lname != other.lname:
            return False

        if self.fname and other.fname:
            return self.fname == other.fname or \
                (set(self.fname.split(' ')) & set(other.fname.split(' ')))
        elif self.fname_initials and other.fname_initials:
            return len(set(self.fname_initials) & set(other.fname_initials)) > 0
        else:
            return True

    def __ior__(self, other):
        "Merge identifiers from two authors"
        neq_fname = self.fname != other.fname
        neq_fname_initials = self.fname_initials != other.fname_initials

        if not (neq_fname or neq_fname_initials):
            return self

        logger.info('Mergin authors %r <- %r', self, other)

        if neq_fname:
            if self.fname is None:
                self.fname = other.fname
            elif other.fname is not None:
                self.fname = max(self.fname, other.fname, key=lambda n: len(n.split()))

        if neq_fname_initials:
            if self.fname_initials is None:
                self.fname_initials = other.fname_initials
            elif other.fname_initials is not None:
                self.fname_initials = max(self.fname_initials, other.fname_initials, key=len)

        return self

    def __hash__(self):
        # Hard equality on last name
        return hash(self.lname)

class Ref:
    def __init__(self, reftype, ref):
        self.reftype = reftype
        if reftype.endswith('title'):
            ref = ref.rstrip('. ').lstrip().lower()
        self.ref = ref

    def _asstr(self):
        return '%s %r' % (self.reftype, self.ref)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self._asstr())

    def __hash__(self):
        return hash((self.reftype, self.ref))

    def __eq__(self, other):
        if self is other: return True
        return self.reftype == other.reftype and self.ref == other.ref

class PaginatedRef(Ref):
    "For Journals and Books"
    def __init__(self, title, pstart, pend=None):
        self.ref = title.rstrip('. ').lstrip().lower()
        if isinstance(pstart, str) and pend is None:
            pstart, pend = PaginatedRef.get_pages(pstart)
            if pstart == 1:
                pstart = None
        self.pstart = pstart
        self.pend = pend

    def includedin(self, other):
        if any([type(p) is not int
                for p in [self.pstart, other.pstart, self.pend, other.pend]]):
            return None # untestable inclusion
        return self.pstart >= other.pstart and self.pend <= other.pend

    def pstart_eq(self, other):
        if self.pstart is None or other.pstart is None:
            return None
        else:
            return self.pstart == other.pstart

    def pend_eq(self, other):
        if self.pend is None or other.pend is None:
            return None
        else:
            return self.pend == other.pend

    def __eq__(self, other):
        if self is other:
            return True
        elif not Ref.__eq__(self, other):
            return False
        elif self.includedin(other) or other.includedin(self):
            return True
        else:
            return self.pstart_eq(other) or self.pend_eq(other)

    def __ior__(self, other):
        no_pstart = self.pstart is None
        no_pend = self.pend is None
        if no_pstart or no_pend:
            if no_pstart: self.psart = other.pstart
            if no_pend and type(self.pstart) is int and type(other.pend) is int and self.pstart <= other.pend:
                self.pend = other.pend
        elif self.pstart != other.pstart or self.pend != other.pend:
            if other.includedin(self):
                # Keep most restricted page range
                self.pstart, self.pend = other.pstart, other.pend
        return self

    @staticmethod
    def get_pages(pages):
        if not pages:
            return (None, None)
        else:
            pages = pages.replace('–', '-')
            pages = pages.replace(' ', '-')
            try:
                ps = [int(i) for i in pages.split('-') if i]
            except ValueError:
                # Avoid 'np' or 'Non-Paginé' in pstart
                if any([char.isdigit() for char in pages]):
                    return (pages, None)
                else:
                    return (None, None)

            if len(ps) == 1:
                pstart = ps[0]
                return (pstart, None)
            elif len(ps) == 2:
                pstart, pend = ps
                if pstart <= pend:
                    return (pstart, pend)
                else:
                    return (pstart, None)
            else:
                return (pages, None)

    def _asstr(self):
        if self.pend is None:
            pages = str(self.pstart)
        elif self.pstart is None:
            return self.ref
        else:
            pages = '%d-%d' % (self.pstart, self.pend)
        return '%r p%s' % (self.ref, pages)

class RefBook(PaginatedRef):
    def __init__(self, title, isbn, pstart, pend=None):
        PaginatedRef.__init__(self, title, pstart, pend)
        self.isbn = isbn
        self.reftype = 'book'

    __hash__ = Ref.__hash__
    def __eq__(self, other):
        if self is other:
            return True
        elif not PaginatedRef.__eq__(self, other):
            return False
        elif self.isbn and other.isbn and self.isbn != other.isbn:
            return False
        return True

    def __ior__(self, other):
        self = super().__ior__(other)
        if self.isbn is None:
            self.isbn = other.isbn
        return self

    def _asstr(self):
        s = PaginatedRef._asstr(self)
        if self.isbn:
            return '%s (ISBN: %s)' % (s, self.isbn)
        else:
            return s


class RefJournal(PaginatedRef):
    def __init__(self, title, issn, issue, volume, pstart, pend=None):
        PaginatedRef.__init__(self, title, pstart, pend)
        self.issue = issue
        self.volume = volume
        self.issn = issn
        self.reftype = 'journal'

    __hash__ = Ref.__hash__
    def __eq__(self, other):
        if self is other:
            return True
        elif not PaginatedRef.__eq__(self, other):
            return False
        elif self.issue != other.issue or self.volume != other.volume:
            return False
        elif self.issn and other.issn and self.issn != other.issn:
            return False
        return True

    def __ior__(self, other):
        self = PaginatedRef.__ior__(self, other)
        if self.issn is None:
            self.issn = other.issn
        return self

    _asstr = lambda self: '%s issn:%s issue:%s volume:%s' % (PaginatedRef._asstr(self), self.issn, self.issue, self.volume)


prio_pubtype = {'ART': 100, 'COUV': 76, 'DOUV': 77, 'OUV': 75, 'THESE': 75, 'HDR':75, 'MEM': 75, 'COMM': 50, 'REPORT': 25, 'PATENT': 15, 'MINUTES': 15, 'SYNTHESE': 13, 'LECTURE': 12, 'NOTE': 11, 'POSTER': 10, 'OTHERREPORT':7, 'SON': 7, 'MAP': 7, 'OTHERREPORT': 6, 'PRESCONF': 6, 'OTHER': 5, 'IMG': 4, 'VIDEO': 4, 'UNDEFINED': 0, None: 0}

class Publication:
    def __init__(self, pubtype, authors, date, refs=set(), en_abstract=None, fr_abstract=None):
        self.pubtype = pubtype.upper()
        self.date = date
        self.authors = authors

        if en_abstract and len(en_abstract) >= 100:
            # Normalization over split characters :
            en_abstract = ' '.join(x for x in en_abstract.split() if x)
            self.en_abstract = en_abstract
            en_abstract_ref = Ref('en_abstract', en_abstract)
            if type(refs) is list:
                refs.append(en_abstract_ref)
            else:
                refs.add(en_abstract_ref)
        else:
            self.en_abstract = None

        if fr_abstract and len(fr_abstract) >= 100:
            # Normalization over split characters :
            fr_abstract = ' '.join(x for x in fr_abstract.split() if x)
            self.fr_abstract = fr_abstract
            fr_abstract_ref = Ref('fr_abstract', fr_abstract)
            if type(refs) is list:
                refs.append(fr_abstract_ref)
            else:
                refs.add(fr_abstract_ref)
        else:
            self.fr_abstract = None


        self.refs = refs
        self.titles = {ref.ref for ref in self.refs if ref.reftype.endswith('_title')}

    @property
    def title(self):
        for title in self.titles:
            return title
        else:
            return None

    def __repr__(self):
        return '<Publication %s %r>' % (self.pubtype, self.title)

    def __eq__(self, other):
        if self is other: return True # Fast path
        # At least one reference in common
        elif len(self.refs & other.refs) == 0: return False
        #elif self.date != other.date:
            #logger.warning('Date mismatch %r (%r)\n\t%r (%r)', self, self.date, other, other.date)
            #return False
        elif self.authors == other.authors:
            return True
        elif len(self.titles & other.titles) > 0:
            return True
        else:
            return False

    def __ior__(self, other):
        logger.info('Merging %r <- %r', self, other)

        assert isinstance(self.refs, DeduplicatedSet)
        self.refs |= other.refs

        assert isinstance(self.authors, DeduplicatedSet)
        self.authors |= other.authors

        self.titles |= other.titles

        self.pubtype = max(self.pubtype, other.pubtype, key=prio_pubtype.get)

        if self.en_abstract is None:
            self.en_abstract = other.en_abstract
        elif other.en_abstract is not None:
            if self.en_abstract != other.en_abstract:
                logger.info('Different abastracts for %r', self)
                self.en_abstract = max(self.en_abstract, other.en_abstract, key=len)

        if self.fr_abstract is None:
            self.fr_abstract = other.fr_abstract
        elif other.fr_abstract is not None:
            if self.fr_abstract != other.fr_abstract:
                logger.info('Different french abastracts for %r', self)
                self.fr_abstract = max(self.fr_abstract, other.fr_abstract, key=len)
        return self

    __hash__ = lambda self: id(self)
    __hash__.__doc__ = """
        PubDB ensure the uniqueness of Publications, in respect to __eq__.
        If this uniqueness is not respected __hash__ will not collide on equal Publications:
        Publication not deduplicated by PubDB should not be placed in a hash index.
    """

class PubDB:
    def __init__(self):
        self.ref2pub = DeduplicatedKeysDict()
        self.author_pubs = DeduplicatedKeysDictOfSets()

    def lookup_byrefs(self, refs):
        results = {}
        for ref in refs:
            pub = self.ref2pub.get(ref)
            if pub is not None:
                yield ref, pub


    def get(self, refs, authors):
        authors = set(authors)
        if isinstance(refs, Ref):
            refs = [refs]

        pub_visited = set()
        for ref in refs:
            pub = self.ref2pub.get(ref)
            if pub is None or pub.authors != authors:
                continue
            pub_visited.add(pub)

        if pub_visited:
            publications = list(pub_visited)
            if len(publications) > 1:
                raise ValueError('More than one publications (%r) were found using refs %r' % (publications, common_refs))
            else:
                return publications[0]

    def add_pub(self, pub):
        ref2existing_pubs = defaultdict(set) # Count the number of shared refs
        existing_pub = None
        for ref, existing_pub_candidate in self.lookup_byrefs(pub.refs):
            if not isinstance(ref, PaginatedRef) or type(ref.pstart) is int:
                ref2existing_pubs[existing_pub_candidate].add(ref)
            if existing_pub_candidate == pub: # Exact match as eq
                existing_pub = existing_pub_candidate
                break
        # If no exact match :
        if existing_pub is None and ref2existing_pubs:
            # Publication with the highest number of matching refs :
            existing_pub, refs = max(ref2existing_pubs.items(), key=lambda x: len(x[1]))
            logger.warning('Merging\t   %r\n\t<- %r\n\ton behalf of: %r', existing_pub, pub, refs)

        if existing_pub is not None:
            existing_pub |= pub # merge information from pub with the publication already presentin the db
            # update our indexes:
            self.ref2pub.update({ref: existing_pub for ref in existing_pub.refs})
            self.author_pubs.update({author: existing_pub for author in existing_pub.authors})
        else:
            # Both sets in the new Publication now share objects from our PubDB indexes:
            pub.refs = DeduplicatedSet(self.ref2pub.update({ref: pub for ref in pub.refs}))
            pub.authors = DeduplicatedSet(self.author_pubs.update({author: pub for author in pub.authors}))
