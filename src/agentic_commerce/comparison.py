"""Deterministic, explicitly assumed-rate financing comparison for AC-2."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from .schemas import CommerceComparisonRequest, CommerceComparisonResponse, SimulatedFinancingOption

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_payment(principal: Decimal, annual_rate_percent: Decimal, months: int) -> Decimal:
    """Return a standard reducing-balance payment, rounded to cents."""
    if principal == 0:
        return Decimal("0.00")
    if annual_rate_percent == 0:
        return _money(principal / months)
    with localcontext() as context:
        context.prec = 32
        monthly_rate = annual_rate_percent / Decimal("1200")
        factor = (Decimal("1") + monthly_rate) ** months
        payment = principal * monthly_rate * factor / (factor - Decimal("1"))
        return _money(payment)


def compare_purchase(request: CommerceComparisonRequest) -> CommerceComparisonResponse:
    intent = request.intent
    principal = _money(intent.product_price - intent.down_payment)
    options: list[SimulatedFinancingOption] = []
    for index, annual_rate in enumerate(sorted(request.annual_rate_scenarios_percent)):
        monthly = monthly_payment(principal, annual_rate, intent.requested_tenure_months)
        # Rounded monthly installments can undershoot principal by a few cents;
        # the final payment adjustment is reflected in the aggregate total.
        total = max(_money(monthly * intent.requested_tenure_months), principal)
        interest = _money(total - principal)
        ratio = (
            (monthly / intent.monthly_income).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            if intent.monthly_income > 0 else None
        )
        options.append(SimulatedFinancingOption(
            option_id=f"scenario-{index + 1}",
            display_name=f"Rate scenario {index + 1}",
            principal=principal,
            annual_rate_percent=annual_rate,
            tenure_months=intent.requested_tenure_months,
            estimated_monthly_payment=monthly,
            estimated_total_payment=total,
            estimated_total_interest=interest,
            payment_to_income_ratio=ratio,
            estimated_remaining_income_after_obligations=_money(
                intent.monthly_income - intent.existing_monthly_obligations - monthly
            ),
            research_notes="Illustrative rate scenario assumption; not a lender offer.",
        ))

    preferred = min(options, key=lambda item: (item.estimated_total_interest, item.estimated_monthly_payment))
    return CommerceComparisonResponse(
        currency=intent.currency,
        purchase_price=_money(intent.product_price),
        down_payment=_money(intent.down_payment),
        financed_amount=principal,
        requested_tenure_months=intent.requested_tenure_months,
        options=options,
        preferred_option_id=preferred.option_id,
        recommendation_explanation=(
            f"{preferred.display_name} has the lowest estimated total interest among the submitted rate scenarios "
            f"for the requested {intent.requested_tenure_months}-month tenure. This is a research comparison, "
            "not an affordability assessment, credit decision, or lender offer."
        ),
        comparison_factors=[
            "Lowest estimated total interest across the submitted scenarios",
            "Monthly payment uses the same requested tenure for each scenario",
            "Payment-to-income ratio is descriptive and is not an approval threshold",
        ],
        event_summary=f"Compared {len(options)} submitted rate scenarios; no transaction or audit event was persisted.",
    )
