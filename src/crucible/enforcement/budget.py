"""Token budget estimation and tracking for LLM compliance assertions."""

from crucible.enforcement.models import (
    Assertion,
    AssertionType,
    BudgetState,
    ComplianceConfig,
)

# Average tokens per character (rough estimate for code)
TOKENS_PER_CHAR = 0.25

# Base overhead for each LLM call (system prompt, response format, etc.)
BASE_OVERHEAD_TOKENS = 200

# Minimum tokens for compliance prompt
MIN_COMPLIANCE_TOKENS = 50


def estimate_assertion_tokens(assertion: Assertion, content_length: int) -> int:
    """Estimate tokens needed to run an LLM assertion.

    Args:
        assertion: The assertion to estimate
        content_length: Length of content to analyze in characters

    Returns:
        Estimated token count for input
    """
    if assertion.type != AssertionType.LLM:
        return 0

    # Content tokens
    content_tokens = int(content_length * TOKENS_PER_CHAR)

    # Compliance prompt tokens
    compliance_tokens = 0
    if assertion.compliance:
        compliance_tokens = max(
            MIN_COMPLIANCE_TOKENS,
            int(len(assertion.compliance) * TOKENS_PER_CHAR),
        )

    return BASE_OVERHEAD_TOKENS + content_tokens + compliance_tokens


def estimate_total_budget(
    assertions: list[Assertion],
    content_length: int,
) -> int:
    """Estimate total tokens needed to run all LLM assertions.

    Args:
        assertions: List of assertions (filters to LLM only)
        content_length: Length of content to analyze

    Returns:
        Estimated total token count
    """
    total = 0
    for assertion in assertions:
        if assertion.type == AssertionType.LLM:
            total += estimate_assertion_tokens(assertion, content_length)
    return total


def sort_by_priority(assertions: list[Assertion]) -> list[Assertion]:
    """Sort assertions by priority (critical first).

    Args:
        assertions: Assertions to sort

    Returns:
        Sorted list (critical > high > medium > low)
    """
    return sorted(assertions, key=lambda a: a.priority.rank)


def select_within_budget(
    assertions: list[Assertion],
    content_length: int,
    budget: int,
) -> tuple[list[Assertion], list[Assertion]]:
    """Select assertions that fit within token budget.

    Args:
        assertions: Assertions to select from (should be pre-sorted by priority)
        content_length: Length of content to analyze
        budget: Token budget (0 = unlimited)

    Returns:
        Tuple of (selected_assertions, skipped_assertions)
    """
    if budget == 0:
        # Unlimited budget
        return list(assertions), []

    selected: list[Assertion] = []
    skipped: list[Assertion] = []
    tokens_used = 0

    for assertion in assertions:
        if assertion.type != AssertionType.LLM:
            continue

        estimated = estimate_assertion_tokens(assertion, content_length)

        if tokens_used + estimated <= budget:
            selected.append(assertion)
            tokens_used += estimated
        else:
            skipped.append(assertion)

    return selected, skipped


def filter_llm_assertions(assertions: list[Assertion]) -> list[Assertion]:
    """Filter to only LLM-type assertions.

    Args:
        assertions: All assertions

    Returns:
        Only assertions with type=llm
    """
    return [a for a in assertions if a.type == AssertionType.LLM]


def create_budget_state(config: ComplianceConfig) -> BudgetState:
    """Create initial budget state from config.

    Args:
        config: Compliance configuration

    Returns:
        Fresh BudgetState
    """
    return BudgetState(total_budget=config.token_budget)


def prepare_llm_assertions(
    assertions: list[Assertion],
    content_length: int,
    config: ComplianceConfig,
) -> tuple[list[Assertion], BudgetState]:
    """Prepare LLM assertions for execution.

    Filters to LLM assertions, sorts by priority, and selects within budget.

    Args:
        assertions: All loaded assertions
        content_length: Length of content to analyze
        config: Compliance configuration

    Returns:
        Tuple of (assertions_to_run, budget_state)
    """
    # Filter to LLM assertions only
    llm_assertions = filter_llm_assertions(assertions)

    if not llm_assertions:
        return [], create_budget_state(config)

    # Sort by priority
    sorted_assertions = sort_by_priority(llm_assertions)

    # Select within budget
    selected, skipped = select_within_budget(
        sorted_assertions,
        content_length,
        config.token_budget,
    )

    # Create budget state
    state = create_budget_state(config)
    for assertion in skipped:
        state.skip(assertion.id)

    return selected, state
