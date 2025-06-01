import spacy
import os

nlp_model = None


def load_nlp_model(model_name: str = "ru_core_news_md"):
    global nlp_model

    os.environ["GRPC_DNS_RESOLVER"] = "native"

    if nlp_model is None:
        try:
            nlp_model = spacy.load(model_name)
            print(f"✅ NLP модель '{model_name}' успешно загружена")
        except OSError:
            print(f"⚠️ Модель {model_name} не найдена. Пытаюсь загрузить...")
            spacy.cli.download(model_name)
            nlp_model = spacy.load(model_name)

    return nlp_model


def get_nlp_model():
    global nlp_model
    if nlp_model is None:
        raise RuntimeError(
            "NLP модель не загружена. Сначала вызовите load_nlp_model()"
        )
    return nlp_model
