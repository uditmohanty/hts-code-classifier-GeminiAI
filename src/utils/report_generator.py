from __future__ import annotations

import io
import os
import json
import unicodedata
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


class ReportGenerator:
    """
    Generates JSON and PDF reports. Unicode-safe:
    - Tries to register a Unicode font (DejaVu / Noto) from ./assets/fonts
    - If no TTF is found, falls back to Helvetica and sanitizes text to Latin-1
    """

    def __init__(self) -> None:
        self.font_name = "Helvetica"
        self.bold_name = "Helvetica-Bold"
        self._setup_font()

    def _setup_font(self) -> None:
        base_dir = os.path.dirname(__file__)
        candidates = [
            ("DejaVuSans", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
            ("NotoSans", "NotoSans-Regular.ttf", "NotoSans-Bold.ttf"),
        ]
        for family, regular, bold in candidates:
            for root in ("assets/fonts", "fonts", "."):
                reg_path = os.path.join(base_dir, root, regular)
                bold_path = os.path.join(base_dir, root, bold)
                if os.path.exists(reg_path) and os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(family, reg_path))
                    pdfmetrics.registerFont(TTFont(family + "-Bold", bold_path))
                    self.font_name = family
                    self.bold_name = family + "-Bold"
                    return

    def _safe(self, text: object) -> str:
        if text is None:
            return ""
        s = str(text)
        if self.font_name != "Helvetica":
            return s
        s = unicodedata.normalize("NFKD", s)
        try:
            return s.encode("latin-1", "ignore").decode("latin-1")
        except Exception:
            return s.encode("ascii", "ignore").decode("ascii")

    def generate_json_report(self, result: dict, product_info: dict) -> str:
        data = {
            "generated_at": datetime.now().isoformat(),
            "product": product_info,
            "classification": result,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def generate_pdf_report(self, result: dict, product_info: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            title="HS Code Classification Report",
            author="HS Code Classifier",
            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        styles["Normal"].fontName = self.font_name
        styles["Heading1"].fontName = self.bold_name
        styles["Heading2"].fontName = self.bold_name
        styles["Heading1"].fontSize = 16
        styles["Heading2"].fontSize = 13
        styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9, leading=12))

        story = []
        story += [
            Paragraph(self._safe("HS Code Classification Report"), styles["Heading1"]),
            Spacer(1, 6),
            Paragraph(self._safe(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), styles["Small"]),
            Spacer(1, 12),
        ]

        story += [Paragraph(self._safe("Product Information"), styles["Heading2"]), Spacer(1, 6)]
        info_rows = [
            ["Product Name", self._safe(product_info.get("product_name", ""))],
            ["Description", self._safe(product_info.get("description", ""))],
            ["Material/Composition", self._safe(product_info.get("material", ""))],
            ["Intended Use", self._safe(product_info.get("use", ""))],
            ["Country of Origin", self._safe(product_info.get("origin", ""))],
        ]
        t_info = Table(info_rows, colWidths=[140, 360], hAlign="LEFT")
        t_info.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ]))
        story += [t_info, Spacer(1, 12)]

        story += [Paragraph(self._safe("Classification Result"), styles["Heading2"]), Spacer(1, 6)]
        class_rows = [
            ["Recommended HS Code", self._safe(result.get("recommended_code", "N/A"))],
            ["Duty Rate", self._safe(result.get("duty_rate", "N/A"))],
            ["Confidence", self._safe(str(result.get("confidence", "0%")))],
        ]
        t_cls = Table(class_rows, colWidths=[180, 320], hAlign="LEFT")
        t_cls.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), self.font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ]))
        story += [t_cls, Spacer(1, 10)]

        story += [Paragraph(self._safe("Reasoning"), styles["Heading2"]), Spacer(1, 6)]
        story += [Paragraph(self._safe(result.get("reasoning", "No reasoning provided")), styles["Normal"]), Spacer(1, 10)]

        alts = result.get("alternatives") or []
        if alts:
            story += [Paragraph(self._safe("Alternative HS Codes"), styles["Heading2"]), Spacer(1, 6)]
            t_alt = Table([[self._safe(a)] for a in alts], colWidths=[500], hAlign="LEFT")
            t_alt.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]))
            story += [t_alt, Spacer(1, 10)]

        cands = result.get("hts_candidates") or []
        if cands:
            story += [Paragraph(self._safe("HTS Database Matches"), styles["Heading2"]), Spacer(1, 6)]
            rows = [["HS Code", "Description", "Duty", "Relevance"]]
            for c in cands:
                rel = c.get("relevance_score", "")
                if isinstance(rel, (int, float)):
                    rel = f"{rel:.2f}"
                rows.append([
                    self._safe(c.get("hs_code", "")),
                    self._safe(c.get("description", "")),
                    self._safe(c.get("duty_rate", "")),
                    self._safe(rel),
                ])
            t_c = Table(rows, colWidths=[90, 300, 60, 60], repeatRows=1, hAlign="LEFT")
            t_c.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), self.font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story += [t_c]

        doc.build(story)
        pdf = buf.getvalue()
        buf.close()
        return pdf
