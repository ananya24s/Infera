"""Verification agent — two independent NLI checks, both by the trained model:

1. STANCE (SciFact-style). Each sub-question is restated as a hypothesis
   ("Creatine improves cognition."). For every retrieved paper we ask the NLI
   model whether its abstract supports, refutes, or says nothing about that
   hypothesis. The most decisive abstract sentence is kept as the rationale.
   These per-paper stances are what consensus/controversy is computed from.

2. FIDELITY. Every extracted claim is checked against its own source abstract.
   This is the citation-hallucination check: a claim an LLM distorted or
   invented during extraction won't be entailed by the abstract it cites.

Each extracted claim also gets a stance (does this finding support or refute
the hypothesis), shown in the claim explorer.
"""
from __future__ import annotations

import numpy as np

from app.agents.query_planning import question_to_hypothesis
from app.ml.nli_model import NLIResult, verify_batch
from app.models.schemas import PaperStance, Verdict, VerificationLabel
from app.orchestrator.state import ResearchState
from app.services.text import split_sentences

SUPPORTS = VerificationLabel.SUPPORTS
REFUTES = VerificationLabel.REFUTES
NEI = VerificationLabel.NOT_ENOUGH_INFO

# A passage must be at least this sure a hypothesis is supported/refuted to count
# as taking a position; anything weaker is "not enough info".
STANCE_MIN_PROB = 0.5

# A passage must also be *about* the hypothesis (embedding cosine similarity) to count
# as evidence for or against it. NLI alone will call an off-topic sentence a
# "contradiction" — e.g. a line about supplement health risks vs "creatine improves
# cognition". Measured on real retrievals: on-topic evidence scored 0.70-0.78,
# the off-topic false positive 0.34.
MIN_RELEVANCE = 0.40


def _hypotheses(state: ResearchState) -> dict[str | None, str]:
    hyp = {sq.id: (sq.hypothesis or question_to_hypothesis(sq.text)) for sq in state.sub_questions}
    hyp[None] = next(iter(hyp.values()), question_to_hypothesis(state.question))
    return hyp


def _decisiveness(r: NLIResult) -> tuple[VerificationLabel, float]:
    """The stronger of support/refute for this passage, and how strong."""
    return (SUPPORTS, r.prob(SUPPORTS)) if r.prob(SUPPORTS) >= r.prob(REFUTES) else (REFUTES, r.prob(REFUTES))


def _relevance(passages: list[str], hypotheses: list[str]) -> list[float]:
    """Cosine similarity of each passage to its hypothesis (row-wise)."""
    from app.services.hybrid_search import _embedder

    embedder = _embedder()
    a = np.asarray(embedder.encode(passages, normalize_embeddings=True, show_progress_bar=False, batch_size=64))
    unique = sorted(set(hypotheses))
    h_vecs = dict(zip(unique, np.asarray(embedder.encode(unique, normalize_embeddings=True, show_progress_bar=False))))
    return [float(a[i] @ h_vecs[h]) for i, h in enumerate(hypotheses)]


def _paper_stances(state: ResearchState, hyp: dict[str | None, str]) -> list[PaperStance]:
    pairs: list[tuple[str, str]] = []
    # (paper index, sentence-or-None for the whole abstract) for each pair
    owners: list[tuple[int, str | None]] = []
    papers = [p for p in state.papers if p.abstract and (p.sub_question_id in hyp)]
    for i, paper in enumerate(papers):
        h = hyp[paper.sub_question_id]
        for sentence in split_sentences(paper.abstract):
            pairs.append((sentence, h))
            owners.append((i, sentence))
        # Whole-abstract pass: catches conclusions whose sentence alone lacks the subject.
        pairs.append((paper.abstract, h))
        owners.append((i, None))

    results = verify_batch(pairs)
    relevance = _relevance([p for p, _h in pairs], [h for _p, h in pairs])

    best: dict[int, tuple[VerificationLabel, float, str | None]] = {}
    best_sentence: dict[int, tuple[float, str]] = {}
    for (i, sentence), r, rel in zip(owners, results, relevance):
        label, prob = _decisiveness(r)
        if rel < MIN_RELEVANCE:
            prob = 0.0  # off-topic passage: can't be evidence either way
        if i not in best or prob > best[i][1]:
            best[i] = (label, prob, sentence)
        if sentence is not None and (i not in best_sentence or prob > best_sentence[i][0]):
            best_sentence[i] = (prob, sentence)

    stances: list[PaperStance] = []
    for i, paper in enumerate(papers):
        label, prob, _ = best[i]
        rationale = best_sentence.get(i, (0.0, ""))[1]
        if prob >= STANCE_MIN_PROB:
            stances.append(PaperStance(paper_id=paper.paper_id, sub_question_id=paper.sub_question_id,
                                       label=label, confidence=prob, evidence_sentence=rationale))
        else:
            # Nothing in the abstract takes a position: confidence is in "neutral".
            stances.append(PaperStance(paper_id=paper.paper_id, sub_question_id=paper.sub_question_id,
                                       label=NEI, confidence=1.0 - prob, evidence_sentence=""))
    return stances


def _nearest_sentence(claim: str, sentences: list[str]) -> str:
    if not sentences:
        return ""
    from app.services.hybrid_search import _embedder

    vecs = _embedder().encode([claim] + sentences, normalize_embeddings=True, show_progress_bar=False)
    return sentences[int(np.argmax(np.asarray(vecs[1:]) @ np.asarray(vecs[0])))]


def _claim_verdicts(state: ResearchState, hyp: dict[str | None, str]) -> list[Verdict]:
    claims = [c for c in state.claims if state.paper_by_id(c.source_paper_id)]
    if not claims:
        return []
    papers = {c.id: state.paper_by_id(c.source_paper_id) for c in claims}

    hyps = [hyp.get(c.sub_question_id, hyp[None]) for c in claims]
    stance = verify_batch([(c.text, h) for c, h in zip(claims, hyps)])
    fidelity = verify_batch([(papers[c.id].abstract, c.text) for c in claims])
    relevance = _relevance([c.text for c in claims], hyps)

    verdicts: list[Verdict] = []
    for claim, s, f, rel in zip(claims, stance, fidelity, relevance):
        s_label, s_prob = _decisiveness(s)
        if rel < MIN_RELEVANCE:
            s_prob = 0.0
        if s_prob >= STANCE_MIN_PROB:
            label, conf = s_label, s_prob
        else:
            label, conf = NEI, 1.0 - s_prob
        verdicts.append(
            Verdict(
                claim_id=claim.id,
                label=label,
                confidence=conf,
                fidelity=f.label,
                fidelity_confidence=f.confidence,
                evidence_sentence=_nearest_sentence(claim.text, split_sentences(papers[claim.id].abstract)),
            )
        )
    return verdicts


def run(state: ResearchState) -> None:
    hyp = _hypotheses(state)
    state.paper_stances = _paper_stances(state, hyp)
    state.verdicts = _claim_verdicts(state, hyp)
