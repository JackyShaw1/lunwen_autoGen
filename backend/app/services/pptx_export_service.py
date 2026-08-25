"""Build editable, classroom-ready PPTX decks from a structured teaching case package."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from app.config import settings
from app.services.material_service import get_cached_material_image, resolve_package_materials


THEMES = {
    "academic": {
        "primary": "312E81", "accent": "4F46E5", "soft": "EEF2FF",
        "background": "F8FAFC", "surface": "FFFFFF", "text": "172033", "muted": "64748B",
    },
    "modern": {
        "primary": "0F3D56", "accent": "0D9488", "soft": "CCFBF1",
        "background": "F6FAFA", "surface": "FFFFFF", "text": "132A35", "muted": "607580",
    },
    "minimal": {
        "primary": "111827", "accent": "D97706", "soft": "FEF3C7",
        "background": "FAFAF9", "surface": "FFFFFF", "text": "1C1917", "muted": "78716C",
    },
}

DENSITY = {
    "concise": {"bullets": 3, "bullet_chars": 52, "narrative_slides": 3, "questions": 3},
    "standard": {"bullets": 4, "bullet_chars": 68, "narrative_slides": 5, "questions": 3},
    "detailed": {"bullets": 5, "bullet_chars": 88, "narrative_slides": 8, "questions": 2},
}


def _clean_text(value: Any) -> str:
    text = re.sub(r"【(?:背景|叙事|案例正文)】", "", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _split_sentences(text: str) -> list[str]:
    normalized = str(text or "").replace("\r\n", "\n").strip()
    parts = re.split(r"(?<=[。！？；])\s*|\n+", normalized)
    return [_clean_text(part) for part in parts if _clean_text(part)]


def _fit_segment(sentence: str, max_chars: int) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]
    clauses = [part.strip() for part in re.split(r"(?<=[，、：])", sentence) if part.strip()]
    result: list[str] = []
    current = ""
    for clause in clauses:
        if current and len(current) + len(clause) > max_chars:
            result.append(current)
            current = clause
        else:
            current += clause
    if current:
        result.append(current)
    hard_limit = int(max_chars * 1.3)
    return [item if len(item) <= hard_limit else item[:hard_limit] + "…" for item in result]


def _content_pages(text: str, density: str, max_slides: int | None = None) -> list[list[str]]:
    rule = DENSITY[density]
    segments: list[str] = []
    for sentence in _split_sentences(text):
        segments.extend(_fit_segment(sentence, rule["bullet_chars"]))
    pages = [segments[index : index + rule["bullets"]] for index in range(0, len(segments), rule["bullets"])]
    if max_slides and len(pages) > max_slides:
        kept = pages[:max_slides]
        if sum(len(page) for page in pages[max_slides:]):
            kept[-1][-1] = kept[-1][-1].rstrip("。…") + "……（其余细节请结合案例原文阅读）"
        return kept
    return pages or [["暂无内容"]]


def build_ppt_outline(package: dict[str, Any], options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    density = options.get("density", "standard")
    if density not in DENSITY:
        density = "standard"
    audience = options.get("audience", "teacher")
    if audience not in {"student", "teacher"}:
        audience = "teacher"
    theme = options.get("theme", "academic")
    if theme not in THEMES:
        theme = "academic"

    meta = package.get("meta") or {}
    body = package.get("body") or {}
    title = _clean_text(meta.get("title") or "教学案例")
    course = _clean_text(meta.get("course") or meta.get("subject") or "课程教学")
    slides: list[dict[str, Any]] = [
        {
            "kind": "cover", "title": title,
            "subtitle": f"{course} · {meta.get('case_type', '教学案例')} · {meta.get('target_audience', '')}",
        }
    ]

    objectives = [
        _clean_text(item.get("description"))
        for item in package.get("learning_objectives") or []
        if _clean_text(item.get("description"))
    ]
    if objectives:
        slides.append({"kind": "objectives", "section": "课程导入", "title": "本课学习目标", "items": objectives})

    for index, items in enumerate(_content_pages(body.get("background", ""), density), 1):
        slides.append({
            "kind": "bullets", "section": "案例情境",
            "title": "案例背景" if index == 1 else f"案例背景 · {index}", "items": items,
        })

    for asset in resolve_package_materials(package, limit=3):
        slides.append({
            "kind": "visual", "section": "案例情境", "title": asset["title"],
            "asset_id": asset["id"], "caption": asset["caption"],
            "source_org": asset["source_org"], "source_page_url": asset["source_page_url"],
            "photographer": asset.get("photographer"),
        })

    characters = body.get("characters") or []
    if characters:
        slides.append({"kind": "characters", "section": "案例情境", "title": "关键角色与立场", "items": characters[:6]})

    narrative_pages = _content_pages(body.get("narrative", ""), density, DENSITY[density]["narrative_slides"])
    phase_names = ["情境建立", "冲突浮现", "证据交锋", "约束升级", "决策临界", "影响扩散", "方案博弈", "行动窗口"]
    for index, items in enumerate(narrative_pages, 1):
        phase = phase_names[min(index - 1, len(phase_names) - 1)]
        slides.append({"kind": "bullets", "section": "案例进程", "title": f"案例进程 {index:02d} · {phase}", "items": items})

    if body.get("decision_point"):
        slides.append({
            "kind": "decision", "section": "课堂决策", "title": "关键决策点",
            "content": _clean_text(body.get("decision_point")),
        })

    questions = package.get("discussion_questions") or []
    question_page_size = DENSITY[density]["questions"]
    for index in range(0, len(questions), question_page_size):
        page_questions = [
            {**question, "_number": index + offset + 1}
            for offset, question in enumerate(questions[index : index + question_page_size])
        ]
        slides.append({
            "kind": "questions", "section": "课堂研讨",
            "title": "课堂讨论" if index == 0 else f"课堂讨论 · {index // question_page_size + 1}",
            "items": page_questions,
            "show_intent": audience == "teacher",
        })

    if audience == "teacher":
        guide = package.get("instructor_guide") or {}
        if guide.get("teaching_flow"):
            slides.append({
                "kind": "bullets", "section": "教学实施", "title": "建议授课流程",
                "items": _content_pages(guide.get("teaching_flow", ""), "concise")[0], "teacher_only": True,
            })
        teaching_items = [
            *[f"教学要点：{_clean_text(item)}" for item in guide.get("key_points") or []],
            *[f"常见误区：{_clean_text(item)}" for item in guide.get("common_misconceptions") or []],
        ]
        if teaching_items:
            slides.append({"kind": "bullets", "section": "教学实施", "title": "教学提示", "items": teaching_items, "teacher_only": True})
        matrix = package.get("alignment_matrix") or []
        if matrix:
            slides.append({"kind": "alignment", "section": "教学实施", "title": "教学目标对齐", "items": matrix[:6], "teacher_only": True})

    slides.append({
        "kind": "closing", "title": "回到决策现场",
        "content": "请基于案例证据形成判断，说明取舍依据、行动路径与风险应对。",
    })
    agenda = ["学习目标", "案例情境", "角色与冲突", "关键决策", "课堂研讨"]
    if audience == "teacher":
        agenda.append("教学实施")
    slides.insert(1, {"kind": "agenda", "title": "今日课堂路径", "items": agenda})
    return {"title": title, "theme": theme, "density": density, "audience": audience, "slides": slides}


def outline_preview(outline: dict[str, Any]) -> dict[str, Any]:
    preview = []
    for index, slide in enumerate(outline["slides"], 1):
        items = slide.get("items") or []
        if items and isinstance(items[0], dict):
            summary = "；".join(_clean_text(item.get("question") or item.get("name") or item.get("objective_id")) for item in items[:2])
        elif items:
            summary = "；".join(_clean_text(item) for item in items[:2])
        else:
            summary = _clean_text(slide.get("content") or slide.get("subtitle") or slide.get("caption"))
        preview.append({
            "index": index, "kind": slide["kind"], "title": slide["title"],
            "summary": summary[:120], "teacher_only": bool(slide.get("teacher_only")),
        })
    return {**{key: outline[key] for key in ("title", "theme", "density", "audience")}, "slide_count": len(preview), "slides": preview}


def _rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def _shape(slide, x, y, w, h, fill: str, radius: bool = True, line: str | None = None):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(fill)
    shape.line.color.rgb = _rgb(line or fill)
    return shape


def _textbox(slide, text: str, x: float, y: float, w: float, h: float, *, size: int = 20,
             color: str = "172033", bold: bool = False, align=PP_ALIGN.LEFT,
             valign=MSO_ANCHOR.TOP, font: str = "Microsoft YaHei"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = Inches(0.05)
    frame.margin_top = frame.margin_bottom = Inches(0.03)
    frame.vertical_anchor = valign
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = str(text or "")
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = _rgb(color)
    return box


def _base_slide(prs: Presentation, palette: dict[str, str], title: str, section: str | None, page: int):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = _rgb(palette["background"])
    _shape(slide, 0, 0, 0.13, 7.5, palette["accent"], radius=False)
    if section:
        _textbox(slide, section.upper(), 0.65, 0.42, 3.5, 0.3, size=9, color=palette["accent"], bold=True)
    _textbox(slide, title, 0.65, 0.78, 12.0, 0.6, size=25, color=palette["primary"], bold=True)
    _shape(slide, 0.65, 7.08, 12.0, 0.012, "D9E2E7", radius=False)
    _textbox(slide, "知案 · AI 教学案例课件", 0.65, 7.16, 4.0, 0.2, size=8, color=palette["muted"])
    _textbox(slide, f"{page:02d}", 11.9, 7.13, 0.75, 0.23, size=9, color=palette["muted"], bold=True, align=PP_ALIGN.RIGHT)
    return slide


def _render_bullets(slide, items: list[str], palette: dict[str, str], *, start_y: float = 1.62):
    count = max(len(items), 1)
    available = 5.05
    row_h = min(1.15, available / count)
    font_size = 20 if count <= 4 else 17
    for index, item in enumerate(items):
        y = start_y + index * row_h
        _shape(slide, 0.72, y + 0.06, 0.38, 0.38, palette["soft"], radius=True)
        _textbox(slide, f"{index + 1}", 0.72, y + 0.075, 0.38, 0.25, size=10, color=palette["accent"], bold=True, align=PP_ALIGN.CENTER)
        _textbox(slide, _clean_text(item), 1.28, y, 11.1, row_h - 0.05, size=font_size, color=palette["text"], valign=MSO_ANCHOR.MIDDLE)


def export_pptx(package: dict[str, Any], title: str, version: int = 1, options: dict[str, Any] | None = None) -> str:
    outline = build_ppt_outline(package, options)
    palette = THEMES[outline["theme"]]
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = outline["title"]
    prs.core_properties.subject = "教学案例课堂课件"
    prs.core_properties.author = "知案 · AI 教学案例工作台"

    for page, spec in enumerate(outline["slides"], 1):
        kind = spec["kind"]
        if kind == "cover":
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            fill = slide.background.fill
            fill.solid(); fill.fore_color.rgb = _rgb(palette["primary"])
            _shape(slide, 0.7, 0.72, 1.15, 0.12, palette["accent"], radius=False)
            _textbox(slide, "教学案例课堂课件", 0.7, 1.08, 5.5, 0.4, size=13, color="FFFFFF", bold=True)
            _textbox(slide, spec["title"], 0.7, 1.72, 11.7, 2.1, size=34, color="FFFFFF", bold=True, valign=MSO_ANCHOR.MIDDLE)
            _textbox(slide, spec.get("subtitle", ""), 0.72, 4.2, 10.8, 0.55, size=17, color="DCE7EC")
            _shape(slide, 0.7, 5.55, 11.9, 0.02, palette["accent"], radius=False)
            _textbox(slide, f"V{version}  ·  {datetime.now():%Y-%m-%d}", 0.72, 5.82, 4.0, 0.35, size=11, color="B9CDD6")
            _textbox(slide, "知案 · AI 教学案例工作台", 8.0, 5.82, 4.6, 0.35, size=11, color="B9CDD6", align=PP_ALIGN.RIGHT)
            continue

        slide = _base_slide(prs, palette, spec["title"], spec.get("section"), page)
        if spec.get("teacher_only"):
            _shape(slide, 10.85, 0.38, 1.55, 0.38, palette["soft"], radius=True)
            _textbox(slide, "教师版专属", 10.9, 0.45, 1.42, 0.2, size=9, color=palette["accent"], bold=True, align=PP_ALIGN.CENTER)

        if kind in {"bullets", "objectives", "agenda"}:
            _render_bullets(slide, spec.get("items") or [], palette)
        elif kind == "visual":
            try:
                image_path = get_cached_material_image(spec["asset_id"])
                slide.shapes.add_picture(str(image_path), Inches(1.02), Inches(1.48), width=Inches(7.45))
            except Exception:
                _shape(slide, 0.72, 1.48, 8.05, 4.95, palette["soft"], line="D9E2E7")
                _textbox(slide, "官方图片暂时无法获取\n请通过来源页面查看", 1.2, 3.05, 7.0, 0.9, size=18, color=palette["muted"], align=PP_ALIGN.CENTER)
            _shape(slide, 9.08, 1.48, 3.45, 4.95, palette["surface"], line="D9E2E7")
            _textbox(slide, spec.get("caption", ""), 9.38, 1.86, 2.85, 1.6, size=16, color=palette["text"], bold=True)
            _textbox(slide, f"来源机构\n{spec.get('source_org', '')}", 9.38, 3.72, 2.85, 0.72, size=11, color=palette["muted"])
            _textbox(slide, f"摄影\n{spec.get('photographer') or '未标注'}", 9.38, 4.62, 2.85, 0.65, size=11, color=palette["muted"])
            _textbox(slide, "教学引用 · 外部分发前确认授权", 9.38, 5.62, 2.85, 0.42, size=9, color=palette["accent"], bold=True)
        elif kind == "characters":
            items = spec.get("items") or []
            cols = 3
            card_w, card_h = 3.72, 2.12
            for index, item in enumerate(items):
                x = 0.7 + (index % cols) * 4.1
                y = 1.62 + (index // cols) * 2.4
                _shape(slide, x, y, card_w, card_h, palette["surface"], line="D9E2E7")
                _shape(slide, x, y, 0.12, card_h, palette["accent"], radius=False)
                _textbox(slide, _clean_text(item.get("name")), x + 0.3, y + 0.25, 1.55, 0.4, size=18, color=palette["primary"], bold=True)
                _textbox(slide, _clean_text(item.get("role")), x + 1.88, y + 0.28, 1.5, 0.3, size=10, color=palette["muted"], align=PP_ALIGN.RIGHT)
                _textbox(slide, _clean_text(item.get("stance")), x + 0.3, y + 0.82, 3.1, 0.95, size=13, color=palette["text"], valign=MSO_ANCHOR.MIDDLE)
        elif kind == "decision":
            _shape(slide, 0.72, 1.7, 11.85, 3.65, palette["surface"], line=palette["accent"])
            _textbox(slide, "DECISION", 1.05, 2.02, 2.0, 0.3, size=10, color=palette["accent"], bold=True)
            _textbox(slide, spec.get("content", ""), 1.05, 2.48, 11.15, 2.25, size=23, color=palette["primary"], bold=True, valign=MSO_ANCHOR.MIDDLE)
            _textbox(slide, "你的选择是什么？依据、取舍和风险分别是什么？", 1.05, 5.62, 10.8, 0.4, size=14, color=palette["muted"])
        elif kind == "questions":
            items = spec.get("items") or []
            row_h = 1.55 if len(items) >= 3 else 2.05
            for index, item in enumerate(items):
                y = 1.58 + index * (row_h + 0.12)
                _shape(slide, 0.72, y, 11.82, row_h, palette["surface"], line="D9E2E7")
                _textbox(slide, f"Q{item.get('_number', index + 1)}", 1.0, y + 0.3, 0.65, 0.35, size=13, color=palette["accent"], bold=True)
                _textbox(slide, f"[{item.get('level', '')}] {_clean_text(item.get('question'))}", 1.72, y + 0.18, 10.35, 0.58, size=17, color=palette["text"], bold=True, valign=MSO_ANCHOR.MIDDLE)
                if spec.get("show_intent") and item.get("teaching_intent"):
                    _textbox(slide, f"教学意图 · {_clean_text(item.get('teaching_intent'))}", 1.72, y + 0.91, 9.9, 0.3, size=10, color=palette["muted"])
        elif kind == "alignment":
            rows = spec.get("items") or []
            headers = ["目标", "案例环节", "课堂活动", "评价方式"]
            widths = [1.4, 3.6, 3.2, 3.6]
            x_positions = [0.72]
            for width in widths[:-1]:
                x_positions.append(x_positions[-1] + width)
            for col, header in enumerate(headers):
                _shape(slide, x_positions[col], 1.58, widths[col], 0.55, palette["primary"], radius=False)
                _textbox(slide, header, x_positions[col] + 0.08, 1.73, widths[col] - 0.16, 0.23, size=10, color="FFFFFF", bold=True, align=PP_ALIGN.CENTER)
            row_h = min(0.72, 4.35 / max(len(rows), 1))
            for row_index, row in enumerate(rows):
                values = [row.get(key, "") for key in ("objective_id", "case_section", "activity", "assessment")]
                y = 2.13 + row_index * row_h
                for col, value in enumerate(values):
                    fill = "FFFFFF" if row_index % 2 == 0 else palette["background"]
                    _shape(slide, x_positions[col], y, widths[col], row_h, fill, radius=False, line="D9E2E7")
                    _textbox(slide, _clean_text(value), x_positions[col] + 0.08, y + 0.05, widths[col] - 0.16, row_h - 0.1, size=10, color=palette["text"], valign=MSO_ANCHOR.MIDDLE)
        elif kind == "closing":
            _shape(slide, 0.72, 1.8, 11.82, 3.7, palette["primary"], radius=True)
            _textbox(slide, spec.get("content", ""), 1.2, 2.34, 10.85, 1.55, size=27, color="FFFFFF", bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
            _textbox(slide, "EVIDENCE · TRADE-OFF · ACTION", 2.1, 4.35, 9.0, 0.35, size=11, color="DCE7EC", bold=True, align=PP_ALIGN.CENTER)

    clean_title = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", outline["title"]).strip(" ._")[:80] or title
    filename = f"{clean_title}_教学案例课件_V{version}.pptx"
    export_dir = Path(settings.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / filename
    prs.save(str(path))
    return str(path)
