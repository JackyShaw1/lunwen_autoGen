"""Word / PDF 导出服务"""

import uuid
from pathlib import Path

from docx import Document
from docx.shared import Pt

from app.config import settings


def _ensure_export_dir() -> Path:
    p = Path(settings.export_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def export_docx(package: dict, title: str) -> str:
    export_dir = _ensure_export_dir()
    file_id = str(uuid.uuid4())
    path = export_dir / f"{file_id}.docx"

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "宋体"
    style.font.size = Pt(12)

    meta = package.get("meta", {})
    doc.add_heading(meta.get("title", title), level=0)
    doc.add_paragraph(
        f"学科：{meta.get('subject', '')} | 课程：{meta.get('course', '')} | "
        f"难度：{meta.get('difficulty', '')}"
    )
    if meta.get("fictional_disclaimer"):
        doc.add_paragraph(meta["fictional_disclaimer"])

    doc.add_heading("学习目标", level=1)
    for lo in package.get("learning_objectives", []):
        doc.add_paragraph(f"• {lo.get('description', '')}", style="List Bullet")

    body = package.get("body", {})
    doc.add_heading("案例背景", level=1)
    doc.add_paragraph(body.get("background", ""))
    doc.add_heading("案例叙事", level=1)
    doc.add_paragraph(body.get("narrative", ""))
    doc.add_heading("决策点", level=1)
    doc.add_paragraph(body.get("decision_point", ""))

    doc.add_heading("讨论题", level=1)
    for q in package.get("discussion_questions", []):
        doc.add_paragraph(f"[{q.get('level', '')}] {q.get('question', '')}")

    guide = package.get("instructor_guide", {})
    doc.add_heading("教师指南", level=1)
    doc.add_paragraph(guide.get("teaching_flow", ""))
    for kp in guide.get("key_points", []):
        doc.add_paragraph(f"• {kp}", style="List Bullet")

    doc.save(str(path))
    return str(path)


def export_pdf(package: dict, title: str) -> str:
    export_dir = _ensure_export_dir()
    docx_path = Path(export_docx(package, title))
    pdf_path = export_dir / f"{docx_path.stem}.pdf"

    try:
        from docx2pdf import convert

        convert(str(docx_path), str(pdf_path))
        return str(pdf_path)
    except Exception:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        meta = package.get("meta", {})
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4
        y = height - 50
        c.setFont("Helvetica", 14)
        c.drawString(50, y, meta.get("title", title)[:80])
        y -= 30
        c.setFont("Helvetica", 10)
        body = package.get("body", {})
        text = (body.get("background", "") + "\n" + body.get("narrative", "")).split("\n")
        for line in text:
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
            c.drawString(50, y, line[:90])
            y -= 14
        c.save()
        return str(pdf_path)
