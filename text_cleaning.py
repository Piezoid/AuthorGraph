import nltk
import re
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.stem import WordNetLemmatizer
porter_stemmer = PorterStemmer()
wordnet_lemmatizer = WordNetLemmatizer()


#abstract => texte à traiter
#language => fr ou en
#option => stem or lem
#namelist_output => sortie de traitement
def text_cleaning(abstract, language, option, name_list_output):
    name_list_output = []

    #tokenization
    abstract_tokenize_list = nltk.word_tokenize(abstract)
    abstract_tokenize_list = [w.lower() for w in abstract_tokenize_list if True or w.isalnum()]

    #delete stop words
    if language == 'en':
        english_stopwords = set(stopwords.words('english'))
        abstract_stopwords = [i for i in abstract_tokenize_list if i not in english_stopwords]
    if language == 'fr':
        french_stopwords = set(stopwords.words('french'))
        abstract_stopwords = [i for i in abstract_tokenize_list if i not in french_stopwords]

    #Stemming
    if option == "stem":
        for i in abstract_stopwords:
            word_stemming = porter_stemmer.stem(i)
            expression_prohibited = re.sub("[ .,;:\n\t\r]", '', word_stemming)
            if expression_prohibited != '':
                name_list_output.append(word_stemming)

    #Lemmatization
    if option == "lem":
        tb2wn = {'J': wordnet.ADJ, 'V': wordnet.VERB, 'N': wordnet.NOUN, 'R': wordnet.ADV}
        for w, pos in nltk.pos_tag(abstract_stopwords):
            word_lemmatization = wnl.lemmatize(w, pos=tb2wn.get(pos[0], 'n'))
            expression_prohibited = re.sub("[ .,;:\n\t\r]", '', word_lemmatization)
            if expression_prohibited != '':
                name_list_output.append(word_lemmatization)
    
    return name_list_output
               
            
language = 'en'
option = "lem" #stem or lem
abstract = "Emerging data implicates ubiquitination, a post-translational modification, in regulating essential cellular events, one of them being mitosis. In this review we discuss how various E3 ligases modulate the cortical proteins such as dynein, LGN, NuMa, Gα, along with polymerization, stability, and integrity of spindles. These are responsible for regulating symmetric cell division. Some of the ubiquitin ligases regulating these proteins include PARK2, BRCA1/BARD1, MGRN1, SMURF2, and SIAH1; these play a pivotal role in the correct positioning of the spindle apparatus. A direct connection between developmental or various pathological disorders and the ubiquitination mediated cortical regulation is rather speculative, though deletions or mutations in them lead to developmental disorders and disease conditions."
text_cleaning(abstract, language, option, "sortie")