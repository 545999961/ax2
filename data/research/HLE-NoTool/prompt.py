SYSTEM_PROMPT = (
    "Your response should be in the following format:\n"
    "Explanation: {your explanation for your answer choice}\n"
    "Answer: {your chosen answer}\n"
    "Confidence: {your confidence score between 0% and 100% for your answer}"
)

USER_PROMPT = "{question}"

PROMPT_BUNDLE = {
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt": USER_PROMPT,
    "token_limit_prompt": "",
    "token_finish_prompt": "",
}

TOOLS = []

GENERATION = {
    "temperature": 0.2,
    "top_p": 0.95,
    "presence_penalty": 0.2,
    "max_completion_tokens": 128000,
    "context_length": 262144,
    "retry_token_threshold": 100000,
    "retry_max_attempts": 3,
}
