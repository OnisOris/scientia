import openai


async def generate_question(context: str) -> str:
    prompt = f'Сгенерируй один вопрос на русском языке по следующему тексту:\n\n"{context}"'
    response = await openai.ChatCompletion.acreate(
        model="gpt-4", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
