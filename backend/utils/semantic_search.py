import torch
import numpy as np
from scipy.special import softmax
from transformers import BertForQuestionAnswering, BertTokenizerFast


MODEL_NAME = "deepset/bert-base-cased-squad2"
NORMAL_CHUNK_SIZE = 3
NORMAL_STRIDE = 1


class SemanticSearchModel:

    """
    Predict an answer to a question based on the given context.

    Returns:
        - answer (str or None): The predicted answer extracted from the context,
          or None if no valid answer is found.
        - confidence_score (float): The confidence score of the prediction,
          calculated as the geometric mean of start and end token scores.
    """

    def __init__(self) -> None:
        self.tokenizer = BertTokenizerFast.from_pretrained(MODEL_NAME)
        self.model = BertForQuestionAnswering.from_pretrained(MODEL_NAME)

    def predict_answer(self, context: str, question: str) -> dict:

        chunked_sentences = self.__pre_process_context(context)
        top_answer = None
        top_confidence = 0.0

        for chunk in chunked_sentences:
            curr_context = "\n".join(chunk)
            answer, confidence = self.__predict(curr_context, question)
            if answer is None and top_answer is None:
                top_confidence = max(top_confidence, confidence)
            elif answer is not None and top_answer is not None:
                if confidence > top_confidence:
                    top_answer = answer
                    top_confidence = confidence
            elif answer is not None and top_answer is None:
                top_answer = answer
                top_confidence = confidence

        return {
            'answer': top_answer,
            'confidence': top_confidence
        }

    def __predict(self, context: str, question: str) -> tuple or dict:
        inputs = self.tokenizer(question, context, return_tensors="pt", truncation=True, max_length=512)

        with torch.no_grad():
            outputs = self.model(**inputs)

        start_scores, end_scores = softmax(outputs.start_logits)[0], softmax(outputs.end_logits)[0]

        start_idx = np.argmax(start_scores)
        end_idx = np.argmax(end_scores)

        confidence_score = round(float((start_scores[start_idx] + end_scores[end_idx]) / 2), 2)

        answer_ids = inputs["input_ids"][0][start_idx: end_idx + 1]
        answer_tokens = self.tokenizer.convert_ids_to_tokens(answer_ids)
        answer = self.tokenizer.convert_tokens_to_string(answer_tokens)

        if answer != self.tokenizer.cls_token:
            return answer, confidence_score

        return {
            'answer': None,
            'confidence': confidence_score
        }

    @staticmethod
    def __pre_process_context(context: str) -> list:
        sentences = context.split("\n")
        chunks = []
        num_sentences = len(sentences)
        for i in range(0, num_sentences, NORMAL_CHUNK_SIZE - NORMAL_STRIDE):
            chunk = sentences[i: i + NORMAL_CHUNK_SIZE]
            chunks.append(chunk)
        return chunks


if __name__ == '__main__':
    sr = SemanticSearchModel()
    print(sr.predict_answer(context="this is a short story about a brown fat cat who lays on the grass and sleeps",
                            question="what is the cats color?"))
