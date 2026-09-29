"""
AdviceGuard corpus: MAS / Financial Advisers Act rule cards.

20 short "rule card" documents summarizing (in plain language, not verbatim
statute text) the Singapore rules that separate financial *information* from
financial *advice*. Built for PE6201 A1 Part 2 (retrieval/RAG).

Each card is a dict with:
  id      - doc_01 .. doc_20
  title   - short card title
  source  - the regulator document (and paragraph/section where known)
  url     - a public MAS / SSO source URL
  text    - the rule card body (own words; at most one short quoted phrase)

See corpus_manifest.md (same folder) for the source table, the intended
distractor cluster, the multi-hop pair, and unverified details.
"""

DOCS = [
    {
        "id": "doc_01",
        "title": "What Makes a Service a 'Financial Advisory Service'",
        "source": "Financial Advisers Act 2001 (FAA), Section 2(1), read with the Second Schedule",
        "url": "https://sso.agc.gov.sg/Act/FAA2001",
        "text": (
            "The FAA itself does not define 'financial advice' as a phrase. Instead, Section "
            "2(1) defines a 'financial advisory service' as any of the services listed in the "
            "Act's Second Schedule. This is the anchor definition for the whole regime: a person "
            "or firm carrying on a Second Schedule activity as a business in Singapore generally "
            "needs to be a licensed financial adviser, an exempt financial adviser, or otherwise "
            "covered by an exemption. Everything else in the FAA framework -- who needs a licence, "
            "what conduct rules apply, what must be disclosed -- hangs off this one gateway "
            "question: is the activity a Second Schedule service? The Second Schedule itself "
            "(see the companion card on the five regulated activities) is where the actual list "
            "of advisory activities, including advising on investment products and issuing "
            "research reports, is set out. Confirmed directly from the statute text."
        ),
    },
    {
        "id": "doc_02",
        "title": "The Second Schedule: Five Regulated Advisory Activities",
        "source": "FAA Second Schedule (paraphrased; corroborated via secondary legal summaries, not re-verified against the live schedule text this session)",
        "url": "https://sso.agc.gov.sg/Act/FAA2001",
        "text": (
            "The Second Schedule is generally described (by MAS-adjacent legal commentary) as "
            "listing roughly five categories of 'financial advisory service': (1) advising "
            "others, directly or through publications, concerning investment products; (2) "
            "advising others concerning any class of investment products; (3) issuing or "
            "promulgating analyses or research reports concerning investment products; (4) "
            "marketing of collective investment schemes (CIS); and (5) marketing of life "
            "policies. 'Investment products' is a wide umbrella covering securities, units in "
            "a CIS, exchange-traded and OTC derivatives, spot foreign exchange contracts traded "
            "for leveraged FX trading, structured deposits, and life policies. Note of caution: "
            "this session could not pull the exact verbatim paragraph lettering of the Second "
            "Schedule from a live fetch of the statute; the activity list above is corroborated "
            "by two independent secondary legal sources but should be checked against the "
            "primary SSO text before being treated as exact statutory wording."
        ),
    },
    {
        "id": "doc_03",
        "title": "MAS's Opinion Test: When Does a Statement Become 'Advice'?",
        "source": "MAS Guidelines on Provision of Financial Advisory Service and Design of Advisory and Sales Forms (10 Jul 2019), para 3.2",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "MAS's own guidance gives the practical test that sits behind the Second Schedule "
            "wording: a communication is treated as financial advice if it expresses "
            "'an opinion on the merits of buying, selling or holding a particular investment "
            "product'. The key word is opinion -- a view or judgement about whether a specific "
            "product is a good idea for someone, as opposed to a plain restatement of facts "
            "about that product. This is the single most important sentence for a chatbot "
            "compliance filter: if the model's output can fairly be read as endorsing or "
            "discouraging a buy/sell/hold decision on a named or clearly identifiable "
            "investment product, MAS's own test treats that as advice, regardless of how "
            "the sentence is phrased or hedged. Confirmed directly from the MAS guidelines PDF."
        ),
    },
    {
        "id": "doc_04",
        "title": "The Factual-Information Exemption -- and Its Limit",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), para 3.3",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "MAS explicitly carves out plain factual information from the definition of advice: "
            "'the provision of factual information ... is generally not considered financial "
            "advice', where factual information means information which is objective, "
            "verifiable, and whose accuracy cannot reasonably be questioned -- things like a "
            "fund's expense ratio, its historical unit price, or its stated investment mandate. "
            "But this exemption has a limit that matters a lot for a chatbot: MAS goes on to say "
            "that even purely factual information can tip into advice if it is presented with "
            "the intention of inducing a person to buy, sell or hold the product. So the same "
            "sentence -- 'this fund returned 8% last year' -- can sit on either side of the line "
            "depending on framing and context, not just on whether the underlying numbers are "
            "true. Confirmed directly from the MAS guidelines PDF, para 3.3."
        ),
    },
    {
        "id": "doc_05",
        "title": "Disclaimers Are Not a Safe Harbour",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), para 3.4",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "A natural instinct for a chatbot builder is to bolt on a disclaimer -- 'this is not "
            "financial advice' -- and assume that settles the question. MAS's guidance says "
            "otherwise: providers of factual information are encouraged to add disclaimers "
            "making clear the content is for information only, but 'the use of a disclaimer "
            "does not, of itself, determine' whether the activity amounts to providing financial "
            "advice. In other words, a disclaimer is one input into the overall picture, not a "
            "dispositive shield. If the substance of a chatbot's output is an opinion on the "
            "merits of a specific product (see the opinion test card), no amount of boilerplate "
            "disclaimer text converts that opinion back into neutral information. This matters "
            "directly for AdviceGuard: a detector cannot simply whitelist any response that "
            "contains a disclaimer string. Confirmed directly from the MAS guidelines PDF, "
            "para 3.4."
        ),
    },
    {
        "id": "doc_06",
        "title": "The Reliance Test: Would the Recipient Reasonably Rely on This?",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), para 3.5",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "Beyond the opinion/fact split, MAS layers in a reliance test: an opinion given in a "
            "situation where the recipient is not reasonably expected to rely on it when making "
            "an investment decision is less likely to be treated as financial advice. This is "
            "context-dependent rather than content-dependent -- the same words said to a "
            "professional audience in an academic seminar sit differently from the identical "
            "words said one-on-one to a retail customer who has just asked 'what should I do "
            "with my savings'. For a conversational financial chatbot, this test cuts against "
            "the chatbot: a user asking a direct question in a one-on-one chat interface is "
            "close to the paradigm case of someone who may reasonably rely on whatever answer "
            "comes back, which pushes borderline outputs toward being treated as advice rather "
            "than neutral commentary. Confirmed directly from the MAS guidelines PDF, para 3.5."
        ),
    },
    {
        "id": "doc_07",
        "title": "Generic Opinions vs Tailored Advice",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), para 3.6(a)",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "Among the factors MAS lists as making a communication less likely to be financial "
            "advice, para 3.6(a) points to genericness: an opinion is less likely to be advice "
            "when it is generic and not tailored to take into account the unique circumstances "
            "of a particular individual. A broadcast statement like 'equities have historically "
            "outperformed bonds over 20-year periods' aimed at an undefined general audience "
            "sits closer to commentary. But a chatbot conversation is structurally different "
            "from a broadcast: once the system has asked about (or been told) a specific user's "
            "age, risk appetite, existing holdings, or goals, and then frames a view about a "
            "product in light of those facts, the tailoring that this factor cares about is "
            "present, and the generic-opinion shelter weakens or disappears. This factor never "
            "operates alone -- see the totality-of-context card. Confirmed directly from the MAS "
            "guidelines PDF, para 3.6(a)."
        ),
    },
    {
        "id": "doc_08",
        "title": "The Call-to-Action Factor",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), para 3.6(b)",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "A second listed factor looks at whether the communication actually pushes the "
            "listener toward or away from a specific action. Para 3.6(b) treats it as less "
            "likely to be advice where the communication does not 'recommend that the recipient "
            "take or not take a course of action' regarding an investment product. Read narrowly, "
            "this sounds like a simple presence/absence-of-a-verb test -- did the output say "
            "'you should buy/sell/hold' -- but MAS's own examples elsewhere make clear that "
            "strong implicit steering (e.g. listing only the upside of one product while a user "
            "is visibly deciding between two) can function as a recommendation even without the "
            "word 'recommend' appearing. For a chatbot detector, this means keyword-matching on "
            "imperative verbs alone ('buy', 'sell') will miss softer steering language and is an "
            "unreliable proxy for this factor on its own. Confirmed directly from the MAS "
            "guidelines PDF, para 3.6(b)."
        ),
    },
    {
        "id": "doc_09",
        "title": "Holding Out as an Advice Business",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), paras 3.6(c) and 3.9",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "Two related factors look past a single message to the nature of the operation "
            "producing it. Para 3.6(c) treats a communication as less likely to be advice where "
            "the provider does not hold itself out, or purport to be, in the business of giving "
            "financial advice. Para 3.9 then unpacks the separate 'carrying on a business' "
            "question that determines whether a licence is even needed: MAS looks at whether "
            "advice is given systematically and with continuity through an organised or "
            "structured method, and whether remuneration or other benefits flow from decisions "
            "the client makes as a result. Notably, the absence of a direct fee does not, by "
            "itself, mean there is no advice business -- a 'free' chatbot that is monetised "
            "indirectly (e.g. through referral fees when a user opens an account) can still be "
            "carrying on a financial advisory business under this test. Confirmed directly from "
            "the MAS guidelines PDF."
        ),
    },
    {
        "id": "doc_10",
        "title": "Totality of Context: No Single Factor Decides",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), para 3.7",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "After listing the individual factors -- opinion vs fact, reliance, genericness, "
            "call-to-action, holding-out -- MAS's guidance closes the loop with an explicit "
            "warning against checklist thinking: para 3.7 states that even where several of "
            "these mitigating factors are present, they do not conclusively establish that a "
            "communication is not financial advice, because 'the entire context of the "
            "communication has to be taken into consideration'. This is the card that should "
            "stop a naive AdviceGuard design from scoring each factor independently and summing "
            "the results. It also explains why the surrounding cards (opinion test, factual-"
            "information limit, disclaimer non-safe-harbour, reliance, genericness, call-to-"
            "action, holding-out) exist as a cluster: they are meant to be read together, and "
            "any one of them read in isolation will misstate MAS's actual position. Confirmed "
            "directly from the MAS guidelines PDF, para 3.7."
        ),
    },
    {
        "id": "doc_11",
        "title": "Passive Distribution of Research Reports",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), paras 4.1-4.2",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "Section 4 of the guidelines applies the general factors to specific situations. "
            "Paras 4.1-4.2 address firms or platforms that merely republish someone else's "
            "research analysis or report on an investment product. MAS treats such a party as a "
            "'passive distribution conduit' that does not itself provide advice, provided the "
            "report genuinely originates from a properly licensed or exempt entity, is "
            "attributed accurately to that originator, is not edited or supplemented with the "
            "distributor's own commentary, and is not presented as an endorsement by the "
            "distributor. This matters for AdviceGuard because a chatbot that quotes or "
            "surfaces a third-party analyst report verbatim, with clear attribution and no added "
            "spin, sits closer to this passive-conduit exception than one that paraphrases the "
            "report's conclusion in its own words as if it were the chatbot's own view. "
            "Confirmed directly from the MAS guidelines PDF."
        ),
    },
    {
        "id": "doc_12",
        "title": "Portfolio Allocation Advice Without a Specific Product",
        "source": "MAS Guidelines on Provision of Financial Advisory Service (10 Jul 2019), paras 4.3-4.4",
        "url": "https://www.mas.gov.sg/-/media/MAS/Regulations-and-Financial-Stability/Regulations-Guidance-and-Licensing/Financial-Advisers/Guidelines/Guidelines-on-Provision-of-Financial-Advisory-Service-10-July-2019.pdf",
        "text": (
            "MAS separately addresses guidance about asset allocation in the abstract -- for "
            "example, suggesting a split across equities, bonds and cash, or across "
            "geographies -- without pointing to any specific, identifiable investment product "
            "or class of investment products. Para 4.4 states that MAS 'does not consider "
            "portfolio allocation advice ... to be financial advice' where it does not involve "
            "recommendations on a specific investment product or class of investment products. "
            "Providers relying on this should still disclaim that they are not FAA-regulated and "
            "point users to a licensed adviser for product-level decisions. The practical "
            "edge case for a chatbot: 'put 60% in equities, 40% in bonds' is arguably outside "
            "the FAA gate under this paragraph, but 'put 60% in Fund X, 40% in Bond ETF Y' names "
            "specific products and falls back inside the opinion test in doc_03. Confirmed "
            "directly from the MAS guidelines PDF, paras 4.3-4.4."
        ),
    },
    {
        "id": "doc_13",
        "title": "Section 27: The Reasonable Basis Requirement",
        "source": "Financial Advisers Act 2001, Section 27, as referenced in MAS Notice FAA-N16 (Recommendations on Investment Products), para 8",
        "url": "https://www.mas.gov.sg/regulation/notices/notice-faa-n16",
        "text": (
            "Once a communication has crossed the line into being a 'recommendation' (see the "
            "opinion-test cluster of cards for where that line sits), a separate and stricter "
            "obligation attaches under the FAA itself. Section 27 of the Act requires a licensed "
            "financial adviser to have a reasonable basis for any recommendation it makes about "
            "an investment product to a person who may reasonably be expected to rely on that "
            "recommendation. 'Reasonable basis' is not a vague aspiration -- MAS Notice FAA-N16 "
            "builds out concrete supporting obligations around it, including the know-your-"
            "client information-gathering duty (doc_14) and the written acknowledgment duty "
            "(doc_15). This section 27 duty is the general, source-of-truth obligation: it "
            "applies to any regulated recommendation, whether given by a human representative "
            "or generated by an automated system, and is not itself relaxed by the lighter "
            "know-your-client path MAS allows for digital advisers (see doc_17). Confirmed "
            "directly from a fetch of FAA-N16, para 8."
        ),
    },
    {
        "id": "doc_14",
        "title": "Know-Your-Client: What Information Must Be Collected",
        "source": "MAS Notice FAA-N16 (Recommendations on Investment Products), para 11",
        "url": "https://www.mas.gov.sg/regulation/notices/notice-faa-n16",
        "text": (
            "To support the reasonable-basis requirement in Section 27 (doc_13), FAA-N16 para "
            "11 sets out the categories of client information a financial adviser must document "
            "before making a recommendation: the client's investment objectives and risk "
            "tolerance; employment status; overall financial situation (assets, liabilities, "
            "cash flow and income); sources and amount of income; existing financial "
            "commitments; the client's current investment portfolio, including any life "
            "policies already held; whether the proposed investment would represent a "
            "substantial portion of the client's assets; and, where a life policy is being "
            "recommended, information about the client's dependants. This is the formal "
            "know-your-client (KYC) checklist behind any suitability judgement -- a "
            "recommendation made without gathering this information (or a documented reason why "
            "an item does not apply) is exposed on the 'reasonable basis' requirement even if "
            "the product itself is unremarkable. Confirmed directly from a fetch of FAA-N16, "
            "para 11."
        ),
    },
    {
        "id": "doc_15",
        "title": "Telling Clients Their Information Is the Basis for the Recommendation",
        "source": "MAS Notice FAA-N16 (Recommendations on Investment Products), para 14",
        "url": "https://www.mas.gov.sg/regulation/notices/notice-faa-n16",
        "text": (
            "FAA-N16 para 14 adds a disclosure duty that sits alongside the know-your-client "
            "collection duty (doc_14): the adviser must highlight to the client, in writing, "
            "that the recommendation is based on the information the client has provided, and "
            "that if that information is inaccurate or incomplete the resulting recommendation "
            "may not be suitable. This closes a loop that a chatbot design can otherwise miss -- "
            "it is not enough to ask a user a handful of profiling questions once; the system "
            "should also make clear, at the point a recommendation is delivered, that its "
            "suitability depends on the accuracy of what the user told it. Without this written "
            "acknowledgment, a client who gave incomplete answers has less basis to understand "
            "why a recommendation might not fit their real situation. Confirmed directly from a "
            "fetch of FAA-N16, para 14."
        ),
    },
    {
        "id": "doc_16",
        "title": "FAA-N03: What Must Be Disclosed to Clients",
        "source": "MAS Notice FAA-N03 (Information to Clients and Product Information Disclosure)",
        "url": "https://www.mas.gov.sg/regulation/notices/notice-faa-n03",
        "text": (
            "Separate from the reasonable-basis and KYC duties in FAA-N16, Notice FAA-N03 "
            "governs what information must be given to a client, independent of whether a "
            "specific recommendation is even made. It requires disclosure of general "
            "information about the financial adviser and the representative dealing with the "
            "client (including their regulatory status); how the adviser and representative are "
            "remunerated; potential conflicts of interest that could colour a recommendation; "
            "the key features, benefits and risks of a 'designated investment product'; and "
            "relevant historical or projected performance information for such products, along "
            "with rules on how promotional material may present that performance. This card "
            "is a useful adjacent-vocabulary distractor for retrieval: it shares words like "
            "'risk', 'recommendation' and 'disclosure' with the reasonable-basis cluster, but it "
            "is about disclosure obligations, not about whether a statement counts as advice in "
            "the first place. Exact paragraph numbers within FAA-N03 could not be confirmed in "
            "this session; the categories above come from a fetch of the MAS notice's own "
            "summary page, not a paragraph-by-paragraph read of the full notice PDF."
        ),
    },
    {
        "id": "doc_17",
        "title": "Digital Advisers Get a Lighter KYC Path -- Not a Lighter Advice Standard",
        "source": "MAS Guidelines on Provision of Digital Advisory Services (2018)",
        "url": "https://www.mas.gov.sg/news/media-releases/2018/mas-issues-guidelines-to-facilitate-provision-of-digital-advisory-services",
        "text": (
            "For robo-advisers, MAS eased one specific piece of friction: digital advisers can "
            "be exempted from collecting the full suite of client financial-circumstance "
            "information that FAA-N16 otherwise calls for (doc_14), and may instead use short "
            "fact-finding questionnaires designed to identify and turn away clients who are "
            "clearly unsuitable for the automated service (a 'knock-out' screening approach) "
            "rather than a complete profile. This is a narrow, information-gathering relief. It "
            "is easy to misread this as digital advisers being held to a lower advice standard "
            "generally -- they are not: the underlying obligation to have a reasonable basis for "
            "any recommendation the algorithm produces, under Section 27 of the FAA (doc_13), "
            "is a separate duty that this relief does not touch. A robo-adviser that screens "
            "clients with a short questionnaire still needs its recommendation logic itself to "
            "be reasonably based. Confirmed via the 2018 MAS media release; not independently "
            "cross-checked against the full guidelines text."
        ),
    },
    {
        "id": "doc_18",
        "title": "Algorithm Governance for Robo-Advisers",
        "source": "MAS Guidelines on Provision of Digital Advisory Services (2018)",
        "url": "https://www.mas.gov.sg/news/media-releases/2018/mas-issues-guidelines-to-facilitate-provision-of-digital-advisory-services",
        "text": (
            "Alongside the eased client-information path (doc_17), MAS's digital advisory "
            "guidelines impose a governance duty specific to automated recommendation engines: "
            "providers must put in place robust frameworks to govern and supervise the "
            "algorithms that generate recommendations, and to manage the technology and cyber "
            "risks that come with an automated business model -- MAS's own framing flags "
            "'faulty algorithms and cyber threats' as the characteristic new risks of this "
            "channel, compared to a human adviser. Senior management is expected to maintain "
            "oversight of the algorithm design and to ensure customers are given proper "
            "disclosures so they can make an informed decision about using an automated rather "
            "than human advisory service. This session's source did not surface detailed, "
            "specific back-testing or algorithm-validation methodology requirements -- only the "
            "general governance and oversight expectation -- so any claim about a specific "
            "testing standard beyond this should not be attributed to this guideline without "
            "further verification."
        ),
    },
    {
        "id": "doc_19",
        "title": "Fair Dealing Outcome 2: Suitable Products and Services",
        "source": "MAS Guidelines on Fair Dealing (revised, effective from the 2024 update)",
        "url": "https://www.mas.gov.sg/news/media-releases/2024/mas-expands-application-of-fair-dealing-guidelines",
        "text": (
            "The Guidelines on Fair Dealing set out five customer-facing outcomes financial "
            "institutions are expected to deliver; Outcome 2 is that products and services "
            "offered are suited to the target customer segment. In practice this means a firm "
            "should assess how a product performs under different market conditions, run due "
            "diligence before offering it, identify customer segments for whom the product is "
            "clearly not suitable and keep them out of the target market, and give 'sufficient "
            "advice' before selling a complex investment product. This outcome sits one level "
            "above an individual recommendation: it is about the firm's product design and "
            "distribution controls, not just about whether any single chatbot answer was "
            "suitable for the one user who asked. It shares heavy vocabulary overlap ('suitable', "
            "'complex product', 'advice') with the Section 27 / FAA-N16 cluster (docs 13-15), "
            "which is intentional -- the two regimes address suitability from different angles "
            "(firm-level design vs individual recommendation) and are easy to conflate. "
            "Confirmed directly from a fetch of a source summarising the guidelines."
        ),
    },
    {
        "id": "doc_20",
        "title": "Fair Dealing Outcome 4: Clear, Relevant and Accurate Information",
        "source": "MAS Guidelines on Fair Dealing (revised, effective from the 2024 update)",
        "url": "https://www.mas.gov.sg/news/media-releases/2024/mas-expands-application-of-fair-dealing-guidelines",
        "text": (
            "Outcome 4 of the Guidelines on Fair Dealing requires financial institutions to give "
            "customers 'clear, relevant and timely information that accurately represent the "
            "products and services', before, during and after a sale. For marketing and "
            "point-of-sale material specifically, this includes highlighting key risks and "
            "disclosing the range of possible outcomes for a financial product, including "
            "worst-case scenarios, rather than only the upside case. Note the 2024 revision also "
            "broadened who this applies to: the Fair Dealing guidelines originally covered only "
            "investment product selection, marketing and advice under the FAA, and were widened "
            "in 2024 to cover all financial institutions and all of their products and "
            "services, not just investment products. This outcome is another close neighbour, "
            "vocabulary-wise, to the FAA-N03 disclosure card (doc_16) and the risk-disclosure "
            "language elsewhere in this corpus -- useful as a deliberate distractor pairing. "
            "Confirmed directly from a fetch of a source summarising the guidelines."
        ),
    },
]

if __name__ == "__main__":
    assert len(DOCS) == 20, f"expected 20 docs, got {len(DOCS)}"
    ids = [d["id"] for d in DOCS]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for d in DOCS:
        for key in ("id", "title", "source", "url", "text"):
            assert key in d and d[key], f"{d.get('id')} missing {key}"
        wc = len(d["text"].split())
        if not (100 <= wc <= 300):
            print(f"WARNING: {d['id']} word count {wc} outside 100-300 (target 120-250)")
    print(f"OK: {len(DOCS)} documents loaded.")
