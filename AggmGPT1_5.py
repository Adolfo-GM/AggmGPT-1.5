import math
import random
import re

from data import corpus

def correct_text(text):
    question_words = ['how', 'why', 'when', 'where', 'what', 'who', 'which', 'whose', 'whom', 'is', 'are', 
                      'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should', 'may', 'might', "what's", ]
    
    text = ' '.join(text.split())
    
    if not text:
        return text

    text = text[0].upper() + text[1:]
    
    if text[-1] in '.!?':
        text = text[:-1]
    
    words = text.lower().split()
    has_question = any(word in question_words for word in words)
    
    if has_question and ' ' in text:
        text = text.replace(' ', ', ', 1)
        text += '?' if not text.endswith('?') else ''
    else:
        text += '.' if not text.endswith('.') else ''
    
    return text

class AggmGPT1_5:
    def __init__(self, model_name='AggmGPT-1.5', max_length=1000):
        self.ModelName = model_name
        self.max_length = max_length
        self.user = 'user'
        self.ai = 'ai'
        self.minNgram = 1
        self.maxNgram = 5
        self.RED = '\033[91m'
        self.GREEN = '\033[92m'
        self.BLUE = '\033[94m'
        self.RESET = '\033[0m'
        self.ngram_models = self.train_model(corpus)

    def mat_mul(self, A, B):
        result = []
        for i in range(len(A)):
            result.append([sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))])
        return result

    def softmax(self, x):
        exp_x = [math.exp(v - max(x)) for v in x]
        sum_exp_x = sum(exp_x)
        return [e / sum_exp_x for e in exp_x]

    def self_attention(self, Q, K, V):
        scores = [[sum(Q[i][idx] * K[j][idx] for idx in range(len(Q[i]))) for j in range(len(K))] for i in range(len(Q))]
        attention_weights = [self.softmax(row) for row in scores]
        output = [[sum(attention_weights[i][k] * V[k][j] for k in range(len(V))) for j in range(len(V[0]))] for i in range(len(V))]
        return output

    def multi_head_attention(self, Q, K, V, num_heads):
        d_model = len(Q[0])
        head_size = d_model // num_heads
        outputs = []
        for head in range(num_heads):
            q_head = [row[head * head_size:(head + 1) * head_size] for row in Q]
            k_head = [row[head * head_size:(head + 1) * head_size] for row in K]
            v_head = [row[head * head_size:(head + 1) * head_size] for row in V]
            attention_output = self.self_attention(q_head, k_head, v_head)
            outputs.extend(attention_output)
        return outputs

    def positional_encoding(self, seq_len, d_model):
        encoding = [[math.sin(pos / (10000 ** (i / d_model))) if i % 2 == 0 else math.cos(pos / (10000 ** (i / d_model))) for i in range(d_model)] for pos in range(seq_len)]
        return encoding

    def add_positional_encoding(self, embeddings, positional_encodings):
        return [[val + positional_encodings[i][j] for j, val in enumerate(row)] for i, row in enumerate(embeddings)]

    def feed_forward_network(self, x):
        input_dim = len(x[0])
        hidden_dim = 10
        output_dim = 10
        W1 = [[1 if i == j else 0 for j in range(hidden_dim)] for i in range(input_dim)]
        b1 = [0] * hidden_dim
        W2 = [[1 for _ in range(output_dim)] for _ in range(hidden_dim)]
        b2 = [0] * output_dim
        hidden = [[max(0, sum(x[i][k] * W1[k][j] for k in range(len(W1))) + b1[j]) for j in range(hidden_dim)] for i in range(len(x))]
        output = [[sum(hidden[i][k] * W2[k][j] for k in range(len(W2))) + b2[j] for j in range(output_dim)] for i in range(len(hidden))]
        return output

    def tokenize(self, text):
        return text.lower().split()

    def embed_tokens(self, tokens):
        return [[random.random() for _ in range(3)] for _ in tokens]

    def build_ngram_models(self, corpus, min_n=1, max_n=5):
        ngram_models = {}
        words = self.tokenize(corpus)
        for n in range(min_n, max_n + 1):
            model = {}
            for i in range(len(words) - n):
                context = ' '.join(words[i:i+n-1])
                next_word = words[i+n-1]
                if context not in model:
                    model[context] = []
                model[context].append(next_word)
            ngram_models[f"{n}gram_model"] = model
        return ngram_models

    def predict_next_word(self, text, models):
        words = self.tokenize(text)
        for n in range(self.maxNgram, self.minNgram - 1, -1):
            if len(words) >= n - 1:
                context = ' '.join(words[-(n-1):])
                model = models.get(f"{n}gram_model", {})
                if context in model:
                    return random.choice(model[context])
        return ''

    def predict_next_word_with_attention(self, text):
        tokens = self.tokenize(text)
        d_model = 3
        embeddings = self.embed_tokens(tokens)
        positional_encodings = self.positional_encoding(len(tokens), d_model)
        encoded_embeddings = self.add_positional_encoding(embeddings, positional_encodings)
        num_heads = 1 if len(tokens) > 25 else max(1, len(tokens))
        attention_output = self.multi_head_attention(encoded_embeddings, encoded_embeddings, encoded_embeddings, num_heads)
        ff_output = self.feed_forward_network(attention_output)
        ngram_prediction = self.predict_next_word(text, self.ngram_models)
        return ngram_prediction

    def clean_user_input(self, text):
        return text.lower()

    def print_progress(self, progress, total):
        percent = (progress / total) * 100
        bar_length = 40
        filled_length = int(bar_length * progress // total)
        bar = '|' * filled_length + '-' * (bar_length - filled_length)
        print(f'{self.RED}\r[{bar}] {percent:.2f}% Complete{self.RESET}', end='')

    def train_model(self, corpus):
        print(f'{self.RED}\nTraining for {self.ModelName} has begun.{self.RESET}')
        cleaned_corpus = re.sub(r'[\r\n]+', ' ', corpus.strip())
        self.print_progress(0, 3)
        cleaned_corpus = re.sub(r'[.,!?]', '', cleaned_corpus)
        self.print_progress(1, 3)
        ngram_models = self.build_ngram_models(cleaned_corpus)
        self.print_progress(2, 3)
        self.print_progress(3, 3)
        print(f'{self.RED}\nTraining complete.{self.RESET}')
        return ngram_models

    def predict_sentence_with_attention(self, input_text, output_length):
        cleaned_input = self.clean_user_input(input_text)
        sentence = cleaned_input
        for _ in range(output_length):
            prediction = self.predict_next_word_with_attention(sentence)
            if prediction == '<|endoftext|>':
                break
            sentence += ' ' + prediction
        if cleaned_input in sentence:
            sentence = sentence.replace(cleaned_input, '', 1).strip()
        return sentence
    
    def remove_duplicates(self, text):
     words = text.split()
     unique_words = list(dict.fromkeys(words))
     return ' '.join(unique_words)

    def AskAggmGPT1_5(self, input_text):
        input_text = str(input_text).lower()
        raw_response = self.predict_sentence_with_attention(self.user + ": " + input_text.lower() + "\n" + self.ai + ": ", self.max_length)
        raw_response = str(raw_response)
        response = raw_response.replace(self.user + ": ", "").replace(self.ai + ": ", "")
        response = self.remove_duplicates(response)
        response = correct_text(response)
        return response

    def run(self):
        while True:
            input_text = input(f'{self.GREEN}\nType a message (type exit to leave): {self.RESET}')
            if input_text.lower() == 'exit':
                break
            print(f"{self.BLUE}{self.ModelName}: {self.RESET}", end="")
            response = self.AskAggmGPT1_5(input_text)
            print(f"{self.BLUE}{response}{self.RESET}")

if __name__ == "__main__":
    model = AggmGPT1_5()
    model.run()