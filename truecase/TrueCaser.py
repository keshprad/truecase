import math
import os
import pickle
import string
from typing import Callable

import nltk
from nltk.tokenize import word_tokenize
from nltk.tokenize.treebank import TreebankWordDetokenizer


class TrueCaser(object):
    def __init__(self, dist_file_path=None):
        """ Initialize module with default data/english.dist file """
        if dist_file_path is None:
            dist_file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "data/english.dist")

        with open(dist_file_path, "rb") as distributions_file:
            pickle_dict = pickle.load(distributions_file)
            self.uni_dist = pickle_dict["uni_dist"]
            self.backward_bi_dist = pickle_dict["backward_bi_dist"]
            self.forward_bi_dist = pickle_dict["forward_bi_dist"]
            self.trigram_dist = pickle_dict["trigram_dist"]
            self.word_casing_lookup = pickle_dict["word_casing_lookup"]
        self.detknzr = TreebankWordDetokenizer()

    def get_score(self, prev_token, possible_token, next_token):
        pseudo_count = 5.0

        # Get Unigram Score
        numerator = self.uni_dist[possible_token] + pseudo_count
        denominator = 0
        for alternativeToken in self.word_casing_lookup[
                possible_token.lower()]:
            denominator += self.uni_dist[alternativeToken] + pseudo_count

        unigram_score = numerator / denominator

        # Get Backward Score
        bigram_backward_score = 1
        if prev_token is not None:
            numerator = (
                self.backward_bi_dist[prev_token + "_" + possible_token] +
                pseudo_count)
            denominator = 0
            for alternativeToken in self.word_casing_lookup[
                    possible_token.lower()]:
                denominator += (self.backward_bi_dist[prev_token + "_" +
                                                      alternativeToken] +
                                pseudo_count)

            bigram_backward_score = numerator / denominator

        # Get Forward Score
        bigram_forward_score = 1
        if next_token is not None:
            next_token = next_token.lower()  # Ensure it is lower case
            numerator = (
                self.forward_bi_dist[possible_token + "_" + next_token] +
                pseudo_count)
            denominator = 0
            for alternativeToken in self.word_casing_lookup[
                    possible_token.lower()]:
                denominator += (
                    self.forward_bi_dist[alternativeToken + "_" + next_token] +
                    pseudo_count)

            bigram_forward_score = numerator / denominator

        # Get Trigram Score
        trigram_score = 1
        if prev_token is not None and next_token is not None:
            next_token = next_token.lower()  # Ensure it is lower case
            numerator = (self.trigram_dist[prev_token + "_" + possible_token +
                                           "_" + next_token] + pseudo_count)
            denominator = 0
            for alternativeToken in self.word_casing_lookup[
                    possible_token.lower()]:
                denominator += (
                    self.trigram_dist[prev_token + "_" + alternativeToken +
                                      "_" + next_token] + pseudo_count)

            trigram_score = numerator / denominator

        result = (math.log(unigram_score) + math.log(bigram_backward_score) +
                  math.log(bigram_forward_score) + math.log(trigram_score))

        return result

    def first_token_case(self, raw):
        return raw.capitalize()

    def out_of_vocabulary_handler(self, token_og_case, out_of_vocabulary_token_option="title"):
        if isinstance(out_of_vocabulary_token_option, Callable):
            return out_of_vocabulary_token_option(token_og_case)
        elif out_of_vocabulary_token_option == "title":
            return token_og_case.title()
        elif out_of_vocabulary_token_option == "capitalize":
            return token_og_case.capitalize()
        elif out_of_vocabulary_token_option == "lower":
            return token_og_case.lower()
        else:
            # If value passed is invalid, use .title()
            return token_og_case.title()

    def get_true_case(self, sentence, out_of_vocabulary_token_option="title"):
        """ Wrapper function for handling untokenized input.
        
        @param sentence: a sentence string to be tokenized
        @param outOfVocabularyTokenOption:
            title: Returns out of vocabulary (OOV) tokens in 'title' format
            lower: Returns OOV tokens in lower case
            as-is: Returns OOV tokens as is
    
        Returns (str): detokenized, truecased version of input sentence 
        """
        tokens = word_tokenize(sentence)
        tokens_true_case = self.get_true_case_from_tokens(tokens, out_of_vocabulary_token_option)
        return self.detknzr.detokenize(tokens_true_case)
        
    def get_true_case_from_tokens(self, tokens, out_of_vocabulary_token_option="title"):
        """ Returns the true case for the passed tokens.
    
        @param tokens: List of tokens in a single sentence
        @param pretokenised: set to true if input is alreay tokenised (e.g. string with whitespace between tokens)
        @param outOfVocabularyTokenOption:
            title: Returns out of vocabulary (OOV) tokens in 'title' format
            lower: Returns OOV tokens in lower case
            as-is: Returns OOV tokens as is
        
        Returns (list[str]): truecased version of input list
        of tokens 
        """
        tokens_true_case = []
        for token_idx, token in enumerate(tokens):
            token_og_case = token
            if token in string.punctuation or token.isdigit():
                tokens_true_case.append(token)
            else:
                token = token.lower()
                if token in self.word_casing_lookup:
                    if len(self.word_casing_lookup[token]) == 1:
                        tokens_true_case.append(
                            list(self.word_casing_lookup[token])[0])
                    else:
                        prev_token = (tokens_true_case[token_idx - 1]
                                      if token_idx > 0 else None)
                        next_token = (tokens[token_idx + 1]
                                      if token_idx < len(tokens) - 1 else None)

                        best_token = None
                        highest_score = float("-inf")

                        for possible_token in self.word_casing_lookup[token]:
                            score = self.get_score(prev_token, possible_token,
                                                   next_token)

                            if score > highest_score:
                                best_token = possible_token
                                highest_score = score

                        tokens_true_case.append(best_token)

                    if token_idx == 0:
                        tokens_true_case[0] = self.first_token_case(
                            tokens_true_case[0])

                else:  # Token out of vocabulary
                    tokens_true_case.append(self.out_of_vocabulary_handler(token_og_case, out_of_vocabulary_token_option))

        return tokens_true_case


if __name__ == "__main__":
    dist_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "data/english.dist")

    caser = TrueCaser(dist_file_path)

    while True:
        ip = input("Enter a sentence: ")
        print(caser.get_true_case(ip, "lower"))
