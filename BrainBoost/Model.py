# Install libraries
# pip install openai==0.28 PyPDF2
# pip install torch

# pip install transformers

# pip install sentencepiece
# pip install tenacity


# -------------------------------------------------------------------------------------------------------------------------------
# Import libraries
import PyPDF2
import openai
import os
import torch
from openai.error import RateLimitError
from tenacity import retry, wait_exponential, stop_after_attempt, wait_fixed
from transformers import T5ForConditionalGeneration, T5Tokenizer
import random

# -------------------------------------------------------------------------------------------------------------------------------

openai_api_key = os.getenv('OPENAI_API_KEY')


os.environ["OPENAI_API_KEY"] = openai_api_key


# @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(100))
# # @retry(wait=wait_fixed(440), stop=stop_after_attempt(100))
# def call_gpt(prompt, model_name="gpt-3.5-turbo"):
#     try:
#         chat_completion = openai.ChatCompletion.create(
#             messages=[
#                 {
#                     "role": "user",
#                     "content": prompt
#                 },
#             ],
#             model=model_name,
#             max_tokens=300,
#             temperature=0.0,
#         )
#
#         return chat_completion.choices[0].message.content
#
#     except Exception as e:
#         print(f"An error occurred: {str(e)}", "error")

# -----------------------------Modified Version -------------------------------------

@retry(wait=wait_exponential(multiplier=1, min=2, max=10),
       stop=stop_after_attempt(100), retry_error_callback=lambda x: isinstance(x, RateLimitError))
def call_gpt(prompt, model_name="gpt-3.5-turbo"):
    try:
        chat_completion = openai.ChatCompletion.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            model=model_name,
            max_tokens=300,
            temperature=0.0,
        )

        return chat_completion.choices[0].message.content

    except RateLimitError as e:
        print(f"Rate limit exceeded: {str(e)}")
        raise
    except Exception as e:
        print(f"An error occurred: {str(e)}")


