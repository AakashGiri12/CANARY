"""Fills FINAL_PRESENTATION.pptx's content placeholders with real CANARY
project content, keeping the template (layouts, master, fonts, colors,
positions) untouched per explicit instruction — only text content and
result charts are added.

Slide 1 (title) is deliberately left completely untouched: project
title, team member name, and mentor name are the user's to fill in.
Same for the "Project Title" running footer on every other slide, and
the mentor's name on the Acknowledgement slide (left as a bracketed
placeholder).

Run once: .venv/bin/python3 docs/ppt_assets/fill_deck.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Inches

ROOT = Path(__file__).resolve().parents[2]
DECK_PATH = ROOT / "FINAL_PRESENTATION.pptx"
ASSETS = Path(__file__).parent


def clean_heading_text(raw: str) -> str:
    """Strips the template's trailing style-note ("…. Calibri body -36"
    etc.) from a heading's concatenated run text."""
    idx = raw.find("Calibri body")
    if idx != -1:
        raw = raw[:idx]
    return raw.rstrip(" .…-\n\t")


def set_heading(shape, override: str | None = None) -> None:
    tf = shape.text_frame
    p = tf.paragraphs[0]
    raw = "".join(r.text for r in p.runs)
    text = override if override is not None else clean_heading_text(raw)
    first_run = p.runs[0]
    first_run.text = text
    for r in list(p.runs[1:]):
        r._r.getparent().remove(r._r)


def _template_font(shape):
    """Finds the first run in the body placeholder with explicit font
    properties, to reuse for newly-added bullet runs (falls back to
    None, i.e. inherit from the layout, when the template never set one
    explicitly for that property)."""
    size = bold = name = color = None
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            if size is None and r.font.size is not None:
                size = r.font.size
            if bold is None and r.font.bold is not None:
                bold = r.font.bold
            if name is None and r.font.name is not None:
                name = r.font.name
            if color is None:
                try:
                    color = r.font.color.rgb
                except Exception:
                    pass
    return size, bold, name, color


def _strip_bullet_override(paragraph) -> None:
    """The template's original first paragraph had an explicit
    <a:buNone/> (or similar) on it, so after reusing that paragraph for
    our first bullet it rendered without a bullet glyph while the
    freshly-added paragraphs (no override, inherit from the layout) got
    one — found live, visibly inconsistent. Stripping any bullet
    override makes every paragraph inherit the same bullet from the
    layout, matching the template's own default rather than a one-off."""
    pPr = paragraph._p.find(qn("a:pPr"))
    if pPr is None:
        return
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        el = pPr.find(qn(tag))
        if el is not None:
            pPr.remove(el)
    # marL="0" indent="0" on the original first paragraph zeroed out the
    # bullet's hanging indent, so its dot sat flush against the text
    # while every other (inherited-default) paragraph had proper
    # spacing — found live, visibly inconsistent. Drop just these two
    # attributes; keep everything else (e.g. the template's deliberate
    # 150% line spacing) intact.
    for attr in ("marL", "indent"):
        if pPr.get(attr) is not None:
            del pPr.attrib[attr]


def set_bullets(shape, bullets: list[str]) -> None:
    size, bold, name, color = _template_font(shape)
    tf = shape.text_frame
    tf.clear()
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _strip_bullet_override(p)
        run = p.add_run()
        run.text = bullet
        if size is not None:
            run.font.size = size
        if bold is not None:
            run.font.bold = bold
        if name is not None:
            run.font.name = name
        if color is not None:
            run.font.color.rgb = color


def fill_slide(slide, *, heading_override=None, bullets=None):
    for shape in slide.shapes:
        if shape.name == "TextBox 2":
            set_heading(shape, override=heading_override)
        elif shape.name == "Text Placeholder 1" and bullets is not None:
            set_bullets(shape, bullets)


