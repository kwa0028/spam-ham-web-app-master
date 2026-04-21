import string
from pathlib import Path

import nltk
from nltk.corpus import stopwords


nltk.data.path.append(str(Path(__file__).resolve().parent / 'nltk_data'))


def text_process(message):
    noPunc = [char for char in message if char not in string.punctuation]
    noPunc = ''.join(noPunc)

    return [word for word in noPunc.split() if word not in stopwords.words('english')]