# -------------------------------------------------------------------------------------------------------------------------------
# Text Extraction
class PDFProcessor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.sentences = []

    def TextPreprocessing(self):
        def clean_text(text):
            # Add your text cleaning process here if needed
            return text

        full_text = ""
        with open(self.pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                full_text += page.extract_text() + "\n"

        cleaned_text = clean_text(full_text)
        # Assuming call_gpt is defined elsewhere
        generated_text = call_gpt(
            f"(from the content of this extracted text {cleaned_text} give me multiple lots of context sentences that cover all important points, do not numrize the sentences)")
        sentences = generated_text.split(".")
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    # -------------------------------------------------------------------------------------------------------------------------------
    # Question Generation
    def QuestionGeneration(self, sentences):
        # T5 model and tokenizer setup
        try:
            trained_model_path = r"E:\New folder\Hasbu\BrainBoost\BrainBoost\model"
            trained_tokenizer = r"E:\New folder\Hasbu\BrainBoost\BrainBoost\tokenizer"

            model = T5ForConditionalGeneration.from_pretrained(trained_model_path, from_tf=True)
            tokenizer = T5Tokenizer.from_pretrained(trained_tokenizer)

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model = model.to(device)

            # Array to store generated questions
            Questions = []

            # Generate a question for each sentence
            for sentence in sentences:
                # Generate the text input for the model
                text = "context: " + sentence + " " + "answer: ..." + " </s>"

                # Encode the text using the tokenizer
                encoding = tokenizer.encode_plus(text, max_length=512, padding=True, return_tensors="pt")

                # Extract input_ids and attention_mask tensors
                input_ids, attention_mask = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

                # Set the model to evaluation mode
                model.eval()

                # Generate the question using the model
                beam_outputs = model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    max_length=72,
                    early_stopping=True,
                    num_beams=5,
                    num_return_sequences=1
                )

                # Decode the generated question and add it to the Questions array
                for beam_output in beam_outputs:
                    generated_question = tokenizer.decode(beam_output, skip_special_tokens=True,
                                                          clean_up_tokenization_spaces=True)
                    # Remove 'question:' from the generated question
                    generated_question = generated_question.replace('question:', '')
                    Questions.append(generated_question)

            return Questions

        except Exception as e:
            print(f"An error occurred: {str(e)}")

    # -------------------------------------------------------------------------------------------------------------------------------
    # Answer Generation
    def AnswerGeneration(self, sentences, Questions):
        # T5 answer model and tokenizer setup
        trained_answer_model_path = r"C:\brainboost\BrainBoost\answer_model"
        trained_answer_tokenizer = r"C:\brainboost\BrainBoost\answer_tokenizer"

        answer_model = T5ForConditionalGeneration.from_pretrained(trained_answer_model_path)
        answer_tokenizer = T5Tokenizer.from_pretrained(trained_answer_tokenizer)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        answer_model = answer_model.to(device)

        # Array to store generated answers
        CorrectAnswers = []

        # Generate an answer for each context and question pair
        for context, question in zip(sentences, Questions):
            # Generate the text input for the answer model
            text = "context: " + context + " " + "Question: " + question + " </s>"

            # Encode the text using the answer tokenizer
            encoding = answer_tokenizer.encode_plus(text, max_length=512, padding=True, return_tensors="pt")

            # Extract input_ids and attention_mask tensors
            input_ids, attention_mask = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

            # Set the answer model to evaluation mode
            answer_model.eval()

            # Generate the answer using the answer model
            beam_outputs = answer_model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=72,
                early_stopping=True,
                num_beams=5,
                num_return_sequences=1
            )

            # Decode the generated answer and add it to the CorrectAnswers array
            for beam_output in beam_outputs:
                generated_answer = answer_tokenizer.decode(beam_output, skip_special_tokens=True,
                                                           clean_up_tokenization_spaces=True)
                # Remove 'answer:' from the generated answer
                generated_answer = generated_answer.replace('question:', '')
                CorrectAnswers.append(generated_answer)

        return CorrectAnswers

    # -------------------------------------------------------------------------------------------------------------------------------
    # MCQ / Distractors Generation
    def GenerateDistractors(self, sentences, Questions, CorrectAnswers):
        # Distractors Generation

        def generate_distractors(context, question, answer):
            # Prompt for GPT
            prompt = f"(Given this Question: {question}. And Correct answer: {answer}. Generate three distractors that are close to the correct answer)"

            generated_text = call_gpt(prompt)

            # Process the generated_text to separate distractors and remove numbering
            distractors = generated_text.split('\n')
            distractors = [distractor.split('. ')[1] for distractor in distractors if
                           distractor.strip()]  # Remove numbering and empty lines

            return distractors

        # Dictionary to store distractors mapped to question numbers
        distractors_dict = {}

        # Generate distractors for each context, question, and correct answer
        for i, (context, question, correct_answer) in enumerate(zip(sentences, Questions, CorrectAnswers), 1):
            # Generate distractors using GPT and process them
            distractors = generate_distractors(context, question, correct_answer)

            # Store distractors in the distractors_dict
            distractors_dict[f"Question {i}"] = distractors

        # Create MCQ Dictionary
        # Dictionary to store MCQs (questions with correct answers)
        mcq = {}

        # Loop through each question and add correct answer to mcq dictionary
        for i, (question_number, distractors) in enumerate(distractors_dict.items()):
            if i < len(CorrectAnswers):
                correct_answer = CorrectAnswers[i]
                mcq[question_number] = distractors + [correct_answer]
            else:
                print(f"Warning: Missing correct answer for question {question_number}")

        # Create a new dictionary with integer keys starting from zero to match the correct answer 
        mcq_mapped = {i: mcq[f'Question {i + 1}'] for i in range(len(mcq))}

        # Shuffle each group of four entries within the dictionary
        shuffled_mcq = {}
        for index, mcq_list in mcq_mapped.items():
            shuffled_group = [mcq_list[i:i + 4] for i in range(0, len(mcq_list), 4)]
            for group_index, group in enumerate(shuffled_group):
                random.shuffle(group)  # Shuffle each group of four elements
                shuffled_mcq[index + group_index] = group  # Assign shuffled group back to the dictionary

        return shuffled_mcq
