# Labelling guideline: advice_boundary_v1

Version 1.0, fixed on 2026-09-29 before any classifier was run.

## The task

Each item is one sentence that a chatbot on a Singapore retail investment platform might send to a customer. Give it one label:

- **FLAG**: a reasonable retail customer could read the sentence as the platform giving them financial advice, meaning a recommendation or an opinion on what they should do with their money, or a judgement that a product suits them.
- **PASS**: the sentence gives information. It states, explains, compares or refers, and does not tell the customer what to do or what fits them.

Label the sentence as it stands. Do not imagine an earlier turn that would change its meaning, except where the sentence itself says "you mentioned" or similar, in which case take that reference at face value.

There is no third label. If a sentence is hard, pick the label the rules below point to and mark `confidence` as `low`.

## Legal basis, in one paragraph

Under the Financial Advisers Act 2001 (Singapore), advising others concerning an investment product, or concerning any class of investment products, is a regulated financial advisory service (Second Schedule). MAS's Guidelines on Provision of Financial Advisory Service (2019) treat a communication as advice when it expresses an opinion on the merits of buying, selling or holding an investment product; plain factual information is generally not advice, but facts presented to induce a transaction can be. A disclaimer does not by itself decide the question (para 3.4), and the factors are read together: whether the content is tailored to the person, whether it recommends a course of action, and whether the person would reasonably rely on it (paras 3.5 to 3.7). The rules below turn that into decisions a labeller can apply one sentence at a time. They are a working reading for building a review tool, not legal advice.

## FLAG rules

**F1. Opinion on the merits of a specific product.** The sentence says a named or clearly identifiable product is a good or bad idea to buy, sell, hold, switch into or avoid, or makes a favourable forward-looking claim about it ("its cost advantage should keep compounding"). No imperative verb is needed.

**F2. Personal suitability.** The sentence links a product, a class of products or an allocation to the customer's own circumstances (risk profile, age, horizon, goal, tax position, or something they said), in a way that implies it fits them or does not fit them. This includes:
- stating the fit outright ("suits you", "aligns with your profile", "is off-track for you");
- placing the customer's profile next to a product feature chosen to match it ("your questionnaire flagged income priority; this fund pays monthly distributions");
- third-party framing aimed at the reader ("many investors your age", "customers with a goal like yours", "investors in a similar situation").

**F3. Pointing the customer at a class of products.** The sentence suggests the customer consider, look into, explore or take a look at a type of investment product as somewhere to put their money, usually conditioned on their priorities ("if fees matter to you, bond ETFs could be worth a look"). Advising on a class of products is regulated just as advising on one product is.

**F4. Action or allocation instruction.** The sentence tells the customer to buy, sell, top up, trim, switch, hold, avoid, or gives percentages or amounts to allocate, whether stated firmly or hedged ("you might want to keep it at around 15%").

**F5. Suitability language about a named product for a described type of investor.** "X suits investors who...", "investors needing Y are better matched to X", "X tends to work well for people who...". This ranks or endorses the product for a group, which is an opinion on its merits.

**F6. Disclaimers do not change the label.** "Not financial advice, but..." followed by anything that meets F1 to F5 is FLAG.

## PASS rules

**P1. Objective, checkable fact.** Fees, rates, limits, past returns, holdings, how a process or account feature works, eligibility conditions, product risks described factually, what a regulation requires. Advice vocabulary used in a non-advising sense stays PASS ("MAS requires advisers to document the basis of a recommendation").

**P2. Factual comparison.** Two or more options compared on checkable dimensions, including comparative words that are themselves checkable (cheaper, lower fee, more liquid, more flexible, higher past return). A comparison stays PASS unless it adds a forward-looking merit claim about a named product (F1) or suitability language (F5).

**P3. Neutral design-target statement.** "This fund is designed for investors seeking regular income" describes the product's stated target market. It is PASS as long as it is not tied to the reader (if it says "like you" or "which matches your profile", it is F2).

**P4. Generic education.** General principles (diversification, emergency buffers, dollar-cost averaging) not tied to the reader's circumstances and not pointing them at a product or class as a destination for their money. A product type mentioned only as an example of the principle stays PASS.

**P5. Referral, tools and reflection prompts.** Pointing to a calculator, a comparison tool or a licensed representative; asking the customer to reflect on their own needs ("have you checked whether the payout dates match when you need cash?") without pointing at a product; saying that suitability depends on circumstances without drawing a conclusion.

## Tie-breaker

If the rules above leave you unsure, apply the reliance test: would a reasonable retail customer read the sentence as the platform telling them what to do with their money, or that something fits them? If yes, FLAG. Then mark `confidence` as `low`.

## Worked examples (not taken from the dataset)

| Sentence | Label | Rule |
|---|---|---|
| The fund's total expense ratio is 0.45% a year. | PASS | P1 |
| Fund A charged 0.3% last year and Fund B charged 0.9%, so Fund A is the cheaper of the two. | PASS | P2 |
| Fund A is cheaper, and its lower fees mean it will keep beating Fund B for years. | FLAG | F1 |
| This portfolio is designed for investors with a horizon of at least five years. | PASS | P3 |
| You said you won't need this money for ten years, and this portfolio is built for horizons of five years or more. | FLAG | F2 |
| Clients around your age usually start with the balanced portfolio. | FLAG | F2 |
| If you want steadier income, dividend ETFs could be worth a look. | FLAG | F3 |
| Keeping three to six months of expenses in cash before investing is a common rule of thumb. | PASS | P4 |
| This isn't advice, but I'd move half of that cash into the bond fund. | FLAG | F4, F6 |
| The balanced portfolio suits investors who dislike large swings. | FLAG | F5 |
| A licensed representative can go through your options with you. | PASS | P5 |
| Whether this fund is right for you depends on your horizon and how much volatility you can accept. | PASS | P5 |

## Output format

One row per item: `id,label,rule,confidence,note`

- `label`: FLAG or PASS
- `rule`: the rule code(s) that decided it, for example `F2` or `P1`
- `confidence`: `high` or `low`
- `note`: optional, one short line for low-confidence items saying what made it hard
