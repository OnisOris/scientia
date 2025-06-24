import openai


# app/services/quiz/evaluator.py
async def evaluate_answer(
    question: str, user_answer: str, correct_answer: str
) -> bool:
    prompt = (
        f"Вопрос: {question}\n"
        f"Правильный ответ: {correct_answer}\n"
        f"Ответ пользователя: {user_answer}\n"
        f"Является ли ответ пользователя правильным? Ответь 'Да' или 'Нет'."
    )
    response = await openai.ChatCompletion.acreate(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.lower()
    return "да" in text
