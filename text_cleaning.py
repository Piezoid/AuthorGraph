import re
from nltk import word_tokenize, pos_tag
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

from functools import lru_cache

#
# Word cleaning : clean_word
#

stop_words = set(stopwords.words('english'))
re_prohibited = re.compile("[ .,;:()\n\t\r]")
re_number = re.compile(r"[-+]?\d+([\.,]\d+)?$")

def clean_word(w):
    w = w.lower()
    if w in stop_words:
        return None
    w = re_prohibited.sub('', w)
    if not w or (not w.isalnum() and len(w)==1):
        return None
    if re_number.match(w):
        w = '[number]'
    return w

cached_clean_word = lru_cache(maxsize=4096)(clean_word)

wordnet_lemmatizer = WordNetLemmatizer()
# Penn Treebank tagger tags (first letter) to wordnet tag:
tb2wn = {'J': wordnet.ADJ,
         'V': wordnet.VERB,
         'N': wordnet.NOUN,
         'R': wordnet.ADV}


@lru_cache(maxsize=4096)
def clean_lematize_word(w, tag):
    wn_postag = tb2wn.get(tag[0], wordnet.NOUN)
    w = clean_word(w)
    if w is None:
        return None
    else:
        w = wordnet_lemmatizer.lemmatize(w, pos=wn_postag)
        return '%s/%s' % (w, tag)

#
# Main function : text_cleaning
#
porter_stemmer = PorterStemmer()

#abstract => texte à traiter
#option => stem or lem
#namelist_output => sortie de traitement
def text_cleaning(text, option='lem'):
    #tokenization
    output = word_tokenize(text)

    #Stemming
    if option == "stem":
        output = (cached_clean_word(porter_stemmer.stem(i))
                  for i in output)
    #Lemmatization
    elif option == "lem":
        output = (clean_lematize_word(w, tag[:2])
                  for w, tag in pos_tag(output))

    return [w for w in output if w is not None]
