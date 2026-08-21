"""Deterministic ticket workflow — application code controls the sequence.

No agent logic, no tool calling.  Each step is ordinary Python that
decides what runs next based on structured analysis output and the
availability of trusted context.
"""

import json
from datetime import datetime

from app.core.prompt_data import serialize_prompt_payload
from app.prompts.analyse import ANALYSE_SYSTEM_PROMPT
from app.prompts.response_generation import RESPONSE_GENERATION_SYSTEM_PROMPT
from app.repositories.faq_repository import FAQRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.enums import Priority, Sentiment, TicketCategory, TicketStatus
from app.schemas.faq import FAQSource
from app.schemas.workflow import (
    ProcessTicketRequest,
    ProcessTicketResponse,
    WorkflowStep,
)
from app.services.llm import chat


class WorkflowService:
    """Orchestrates the deterministic ticket-processing pipeline.

    Reuses existing repositories and LLM helpers — never queries
    MongoDB directly, never calls the LLM SDK directly.
    """

    def __init__(
        self,
        ticket_repo: TicketRepository,
        order_repo: OrderRepository,
        faq_repo: FAQRepository,
    ) -> None:
        self.ticket_repo = ticket_repo
        self.order_repo = order_repo
        self.faq_repo = faq_repo

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def process(self, request: ProcessTicketRequest) -> ProcessTicketResponse:
        """Run the full deterministic workflow for a single customer message."""

        executed_steps: list[WorkflowStep] = []
        requires_human_review = False
        human_review_reasons: list[str] = []

        order_context: dict | None = None
        faq_sources: list[FAQSource] = []

        # ── 1. ANALYSIS ──────────────────────────────────────────────
        analysis = await self._analyse(request.customer_message)
        executed_steps.append(WorkflowStep.ANALYSIS)

        if analysis.get("needs_human_review"):
            requires_human_review = True
            human_review_reasons.append(
                analysis.get("human_review_reason") or "Analysis flagged for human review"
            )

        # ── 2. ORDER_LOOKUP (conditional) ────────────────────────────
        if analysis.get("needs_order_lookup"):
            order_context, order_ok = await self._lookup_order(
                request.customer_id, request.order_id,
            )
            executed_steps.append(WorkflowStep.ORDER_LOOKUP)

            if not order_ok:
                requires_human_review = True
                human_review_reasons.append(
                    "Required order context could not be verified"
                )

        # ── 3. FAQ_LOOKUP (conditional) ──────────────────────────────
        if analysis.get("needs_faq_lookup"):
            faq_sources, faq_ok = await self._lookup_faq(
                analysis.get("faq_query") or request.customer_message,
            )
            executed_steps.append(WorkflowStep.FAQ_LOOKUP)

            if not faq_ok:
                requires_human_review = True
                human_review_reasons.append(
                    "No approved FAQ evidence found for the customer question"
                )

        # ── 4. DATABASE_INSERT ───────────────────────────────────────
        now = datetime.utcnow()
        ticket_id = await self.ticket_repo.generate_ticket_id()
        subject = request.subject or request.customer_message[:80]

        user_message = {
            "role": "user",
            "content": request.customer_message,
            "order_context": order_context,
            "timestamp": now,
        }

        ticket_doc = {
            "ticket_id": ticket_id,
            "customer_id": request.customer_id,
            "order_id": request.order_id,
            "subject": subject,
            "status": TicketStatus.OPEN.value,
            "analysis": analysis,
            "messages": [user_message],
            "created_at": now,
            "updated_at": now,
        }
        await self.ticket_repo.create_ticket(ticket_doc)
        executed_steps.append(WorkflowStep.DATABASE_INSERT)

        # ── 5. RESPONSE_GENERATION ───────────────────────────────────
        draft = await self._generate_response(
            request.customer_message, order_context, faq_sources,
        )
        executed_steps.append(WorkflowStep.RESPONSE_GENERATION)

        # Persist assistant message
        await self.ticket_repo.add_message(ticket_id, {
            "role": "assistant",
            "content": draft,
            "timestamp": datetime.utcnow(),
        })

        # ── 6. DATABASE_UPDATE — decide final status ────────────────
        final_status = self._decide_status(
            requires_human_review, analysis,
        )
        await self.ticket_repo.update_ticket(ticket_id, {
            "status": final_status.value,
            "requires_human_review": requires_human_review,
            "human_review_reason": "; ".join(human_review_reasons) if human_review_reasons else None,
        })
        executed_steps.append(WorkflowStep.DATABASE_UPDATE)

        # ── Build response ───────────────────────────────────────────
        return ProcessTicketResponse(
            ticket_id=ticket_id,
            final_status=final_status.value,
            executed_steps=executed_steps,
            analysis=analysis,
            order_context=order_context,
            faq_sources=[s.model_dump(mode="json") for s in faq_sources],
            draft_response=draft,
            requires_human_review=requires_human_review,
            human_review_reason="; ".join(human_review_reasons) if human_review_reasons else None,
        )

    # ------------------------------------------------------------------
    # Private helpers — each wraps one existing component
    # ------------------------------------------------------------------

    async def _analyse(self, text: str) -> dict:
        """Call the LLM for structured ticket analysis."""
        result = await chat(
            prompt=text,
            system_prompt=ANALYSE_SYSTEM_PROMPT,
            response_format="json_object",
        )
        try:
            parsed = json.loads(result["response"])

            # Normalise enum values with safe fallbacks
            try:
                parsed["category"] = TicketCategory(parsed.get("category", "general")).value
            except ValueError:
                parsed["category"] = TicketCategory.GENERAL.value

            try:
                parsed["sentiment"] = Sentiment(parsed.get("sentiment", "neutral")).value
            except ValueError:
                parsed["sentiment"] = Sentiment.NEUTRAL.value

            try:
                parsed["priority"] = Priority(parsed.get("priority", "medium")).value
            except ValueError:
                parsed["priority"] = Priority.MEDIUM.value

            return parsed
        except (json.JSONDecodeError, AttributeError):
            return {
                "summary": "Unable to analyze ticket",
                "category": TicketCategory.GENERAL.value,
                "sentiment": Sentiment.NEUTRAL.value,
                "priority": Priority.MEDIUM.value,
                "needs_order_lookup": False,
                "needs_faq_lookup": False,
                "needs_human_review": True,
                "human_review_reason": "LLM analysis failed",
            }

    async def _lookup_order(
        self, customer_id: str | None, order_id: str | None,
    ) -> tuple[dict | None, bool]:
        """Customer-scoped order lookup.  Returns (context, success)."""
        if not customer_id or not order_id:
            return None, False

        order_doc = await self.order_repo.get_order_for_customer(customer_id, order_id)
        if order_doc is None:
            return None, False

        return {
            "order_id": order_doc.order_id,
            "status": order_doc.status.value,
            "estimated_delivery": str(order_doc.estimated_delivery),
            "delivered_at": str(order_doc.delivered_at),
        }, True

    async def _lookup_faq(
        self, query: str,
    ) -> tuple[list[FAQSource], bool]:
        """Search approved FAQ sources.  Returns (sources, success)."""
        sources = self.faq_repo.search(query, limit=3)
        return sources, len(sources) > 0

    async def _generate_response(
        self,
        customer_message: str,
        order_context: dict | None,
        faq_sources: list[FAQSource],
    ) -> str:
        """Draft a customer-facing response using trusted context only."""
        payload = {
            "customer_message": customer_message,
            "trusted_order_context": order_context,
            "trusted_faq_context": [s.model_dump(mode="json") for s in faq_sources],
        }
        result = await chat(
            prompt=(
                "Customer request and application context:\n"
                + serialize_prompt_payload(payload)
            ),
            system_prompt=RESPONSE_GENERATION_SYSTEM_PROMPT,
        )
        return result["response"]

    @staticmethod
    def _decide_status(
        requires_human_review: bool,
        analysis: dict,
    ) -> TicketStatus:
        """Application owns the final status — not the LLM.

        Rules:
        - Human review required  → OPEN
        - Critical priority       → OPEN
        - Otherwise               → RESOLVED
        """
        if requires_human_review:
            return TicketStatus.OPEN

        priority = analysis.get("priority", "medium")
        if priority == Priority.CRITICAL.value:
            return TicketStatus.OPEN

        return TicketStatus.RESOLVED
