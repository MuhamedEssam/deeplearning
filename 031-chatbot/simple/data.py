import os
import io
import re
import pickle
import errno
from .utils.file_helper import file_exists, try_create_dir
# from urllib.request import urlopen
from urllib2 import urlopen
import numpy as np
from pprint import pprint

from .utils.pprint_helper import Head

# List of NLP tokens
tokens = ['<PAD>', '<EOS>', '<OUT>', '<SOS>']


def clean_text(text):
    """
    English helper to clean text
    :param text:
    :return:
    """
    text = text.lower()
    text = re.sub(r"i'm", 'i am', text)
    text = re.sub(r"he's", 'he is', text)
    text = re.sub(r"she's", 'she is', text)
    text = re.sub(r"that's", 'that is', text)
    text = re.sub(r"what's", 'what is', text)
    text = re.sub(r"where's", 'where is', text)
    text = re.sub(r"\'ll", ' will', text)
    text = re.sub(r"\'ve", ' have', text)
    text = re.sub(r"\'re", ' are', text)
    text = re.sub(r"\'d", ' would', text)
    text = re.sub(r"won't", 'will not', text)
    text = re.sub(r"can't", 'cannot', text)
    text = re.sub(r"[-()\"#/@;:<>{}+=~|.?,]", '', text)
    return text


def convert_string2int(question, word2int):
    """
	Converting the raw string question to an integer representation
	:param question:
	:param word2int:
	:return:
	"""
    question = clean_text(question)
    return [word2int.get(word, word2int['<OUT>']) for word in question.split()]


def convert_word_to_count(counter={}, doc=[]):
    """
    In-memory based simple word_to_count
    :param counter: Counter object to be returned
    :param doc: an entire document
    :return:
    """
    for sentence in doc:
        for word in sentence.split():
            if word not in counter:
                counter[word] = 1
            else:
                counter[word] += 1
    return counter


def save_file_data(name, obj):
    """
    Saving an object as a file using pickle
    :param name:
    :param obj:
    :return:
    """
    filename = './data/{}.pkl'.format(name)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:    # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    with open(filename.format(name), 'wb+') as output:
        pickle.dump(obj, output)


def read_file_data(name):
    """
    Reading
    :param name:
    :return:
    """
    filename = './data/{}.pkl'.format(name)
    with open(filename, 'rb') as input:
        return pickle.load(input)


cornell_file_urls = [('movie_lines.txt', 'https://www.dropbox.com/s/sljz3iejzfrwf5b/movie_lines.txt?dl=1'),
                     ('movie_conversations.txt',
                      'https://www.dropbox.com/s/nk0r6raow7xkr8b/movie_conversations.txt?dl=1')]


