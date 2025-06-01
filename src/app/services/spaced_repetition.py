from datetime import datetime, timedelta
from app.models import User, UserKnowledge


class SpacedRepetitionService:
    @staticmethod
    def update_knowledge(user: User, knowledge: UserKnowledge, quality: float):
        if not hasattr(user, "lambda_coef"):
            user.lambda_coef = 0.5

        retention = knowledge.retention
        old_lambda = user.lambda_coef
        if quality >= 0.6:
            new_retention = retention + (1 - retention) * old_lambda
            new_lambda = old_lambda * 0.9
        else:
            new_retention = retention * 0.5
            new_lambda = old_lambda * 1.1

        interval_days = max(1, int(10 * (1 - new_retention)))
        user.lambda_coef = max(0.1, min(0.9, new_lambda))
        knowledge.retention = max(0.1, min(0.99, new_retention))
        knowledge.last_reviewed = datetime.utcnow()
        knowledge.next_review = knowledge.last_reviewed + timedelta(
            days=interval_days
        )
        log_data = RetentionLogData(
            user_id=user.id,
            concept_id=knowledge.concept_id,
            old_lambda=old_lambda,
            new_lambda=new_lambda,
            retention_before=retention,
            retention_after=new_retention,
        )

        return user, knowledge, log_data


class RetentionLogData:
    def __init__(
        self,
        user_id,
        concept_id,
        old_lambda,
        new_lambda,
        retention_before,
        retention_after,
    ):
        self.user_id = user_id
        self.concept_id = concept_id
        self.old_lambda = old_lambda
        self.new_lambda = new_lambda
        self.retention_before = retention_before
        self.retention_after = retention_after
