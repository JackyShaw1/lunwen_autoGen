"""Word / PDF 导出服务（完整教学案例四件套，PDF 支持中文）"""

from __future__ import annotations

import uuid
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

from app.config import settings

# Windows 常见中文字体（优先 TTF，TTC 作后备）
_CN_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\Deng.ttf"),
    Path(r"C:\Windows\Fonts\simkai.ttf"),
]


def _ensure_export_dir() -> Path:
    p = Path(settings.export_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _set_run_east_asia_font(run, font_name: str = "宋体") -> None:
    run.font.name = font_name
    r = run._element
    r.rPr.rFonts.set(qn("w:eastAsia"), font_name)


def export_docx(package: dict, title: str) -> str:
    export_dir = _ensure_export_dir()
    file_id = str(uuid.uuid4())
    path = export_dir / f"{file_id}.docx"

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(12)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    meta = package.get("meta", {})
    h = doc.add_heading(meta.get("title", title), level=0)
    for run in h.runs:
        _set_run_east_asia_font(run, "黑体")

    p = doc.add_paragraph(
        f"学科：{meta.get('subject', '')} | 课程：{meta.get('course', '')} | "
        f"类型：{meta.get('case_type', '')} | 难度：{meta.get('difficulty', '')}"
    )
    for run in p.runs:
        _set_run_east_asia_font(run)

    if meta.get("fictional_disclaimer"):
        tip = doc.add_paragraph(f"⚠️ {meta['fictional_disclaimer']}")
        for run in tip.runs:
            _set_run_east_asia_font(run)

    doc.add_heading("一、学习目标", level=1)
    for lo in package.get("learning_objectives", []):
        doc.add_paragraph(
            f"{lo.get('id', '')} [{lo.get('level', '')}] {lo.get('description', '')}",
            style="List Bullet",
        )

    body = package.get("body", {})
    doc.add_heading("二、案例背景", level=1)
    doc.add_paragraph(body.get("background", "") or "（无）")
    doc.add_heading("三、案例叙事", level=1)
    doc.add_paragraph(body.get("narrative", "") or "（无）")
    doc.add_heading("四、决策点", level=1)
    doc.add_paragraph(body.get("decision_point", "") or "（无）")

    chars = body.get("characters") or []
    if chars:
        doc.add_heading("五、角色立场", level=1)
        for c in chars:
            doc.add_paragraph(
                f"{c.get('name', '')}（{c.get('role', '')}）：{c.get('stance', '')}",
                style="List Bullet",
            )

    doc.add_heading("六、讨论题", level=1)
    for i, q in enumerate(package.get("discussion_questions", []), 1):
        doc.add_paragraph(f"{i}. [{q.get('level', '')}] {q.get('question', '')}")
        if q.get("teaching_intent"):
            doc.add_paragraph(f"   教学意图：{q['teaching_intent']}")

    guide = package.get("instructor_guide", {}) or {}
    doc.add_heading("七、教师指南", level=1)
    doc.add_paragraph(f"授课流程：{guide.get('teaching_flow', '') or '（无）'}")
    if guide.get("key_points"):
        doc.add_paragraph("要点：")
        for kp in guide["key_points"]:
            doc.add_paragraph(f"• {kp}", style="List Bullet")
    if guide.get("common_misconceptions"):
        doc.add_paragraph("常见误区：")
        for m in guide["common_misconceptions"]:
            doc.add_paragraph(f"• {m}", style="List Bullet")

    matrix = package.get("alignment_matrix") or []
    if matrix:
        doc.add_heading("八、教学目标对齐表", level=1)
        table = doc.add_table(rows=1, cols=4)
        hdr = table.rows[0].cells
        hdr[0].text = "目标"
        hdr[1].text = "案例环节"
        hdr[2].text = "活动"
        hdr[3].text = "评价"
        for row in matrix:
            cells = table.add_row().cells
            cells[0].text = str(row.get("objective_id", ""))
            cells[1].text = str(row.get("case_section", ""))
            cells[2].text = str(row.get("activity", ""))
            cells[3].text = str(row.get("assessment", ""))

    quality = package.get("quality") or {}
    if quality:
        doc.add_heading("九、质量评审", level=1)
        doc.add_paragraph(f"综合分：{quality.get('overall_score', '—')}")
        doc.add_paragraph(f"评审摘要：{quality.get('reviewer_summary', '')}")
        scores = quality.get("rubric_scores") or {}
        if scores:
            doc.add_paragraph("五维评分：" + "；".join(f"{k}={v}" for k, v in scores.items()))

    doc.save(str(path))
    return str(path)


def _resolve_cn_font() -> Path | None:
    for p in _CN_FONT_CANDIDATES:
        if p.exists():
            return p
    return None


def _register_cn_font() -> str:
    """注册中文字体，返回 reportlab 字体名。"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = _resolve_cn_font()
    if not font_path:
        raise RuntimeError("未找到可用中文字体（请安装 黑体/微软雅黑/宋体）")

    font_name = "CaseAutoGenCN"
    # 已注册则复用
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name

    # TTC 需指定 subfontIndex
    if font_path.suffix.lower() == ".ttc":
        pdfmetrics.registerFont(TTFont(font_name, str(font_path), subfontIndex=0))
    else:
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    return font_name


def _pdf_escape(text: str) -> str:
    """ReportLab Paragraph 需要转义 XML 特殊字符。"""
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def export_pdf(package: dict, title: str) -> str:
    """使用 reportlab + 中文字体导出完整 PDF（不依赖 Word）。"""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        KeepTogether,
    )

    export_dir = _ensure_export_dir()
    file_id = str(uuid.uuid4())
    pdf_path = export_dir / f"{file_id}.pdf"

    font_name = _register_cn_font()
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CNTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=26,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "CNH1",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=14,
        leading=22,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#0f766e"),
    )
    body_style = ParagraphStyle(
        "CNBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=11,
        leading=18,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    tip_style = ParagraphStyle(
        "CNTip",
        parent=body_style,
        fontSize=9,
        textColor=colors.HexColor("#6b7280"),
        leading=14,
    )
    meta_style = ParagraphStyle(
        "CNMeta",
        parent=body_style,
        fontSize=10,
        textColor=colors.HexColor("#374151"),
        alignment=TA_CENTER,
    )

    meta = package.get("meta", {}) or {}
    body = package.get("body", {}) or {}
    guide = package.get("instructor_guide", {}) or {}
    quality = package.get("quality", {}) or {}

    story: list = []
    story.append(Paragraph(_pdf_escape(meta.get("title", title) or title), title_style))
    story.append(
        Paragraph(
            _pdf_escape(
                f"学科：{meta.get('subject', '')}　课程：{meta.get('course', '')}　"
                f"类型：{meta.get('case_type', '')}　难度：{meta.get('difficulty', '')}"
            ),
            meta_style,
        )
    )
    if meta.get("fictional_disclaimer"):
        story.append(Paragraph(_pdf_escape(f"※ {meta['fictional_disclaimer']}"), tip_style))
    story.append(Spacer(1, 0.4 * cm))

    # 学习目标
    story.append(Paragraph("一、学习目标", h1_style))
    objectives = package.get("learning_objectives") or []
    if not objectives:
        story.append(Paragraph("（无）", body_style))
    for lo in objectives:
        story.append(
            Paragraph(
                _pdf_escape(
                    f"• {lo.get('id', '')} [{lo.get('level', '')}] {lo.get('description', '')}"
                ),
                body_style,
            )
        )

    # 背景 / 叙事 / 决策点
    story.append(Paragraph("二、案例背景", h1_style))
    story.append(Paragraph(_pdf_escape(body.get("background", "") or "（无）").replace("\n", "<br/>"), body_style))

    story.append(Paragraph("三、案例叙事", h1_style))
    story.append(Paragraph(_pdf_escape(body.get("narrative", "") or "（无）").replace("\n", "<br/>"), body_style))

    story.append(Paragraph("四、决策点", h1_style))
    story.append(Paragraph(_pdf_escape(body.get("decision_point", "") or "（无）"), body_style))

    chars = body.get("characters") or []
    if chars:
        story.append(Paragraph("五、角色立场", h1_style))
        for c in chars:
            story.append(
                Paragraph(
                    _pdf_escape(
                        f"• {c.get('name', '')}（{c.get('role', '')}）：{c.get('stance', '')}"
                    ),
                    body_style,
                )
            )

    # 讨论题
    story.append(Paragraph("六、讨论题", h1_style))
    questions = package.get("discussion_questions") or []
    if not questions:
        story.append(Paragraph("（无）", body_style))
    for i, q in enumerate(questions, 1):
        story.append(
            Paragraph(
                _pdf_escape(f"{i}. [{q.get('level', '')}] {q.get('question', '')}"),
                body_style,
            )
        )
        if q.get("teaching_intent"):
            story.append(
                Paragraph(_pdf_escape(f"　教学意图：{q['teaching_intent']}"), tip_style)
            )

    # 教师指南
    story.append(Paragraph("七、教师指南", h1_style))
    story.append(
        Paragraph(
            _pdf_escape(f"授课流程：{guide.get('teaching_flow', '') or '（无）'}"),
            body_style,
        )
    )
    for kp in guide.get("key_points") or []:
        story.append(Paragraph(_pdf_escape(f"• 要点：{kp}"), body_style))
    for m in guide.get("common_misconceptions") or []:
        story.append(Paragraph(_pdf_escape(f"• 误区：{m}"), body_style))

    # 对齐表
    matrix = package.get("alignment_matrix") or []
    if matrix:
        story.append(Paragraph("八、教学目标对齐表", h1_style))
        data = [["目标", "案例环节", "活动", "评价"]]
        for row in matrix:
            data.append(
                [
                    Paragraph(_pdf_escape(str(row.get("objective_id", ""))), tip_style),
                    Paragraph(_pdf_escape(str(row.get("case_section", ""))), tip_style),
                    Paragraph(_pdf_escape(str(row.get("activity", ""))), tip_style),
                    Paragraph(_pdf_escape(str(row.get("assessment", ""))), tip_style),
                ]
            )
        table = Table(data, colWidths=[2.2 * cm, 5 * cm, 4 * cm, 4 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0fdfa")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(KeepTogether([table]))

    if quality:
        story.append(Paragraph("九、质量评审", h1_style))
        story.append(
            Paragraph(
                _pdf_escape(f"综合分：{quality.get('overall_score', '—')}"),
                body_style,
            )
        )
        story.append(
            Paragraph(
                _pdf_escape(f"评审摘要：{quality.get('reviewer_summary', '') or '（无）'}"),
                body_style,
            )
        )
        scores = quality.get("rubric_scores") or {}
        if scores:
            story.append(
                Paragraph(
                    _pdf_escape("五维评分：" + "；".join(f"{k}={v}" for k, v in scores.items())),
                    body_style,
                )
            )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=meta.get("title", title),
        author="CaseAutoGenSystem",
    )
    doc.build(story)
    return str(pdf_path)