class Cornell:
    sorted_clean_questions = None
    sorted_clean_answers = None
    questions_words_2_counts = None
    answers_words_2_counts = None
    answers_counts_2_words = None
    num_questions_word2count = 0    # Number of total word2count in questions dict
    num_answers_word2count = 0    # Number of total word2count in answers dict

    # Train test split
    training_validation_split = 0
    training_questions = None
    training_answers = None
    validation_questions = None
    validation_answers = None

    # System
    input_dir = '/inputs'
    output_dir = '/output'

    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir

    def load(self):
        (self.sorted_clean_questions, self.sorted_clean_answers, self.questions_words_2_counts,
         self.answers_words_2_counts, self.answers_counts_2_words) = self._process_count_vectorization()
        self.num_questions_word2count = len(self.questions_words_2_counts)
        self.num_answers_word2count = len(self.answers_words_2_counts)

        # Train test split
        self.training_validation_split = int(len(self.sorted_clean_questions) * 0.15)
        self.training_questions = self.sorted_clean_questions[self.training_validation_split:]
        self.training_answers = self.sorted_clean_answers[self.training_validation_split:]
        self.validation_questions = self.sorted_clean_questions[:self.training_validation_split]
        self.validation_answers = self.sorted_clean_answers[:self.training_validation_split]

    def download_if_not_exist(self):
        """
		Downloads required data file for cornell if it does not exists already
		:return:
		"""
        for (fname, furl) in cornell_file_urls:
            # dir_path = os.path.dirname(os.path.realpath(__file__))
            input_folder = '{input_dir}/cornell'.format(input_dir=self.input_dir)
            full_dirname = input_folder
            full_fname = '/'.join([full_dirname, fname])
            if not file_exists(full_fname):
                remote_file = urlopen(furl)
                data = remote_file.read()
                remote_file.close()
                # Try creating the dir
                try_create_dir(full_dirname)
                print('download if not exist fname:', fname, 'url:', furl)
                # Write the file
                with open(full_fname, 'wb') as f:
                    f.write(data)

    def _get_data(self):
        """
				:return: raw questions and answers
				"""
        print('Checking inputs cornell folder')
        print(os.listdir('{input_dir}/cornell'.format(input_dir=self.input_dir)))
        movie_line_path = '{input_dir}/cornell/movie_lines.txt'.format(input_dir=self.input_dir)
        lines = io.open(movie_line_path, encoding='utf8', errors='ignore').read().split('\n')
        conversation_path = '{input_dir}/cornell/movie_conversations.txt'.format(input_dir=self.input_dir)
        conversations = io.open(
            conversation_path, encoding='utf8', errors='ignore').read().split('\n')

        id2line = {}
        """
				Step 1: Creating a dict that maps each line to its id
				"""

        pprint('---- Step 1 creating a dict of id2lines ----')
        pprint('Original lines')
        pprint(lines, stream=Head(5))
        print('\n')

        for line in lines:
            _line = line.split(' +++$+++ ')
            if len(_line) == 5:
                id2line[_line[0]] = _line[4]

        pprint('processed')
        pprint(id2line, stream=Head(5))
        print('\n')
        print('Validating data')
        for line in lines[:5]:
            _line = line.split(' +++$+++ ')
            if len(_line) == 5:
                pprint(id2line[_line[0]])
        print('\n\n')
        """
				Step 2: Creating a list of all of the conversations
				"""

        conversations_ids = []
        pprint('----- Step 2 creating conversation ids ----')
        pprint('Original conversations:')
        pprint(conversations, stream=Head(5))
        print('\n')

        for conversation in conversations[:-1]:
            # Example: u0 +++$+++ u2 +++$+++ m0 +++$+++ ['L194', 'L195', 'L196', 'L197']
            _convo = conversation.split(' +++$+++ ')[-1][1:-1].replace("'", '').replace(' ', '')
            conversations_ids.append(_convo.split(','))

        pprint('processed')
        pprint(conversations_ids, stream=Head(10))
        print('\n\n')
        """
				Step 3: Creates questions and answers sequence according to conversation_ids
				"""

        questions = []
        answers = []
        pprint('---- Step 3 constructing sequence ----')
        pprint(conversations_ids, stream=Head(5))
        for conversation_id in conversations_ids:
            for i in range(len(conversation_id) - 1):
                questions.append(id2line[conversation_id[i]])
                answers.append(id2line[conversation_id[i + 1]])

        print('\nChecking questions sequences')
        pprint(questions, stream=Head(5))
        print('\nChecking answers sequences')
        pprint(answers, stream=Head(5))
        print('\n\n')
        """
				Documents of questions and answers 1:1 mapped based on Cornell Movie Corpus Dialog
				"""
        return questions, answers

    def _process_count_vectorization(self, lazy=True):
        """
        Process in-memory word2vec
        :param type:
        :param lazy:
        :return:
        """
        # Handle lazy load
        if lazy:
            try:
                sorted_clean_questions = read_file_data('sorted_clean_questions')
                sorted_clean_answers = read_file_data('sorted_clean_answers')
                questions_words_2_counts = read_file_data('questions_words_2_counts')
                answers_words_2_counts = read_file_data('answers_words_2_counts')
                answers_counts_2_words = read_file_data('answers_counts_2_words')
                return sorted_clean_questions, sorted_clean_answers, questions_words_2_counts, answers_words_2_counts, answers_counts_2_words
            except Exception as e:
                print('Lazy load failed:', e)
                pass

        questions = []
        answers = []

        questions, answers = self._get_data()

        # Step 4: cleaning the questions
        pprint('---- Step 4 cleaning questions ----')

        clean_questions = []
        for question in questions:
            clean_questions.append(clean_text(question))

        pprint(clean_questions, stream=Head(5))
        print('\n\n')
        """
    	  Step 5: Clean the answers
    	  """

        pprint('---- Step 5 cleaning answers ----')
        clean_answers = []
        for answer in answers:
            clean_answers.append(clean_text(answer))

        pprint(clean_answers, stream=Head(5))
        print('\n\n')
        """
    	  Step 6: Creating a dictionary that maps each word to its number of occurences
    	  """

        word2count = {}
        pprint('------ Step 6: counting words in questions ----')

        word2count = convert_word_to_count(word2count, clean_questions)

        pprint(word2count, stream=Head(5))
        print('\n\n')
        """
    	  Step 7:
    	  For example, for a question: can we make this quick  roxanne korrine and andrew barrett are having an incredibly horrendous public break up on the quad  again
    	  It counts each word occurence such as "can" and accumulates the count into word2count dict
    	  """
        pprint('------ Step 6: counting words in answers ----')

        word2count = convert_word_to_count(word2count, clean_answers)

        pprint(word2count, stream=Head(5))
        print('\n\n')
        """
    	  Step 8: Creating word 2 int(count) by filtering words that are greater than the threshold
    	  """

        pprint('------ Step 8: questions_words_2_int(count) filtered by threshold (>) ----')
        threshold_questions = 20
        questions_words_2_counts = {}
        word_number = 0
        for word, count in word2count.items():
            if count >= threshold_questions:
                questions_words_2_counts[word] = word_number
                word_number += 1

        pprint(questions_words_2_counts, stream=Head(5))
        print('\n\n')
        """
    	  Step 9: Same as step 8 but for answers
    	  """
        pprint('------ Step 9: answers_words_2_counts(count) filtered by threshold (>) ----')
        threshold_answers = 20
        answers_words_2_counts = {}
        word_number = 0
        for word, count in word2count.items():
            if count >= threshold_answers:
                answers_words_2_counts[word] = word_number
                word_number += 1

        pprint(answers_words_2_counts, stream=Head(5))
        print('\n\n')
        """
    	  Step 10: Adding the last tokens to these two dictionaries
    	  """
        pprint('------ Step 10: Adding token counts for questions_words_2_counts ----')
        for token in tokens:
            questions_words_2_counts[token] = len(questions_words_2_counts) + 1
            pprint((token, ':', questions_words_2_counts[token]))

        print('\n\n')

        pprint('------ Step 11: Adding token counts for answers_words_2_counts ----')
        for token in tokens:
            answers_words_2_counts[token] = len(answers_words_2_counts) + 1
            pprint((token, ':', answers_words_2_counts[token]))

        print('\n\n')
        """
    	  Step 12: Creating an inverse dictionary of the word:count to count:word
    	  """
        pprint('------ Step 12: Creating an inverse dictionary of the word:count to count:word ----')

        answers_counts_2_words = {c: w for w, c, in answers_words_2_counts.items()}

        pprint(answers_counts_2_words, stream=Head(5))
        print('\n\n')

        # TODO: Check the Seq2Seq diagram to understand this
        pprint('------ Step 13: Adding the EOS to every answer ----')

        for i in range(len(clean_answers)):
            clean_answers[i] += ' <EOS>'

        pprint(clean_answers, stream=Head(5))
        print('\n\n')
        """
    	  Step 13: Translating all the questions and answers into counts
    	  and replacing all the words that were filtered out by OUT
    	  """
        pprint('Step 13: Translating all the questions into counts; replacing unknown words with OUT token')

        questions_to_counts = []
        for question in clean_questions:
            counts = []
            for word in question.split():
                if word not in questions_words_2_counts:
                    counts.append(questions_words_2_counts['<OUT>'])
                else:
                    counts.append(questions_words_2_counts[word])
            questions_to_counts.append(counts)

        pprint(questions_to_counts, stream=Head(5))
        print('\n\n')
        """
    	  Step 14: Same as step 13 except for it's targeting answers
    	  """
        pprint('Step 14: Translating all the answers into counts; replacing unknown words with OUT token')

        answers_to_counts = []
        for answer in clean_answers:
            counts = []
            for word in answer.split():
                if word not in answers_words_2_counts:
                    counts.append(answers_words_2_counts['<OUT>'])
                else:
                    counts.append(answers_words_2_counts[word])
            answers_to_counts.append(counts)

        pprint(answers_to_counts, stream=Head(5))
        print('\n\n')
        """
        Step 15: Sorting questions and answers by the length of questions
    	  tip: look at CounterVectorizer
    	  """
        pprint('Step 15: Sorting questions and answers counts')

        sorted_clean_questions = []
        sorted_clean_answers = []
        for length in range(1, 25 + 1):
            for i in enumerate(questions_to_counts):
                if len(i[1]) == length:
                    sorted_clean_questions.append(questions_to_counts[i[0]])
                    sorted_clean_answers.append(answers_to_counts[i[0]])

        pprint('sorted_clean_questions')
        print('')
        pprint(sorted_clean_questions, stream=Head(5))
        print('\n')
        pprint('sorted_clean_answers')
        print('')
        pprint(sorted_clean_answers, stream=Head(5))
        print('\n\n')
        """
    	  1. sorted_clean_questions: list of processed questions
    	  2. sorted_clean_answers: list of processed answers
    	  3. answers_counts_2_words: list of ints lookup word table
    	  """

        # Saving
        if lazy:
            save_file_data('sorted_clean_questions', sorted_clean_questions)
            save_file_data('sorted_clean_answers', sorted_clean_answers)
            save_file_data('questions_words_2_counts', questions_words_2_counts)
            save_file_data('answers_words_2_counts', answers_words_2_counts)
            save_file_data('answers_counts_2_words', answers_counts_2_words)
        return sorted_clean_questions, sorted_clean_answers, questions_words_2_counts, answers_words_2_counts, answers_counts_2_words

    def _apply_padding(self, batch_of_sequences, word2int):
        """
        Padding the sequence with the <PAD> token
        :param batch_of_sequences:
        :param word2int:
        :return: ['something', '<PAD>', '<PAD>', '<PAD>', '<PAD>', '<PAD>'] <- depends on max_sequence_length
        """
        max_sequence_length = max([len(sequence) for sequence in batch_of_sequences])
        return [
            sequence + [word2int['<PAD>']] * (max_sequence_length - len(sequence)) for sequence in batch_of_sequences
        ]

    def _get_next_batch(self, batch_index, batch_size, questions, answers):
        """
		Getting padded questions and answers of batch index and size
		This method is only used internally.
		:param batch_index:
		:param batch_size:
		:param questions:
		:param answers:
		:return:
		"""
        start_index = batch_index * batch_size
        questions_in_batch = questions[start_index:start_index + batch_size]
        answers_in_batch = answers[start_index:start_index + batch_size]
        padded_questions_in_batch = np.array(self._apply_padding(questions_in_batch, self.questions_words_2_counts))
        padded_answers_in_batch = np.array(self._apply_padding(answers_in_batch, self.answers_words_2_counts))
        return padded_questions_in_batch, padded_answers_in_batch

    def get_next_batch(self, batch_index, batch_size):
        """
		start_index = batch_index * batch_size
		questions_in_batch = self.training_questions[start_index:start_index + batch_size]
		answers_in_batch = self.training_answers[start_index:start_index + batch_size]
		padded_questions_in_batch = np.array(self._apply_padding(questions_in_batch, self.questions_words_2_counts))
		padded_answers_in_batch = np.array(self._apply_padding(answers_in_batch, self.answers_words_2_counts))
		return padded_questions_in_batch, padded_answers_in_batch
		"""
        return self._get_next_batch(
            batch_index=batch_index,
            batch_size=batch_size,
            questions=self.training_questions,
            answers=self.training_answers)

    def get_next_valid_batch(self, batch_index, batch_size):
        return self._get_next_batch(
            batch_index=batch_index,
            batch_size=batch_size,
            questions=self.validation_questions,
            answers=self.validation_answers)

    def get_word2int(self, word):
        return self.questions_words_2_counts[word]


