from typing import Any

from app.schemas.faq import FAQSource

# MongoDB projection: only approved FAQ fields leave the repository.
FAQ_SOURCE_PROJECTION = {
    "_id": 0,
    "faq_id": 1,
    "category": 1,
    "question": 1,
    "answer": 1,
}


class FAQRepository:
    """Data access layer for approved FAQ records in MongoDB."""

    def __init__(self, database: Any) -> None:
        self.collection = database.faqs

    def get_by_ids(
        self,
        faq_ids: list[str],
        *,
        limit: int = 3,
    ) -> list[FAQSource]:
        """Retrieve approved FAQs by their IDs, preserving request order."""
        requested_ids = list(dict.fromkeys(faq_ids))[:limit]

        if not requested_ids:
            return []

        cursor = self.collection.find(
            {"faq_id": {"$in": requested_ids}, "active": True},
            FAQ_SOURCE_PROJECTION,
        )

        found: dict[str, FAQSource] = {}
        for document in cursor:
            faq = FAQSource.model_validate(document)
            found[faq.faq_id] = faq

        return [found[faq_id] for faq_id in requested_ids if faq_id in found]

    def search(
        self,
        query: str,
        *,
        limit: int = 3,
    ) -> list[FAQSource]:
        """Search FAQs using MongoDB text search, ranked by relevance."""
        search_query = query.strip()
        if not search_query:
            return []

        safe_limit = max(1, min(limit, 3))

        pipeline = [
            {
                "$match": {
                    "active": True,
                    "$text": {"$search": search_query},
                }
            },
            {
                "$sort": {"score": {"$meta": "textScore"}}
            },
            {"$limit": safe_limit},
            {"$project": FAQ_SOURCE_PROJECTION},
        ]

        cursor = self.collection.aggregate(pipeline)

        results: list[FAQSource] = []
        for document in cursor:
            results.append(FAQSource.model_validate(document))

        return results