def main() -> None:
    prs = Presentation(DECK_PATH)
    slides = prs.slides

    # Slide 1 (title) intentionally untouched — user fills it in.

    fill_slide(
        slides[1],  # Introduction
        bullets=[
            "Prompt injection: malicious instructions hidden in untrusted tool output (email, files, web pages) that hijack an AI agent.",
            "CANARY is a full pipeline to attack, defend, and measure this vulnerability end-to-end.",
            "Four components: Target Agent, Attack Engine, Defense Layer, Eval Harness.",
            "Core contribution: an adaptive, retrieval-informed attacker — not just a static benchmark.",
            "Built entirely on free-tier cloud infrastructure, by design.",
        ],
    )

    fill_slide(
        slides[2],  # Objective
        bullets=[
            "Build an end-to-end pipeline to measure LLM-agent vulnerability to prompt injection.",
            "Quantify the Utility vs. Attack Success Rate trade-off across defense configs (the Pareto frontier).",
            "Show that static, pattern-based defenses have blind spots an adaptive attacker can find.",
            "Compare a lightweight prompt-based defense against a trained ML classifier.",
            "Validate everything against a real, live LLM — not only rule-based stand-ins.",
        ],
    )

    fill_slide(
        slides[3],  # was "Module name" — repurposed as Related Work
        heading_override="Related Work",
        bullets=[
            "AgentDojo (Debenedetti et al., 2024) — benchmark for prompt injection attacks/defenses on tool-using LLM agents.",
            "InjecAgent (Zhan et al., ACL Findings 2024) — benchmarking indirect prompt injection in tool-integrated agents.",
            "OWASP Top 10 for LLM Applications — Prompt Injection ranked LLM01, the top risk, every edition.",
            "Off-the-shelf injection classifiers (e.g. ProtectAI, Meta Prompt Guard) exist as baselines, not yet integrated here.",
            "Gap: most published evaluations use a fixed attack set — few model an attacker that adapts to the defense.",
        ],
    )

    fill_slide(
        slides[4],  # Problem Statement
        bullets=[
            "Agents that read untrusted content (email, web, files) can be hijacked by embedded instructions.",
            "Static regex/keyword defenses only catch the exact framings they were designed for.",
            "Published evaluations rarely model an attacker that adapts based on what got blocked.",
            "Need: one system that attacks, adapts, defends, and measures Utility and ASR together.",
        ],
    )

    fill_slide(
        slides[5],  # Methodology
        bullets=[
            "Build order: Target Agent → static Attack Engine + Eval Harness → prompt defense → adaptive Attack Engine (pgvector retrieval) → trained classifier → persistence → dashboard.",
            "Adaptive loop: embed context → retrieve similar past outcomes → mutate the framing → run → score → write outcome back to memory.",
            "Every run scored on two axes: Utility (did the real task succeed) and ASR (did the injection succeed).",
            "ASR judged by an LLM judge, validated 6/6 against hand-labeled cases — including two real failures a keyword heuristic missed.",
        ],
    )

    fill_slide(
        slides[6],  # Approach/Algorithms/Tools
        bullets=[
            "Agent framework: LangGraph — StateGraph (agent node → tool node → loop to final answer).",
            "LLM backend: DeepSeek API — a time-constrained, mentor-approved substitute for the originally-designed self-hosted vLLM-on-GCP architecture (kept fully built, for reference).",
            "Attack Engine: 7 static seed attacks + retrieval-informed adaptive mutation.",
            "Defense Layer: prompt-based structural defense + trained DeBERTa-v3 classifier.",
            "Infra: PostgreSQL + pgvector, Redis + Celery, FastAPI, Next.js dashboard, pytest (64 tests).",
        ],
    )

    fill_slide(
        slides[7],  # Findings and Results — kept short: this slide's
        # text column is narrowed to make room for the result charts
        # added below, so long bullets overflow the content area (found
        # live — the 5-bullet version ran past the slide boundary).
        bullets=[
            "Real target model: 0% ASR vs. all 7 attacks, defended or not.",
            "Rule-based baseline: 71% ASR — pipeline measures real vulnerability.",
            "Adaptive attacker breaks the prompt defense: 0%→100% ASR by gen 3.",
            "Classifier: small = 83% acc (validated); base collapsed to 50%.",
        ],
    )

    fill_slide(
        slides[8],  # Conclusion
        bullets=[
            "Built and validated a full adversarial-agent-security pipeline, end to end, on free-tier infra.",
            "Static defenses look effective against a fixed attack set but have discoverable blind spots.",
            "An adaptive, retrieval-informed attacker found that blind spot in 3 generations.",
            "Model size isn’t automatically better — the smaller classifier generalized, the base model collapsed.",
            "Future work: off-the-shelf classifier baseline, semantic adaptive mutation, Oracle VM + GCP redeployment.",
        ],
    )

    fill_slide(
        slides[9],  # Acknowledgement — mentor name left as placeholder
        bullets=[
            "We would like to thank our mentor, [Mentor Name], for guidance throughout this project.",
            "We thank University and LTIMindTree for the opportunity to pursue this work.",
        ],
    )

    fill_slide(
        slides[10],  # Reference
        bullets=[
            "Debenedetti et al., “AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents,” arXiv:2406.13352, 2024.",
            "Zhan et al., “InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated LLM Agents,” Findings of ACL 2024, arXiv:2403.02691.",
            "OWASP Top 10 for LLM Applications — owasp.org/www-project-top-10-for-large-language-model-applications.",
            "He, Gao, Chen, “DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training,” arXiv:2111.09543 — microsoft/deberta-v3-small, microsoft/deberta-v3-base.",
            "LangGraph documentation — langchain-ai.github.io/langgraph.",
            "DeepSeek API documentation — platform.deepseek.com/api-docs.",
        ],
    )

    # --- Findings and Results: add the real result charts ---
    findings_slide = slides[7]
    body = next(s for s in findings_slide.shapes if s.name == "Text Placeholder 1")
    left, top, width, height = body.left, body.top, body.width, body.height

    # Shrink the bullet text box to the left ~48% so two chart images fit
    # to its right, inside the same content-area bounds the template
    # already reserved (no new space claimed from the slide).
    body.width = int(width * 0.46)

    chart_w = int(width * 0.50)
    gap = int(width * 0.02)
    chart_left = left + body.width + gap
    chart_h = int(height * 0.48)

    findings_slide.shapes.add_picture(
        str(ASSETS / "config_comparison.png"),
        chart_left,
        top,
        width=chart_w,
        height=chart_h,
    )
    findings_slide.shapes.add_picture(
        str(ASSETS / "adaptive_curve.png"),
        chart_left,
        top + chart_h + int(height * 0.02),
        width=int(chart_w * 0.48),
        height=int(height * 0.48),
    )
    findings_slide.shapes.add_picture(
        str(ASSETS / "classifier_bars.png"),
        chart_left + int(chart_w * 0.52),
        top + chart_h + int(height * 0.02),
        width=int(chart_w * 0.48),
        height=int(height * 0.48),
    )

    prs.save(DECK_PATH)
    print(f"Saved {DECK_PATH}")


if __name__ == "__main__":
    main()