class Dataset:
    sub = None    # Dataset object
    type = 'cornell'
    output_dir = '/output'
    inputs_dir = '/inputs'

    def __init__(self, FLAGS):
        self.output_dir = FLAGS.output
        self.inputs_dir = FLAGS.input

    def load(self):
        if self.type == 'cornell':
            self.sub = Cornell(
                input_dir=self.inputs_dir,
                output_dir=self.output_dir
            )

        if self.sub:
            self.sub.download_if_not_exist()
            self.sub.load()
        else:
            raise Exception('Invalid dataset!')

    def get_batches(self, batch_size):
        # training_questions = self.sub.sorted_clean_questions[self.sub.training_validation_split:]
        for batch_index in range(0, len(self.sub.training_questions) // batch_size):
            yield self.sub.get_next_batch(batch_index, batch_size)

    def get_validation_batches(self, batch_size):
        # validation_questions = self.sub.sorted_clean_questions[:self.sub.training_validation_split]
        for batch_index in range(0, len(self.sub.validation_questions) // batch_size):
            yield self.sub.get_next_valid_batch(batch_index, batch_size)


def main():
    ds = Dataset()
    ds.load()

    for index, val in enumerate(ds.get_batches(25)):
        print('training: index', index, 'val', val)

    for index, val in enumerate(ds.get_validation_batches(25)):
        print('valid: index', index, 'val', val)


if __name__ == "__main__":
    main()
