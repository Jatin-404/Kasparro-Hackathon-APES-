"""Deterministic re-simulation helpers for applying generated fixes."""

from __future__ import annotations

from copy import deepcopy

from backend.app.models import FAQ, FixProposal, Policy, StoreContext


class ResimulationRunner:
    """Apply generated fixes to StoreContext before re-running failed queries."""

    def apply_fixes(self, store_context: StoreContext, fixes: list[FixProposal]) -> StoreContext:
        """Return a copied StoreContext with generated fixes inserted into content slots."""

        fixed = deepcopy(store_context)
        for fix in fixes:
            self._apply_one(fixed, fix)
        return fixed

    def _apply_one(self, store_context: StoreContext, fix: FixProposal) -> None:
        """Apply a single fix in the least surprising content location."""

        if fix.content_type == "shipping policy":
            store_context.policies.shipping = Policy(title="Shipping Policy", body=fix.improved_content)
        elif fix.content_type == "refund policy":
            store_context.policies.refund = Policy(title="Refund Policy", body=fix.improved_content)
        elif fix.content_type == "return policy":
            store_context.policies.return_policy = Policy(title="Return Policy", body=fix.improved_content)
        elif fix.content_type == "warranty policy":
            store_context.policies.warranty = Policy(title="Warranty Policy", body=fix.improved_content)
        elif fix.content_type == "FAQ answer":
            store_context.faqs.append(
                FAQ(question="What does APES recommend clarifying?", answer=fix.improved_content)
            )
        elif fix.content_type == "product description":
            self._apply_product_description(store_context, fix)

    def _apply_product_description(self, store_context: StoreContext, fix: FixProposal) -> None:
        """Patch the first product matching the original content or missing description."""

        for product in store_context.products:
            if product.description == fix.original_content or product.description is None:
                product.description = fix.improved_content
                return
