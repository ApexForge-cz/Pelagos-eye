"""Build the maintainable OceanScope V2.1 project-plan PDF from Markdown.

The application has no runtime dependency on ReportLab. Install ReportLab in an
isolated documentation environment before running this script.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    LongTable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "OceanScope_Project_Plan_v2.1.md"
DEFAULT_OUTPUT = ROOT / "output" / "pdf" / "OceanScope_Project_Plan_v2.1.pdf"
ROOT_PDF = ROOT / "OceanScope_项目规划与开发路线图.pdf"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 17 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm

NAVY = colors.HexColor("#111111")
DEEP = colors.white
INK = colors.HexColor("#222222")
MUTED = colors.HexColor("#666666")
CYAN = colors.HexColor("#222222")
CYAN_LIGHT = colors.HexColor("#F7F7F7")
BLUE = colors.HexColor("#111111")
GREEN = colors.HexColor("#222222")
AMBER = colors.HexColor("#222222")
RED = colors.HexColor("#222222")
VIOLET = colors.HexColor("#333333")
PAPER = colors.white
GRID = colors.HexColor("#B8B8B8")


LOCALIZATION = {
    "Executive Summary": "执行摘要",
    "Project Background": "项目背景",
    "Positioning / Scope / Boundaries": "定位、范围与边界",
    "Product & Feature Architecture": "产品与功能架构",
    "System Architecture": "系统架构",
    "Data Architecture": "数据架构",
    "Real Data Sources": "真实数据源",
    "UI / UX & 3D Spatial Design": "界面、交互与三维空间设计",
    "Two-Developer Collaboration": "双人协作",
    "Current Repository & Development State": "当前仓库与开发状态",
    "Phase 0 Retrospective": "Phase 0 回顾",
    "Phase 1 Hardening": "Phase 1 工程加固",
    "Phase 2 Complete & Follow-up": "Phase 2 完成与后续工作",
    "Phase 3 Digital Earth": "Phase 3 数字地球",
    "Phase 4 Live AIS": "Phase 4 实时 AIS",
    "Phase 5 Historical Intelligence": "Phase 5 历史智能分析",
    "Phase 6 Risk & Anomaly": "Phase 6 风险与异常",
    "Phase 7 Advanced Visualization": "Phase 7 高级可视化",
    "Phase 8 Intelligence": "Phase 8 证据智能",
    "Phase 9 Quality & Security": "Phase 9 质量与安全",
    "Phase 10 Release": "Phase 10 发布",
    "Feature Coverage Matrix": "功能覆盖矩阵",
    "Data Coverage Matrix": "数据覆盖矩阵",
    "Innovation Roadmap": "创新路线图",
    "Testing Strategy": "测试策略",
    "Security": "安全",
    "GitHub / Codex Workflow": "GitHub / Codex 工作流",
    "Risk Register": "风险登记",
    "Decision Log": "决策日志",
    "Appendix A. Design Tokens": "附录 A：设计 Token",
    "Appendix B. Status Vocabulary": "附录 B：状态词汇",
    "Appendix C. Audit Evidence and Open Confirmations": "附录 C：审计证据与待确认事项",
    "Appendix D. Official Source References": "附录 D：官方来源",
    "Design position": "设计定位",
    "Definition of Real Feature": "真实功能定义",
    "Primary workspaces": "主要工作区",
    "Architecture V2": "架构 V2",
    "Spatial and temporal rules": "时空规则",
    "Gate evidence and follow-up": "门禁证据与后续工作",
    "Current Phase 2 ownership": "当前 Phase 2 所有权",
    "URL Workspace State and Scene Presets": "URL 工作区状态与场景预设",
    "Quality layers": "质量层",
    "Completion commands": "完成检查命令",
    "Branch and PR rules": "分支与 PR 规则",
    "Codex start protocol": "Codex 开始协议",
    "Small PR contract": "小型 PR 约定",
    "Evidence inspected": "已检查证据",
    "Human confirmations still required": "仍需人工确认",
    "Next recommendation": "下一步建议",
    "Dataset": "数据集",
    "Current status": "当前状态",
    "Implemented evidence": "已实现证据",
    "Remaining boundary": "剩余边界",
    "Current evidence": "当前证据",
    "Assessment": "评估",
    "Area": "领域",
    "Review item": "审查项目",
    "Result": "结果",
    "Objective:": "目标：",
    "Must:": "必须：",
    "Should:": "应当：",
    "Constraints:": "约束：",
    "**Objective**": "**目标**",
    "**Must**": "**必须**",
    "**Should**": "**应当**",
    "**Constraints**": "**约束**",
    "**Must rules**": "**必须规则**",
    "Allowed language:": "允许用语：",
    "Must rules:": "必须规则：",
    "Layer": "层",
    "Purpose": "用途",
    "Capability": "能力",
    "Current state": "当前状态",
    "Hardening action": "加固动作",
    "Data licensing": "数据授权",
    "Maritime terminology": "海事术语",
    "Historical AIS coverage": "历史 AIS 覆盖",
    "Real-time AIS plan": "实时 AIS 计划",
    "Risk wording": "风险措辞",
    "AI boundary": "AI 边界",
    "GitHub positioning": "GitHub 定位",
    "Two-developer collaboration": "双人协作",
    "UI baseline": "UI 基线",
    "Feature/data coverage": "功能/数据覆盖",
    "Feature": "功能",
    "User value": "用户价值",
    "Real source": "真实来源",
    "Backend": "后端",
    "Frontend": "前端",
    "Owner": "负责人",
    "Test": "测试",
    "Provider": "提供方",
    "Geographic coverage": "地理覆盖",
    "Temporal coverage": "时间覆盖",
    "Mode": "类型",
    "Update": "更新",
    "License / terms": "授权 / 条款",
    "Cache": "缓存",
    "Used by": "使用模块",
    "Limitations": "局限",
    "Risk": "风险",
    "Likelihood / Impact": "可能性 / 影响",
    "Control": "控制措施",
    "Owner / Gate": "负责人 / 门禁",
    "Decision": "决策",
    "Status / rationale": "状态 / 理由",
    "Value": "值",
    "Meaning": "含义",
    "State": "状态",
    "Status": "状态",
    "User meaning": "用户含义",
    "Required UI evidence": "必需 UI 证据",
    "Visual depth": "视觉层次",
    "Command Center layout": "指挥中心布局",
    "Scene Director and motion": "场景导演与动效",
    "Performance modes": "性能模式",
    "Roles and workload": "角色与工作量",
    "Existing Ownership Wins": "已有所有权优先",
    "Contract-first parallel workflow": "契约优先的并行工作流",
    "Dual-developer workflow": "双人开发工作流",
    "Audit snapshot": "审计快照",
    "Current System State": "当前系统状态",
    "API inventory": "API 清单",
    "Implemented": "已实现",
    "Partially Implemented": "部分实现",
    "Backend Ready": "后端就绪",
    "Prototype": "原型",
    "Planned": "计划中",
    "Research": "研究",
    "Development Only": "仅开发使用",
    "Current source assessment": "当前数据源评估",
    "Source-specific rules": "数据源规则",
    "Real Data Pipeline": "真实数据管线",
    "Provenance contract": "来源追踪契约",
    "Status and failure semantics": "状态与失败语义",
    "Data Confidence Layer": "数据置信度层",
    "Source Lens": "来源透镜",
    "Event Timeline": "事件时间线",
    "Data Sources": "数据源",
    "System Health": "系统健康",
    "Data Explorer": "数据探索器",
    "Region Workspace": "区域工作区",
    "Compare Mode": "对比模式",
    "Corridor Intelligence": "航道/通道分析",
    "Environmental Context": "环境上下文",
    "Evidence-first Intelligence": "证据优先智能",
    "Real data before impressive numbers.": "真实数据优先于漂亮数字。",
    "Correctness before visual decoration.": "正确性优先于视觉装饰。",
    "Map interaction should drive analysis.": "地图交互应驱动分析。",
    "Every important number must be traceable.": "每个重要数字都必须可追溯。",
    "No data is not zero; no coverage is not no vessel.": "没有数据不等于零；没有覆盖不等于没有船。",
    "Model data is not observation; derived metrics are not official facts.": "模型数据不是现场观测；派生指标不是官方事实。",
    "AI explains evidence; AI does not invent evidence.": "AI 解释证据；AI 不创造证据。",
    "Phase 0-2 Complete · Phase 3 Awaiting Approval": "Phase 0-2 已完成 · Phase 3 待批准",
    "Non-commercial · Learning & Research · Not for navigation": "非商业 · 学习与研究 · 不用于航行",
    "Non-commercial / Learning & Research / GitHub Portfolio / Software Engineering Project": "非商业 / 学习与研究 / GitHub 作品集 / 软件工程项目",
    "FIGURE": "图",
}


def register_fonts() -> None:
    regular = Path(r"C:\Windows\Fonts\simsun.ttc")
    bold = Path(r"C:\Windows\Fonts\simhei.ttf")
    if not regular.exists() or not bold.exists():
        raise FileNotFoundError(
            "SimSun and SimHei fonts are required to build the Chinese PDF"
        )
    pdfmetrics.registerFont(TTFont("OceanScopeSerif", str(regular), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("OceanScopeHeading", str(bold)))
    pdfmetrics.registerFontFamily(
        "OceanScopeSerif",
        normal="OceanScopeSerif",
        bold="OceanScopeHeading",
        italic="OceanScopeSerif",
        boldItalic="OceanScopeHeading",
    )


def localize_text(value: str) -> str:
    localized = value
    for source, target in sorted(
        LOCALIZATION.items(), key=lambda item: len(item[0]), reverse=True
    ):
        localized = localized.replace(source, target)
    return localized


def inline_markup(value: str) -> str:
    code_spans: list[str] = []

    def protect_code(match: re.Match[str]) -> str:
        code_spans.append(match.group(1))
        return f"@@OCEANSCOPE_CODE_{len(code_spans) - 1}@@"

    protected = re.sub(r"`([^`]+)`", protect_code, value.strip())
    escaped = html.escape(localize_text(protected))
    escaped = escaped.replace("&lt;br&gt;", "<br/>").replace("&lt;br/&gt;", "<br/>")
    escaped = re.sub(
        r"\[([^]]+)]\((https?://[^)]+)\)",
        r'<link href="\2" color="#245EEB">\1</link>',
        escaped,
    )
    for index, code in enumerate(code_spans):
        escaped = escaped.replace(
            f"@@OCEANSCOPE_CODE_{index}@@",
            f'<font name="OceanScopeSerif" color="#344054">{html.escape(code)}</font>',
        )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return escaped


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="OceanScopeSerif",
            fontSize=10.2,
            leading=17.2,
            textColor=INK,
            spaceAfter=5.5,
            wordWrap="CJK",
        ),
        "Lead": ParagraphStyle(
            "Lead",
            parent=base["BodyText"],
            fontName="OceanScopeSerif",
            fontSize=10.5,
            leading=18,
            textColor=NAVY,
            borderColor=CYAN,
            borderWidth=0,
            borderPadding=(3, 8, 3, 10),
            leftIndent=6,
            spaceAfter=8,
            wordWrap="CJK",
        ),
        "Heading1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="OceanScopeHeading",
            fontSize=17,
            leading=24,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=9,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "Heading2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="OceanScopeHeading",
            fontSize=13,
            leading=19,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "Heading3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName="OceanScopeHeading",
            fontSize=11,
            leading=16,
            textColor=VIOLET,
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
            wordWrap="CJK",
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="OceanScopeSerif",
            fontSize=9.8,
            leading=16,
            textColor=INK,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=2,
            spaceAfter=2.5,
            wordWrap="CJK",
        ),
        "Numbered": ParagraphStyle(
            "Numbered",
            parent=base["BodyText"],
            fontName="OceanScopeSerif",
            fontSize=9.8,
            leading=16,
            textColor=INK,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=2.5,
            wordWrap="CJK",
        ),
        "Quote": ParagraphStyle(
            "Quote",
            parent=base["BodyText"],
            fontName="OceanScopeSerif",
            fontSize=10.2,
            leading=17.2,
            textColor=NAVY,
            backColor=CYAN_LIGHT,
            borderColor=CYAN,
            borderWidth=0.8,
            borderPadding=8,
            leftIndent=7,
            rightIndent=7,
            spaceBefore=3,
            spaceAfter=9,
            wordWrap="CJK",
        ),
        "Table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName="OceanScopeSerif",
            fontSize=8.1,
            leading=12,
            textColor=INK,
            wordWrap="CJK",
        ),
        "TableHead": ParagraphStyle(
            "TableHead",
            parent=base["BodyText"],
            fontName="OceanScopeHeading",
            fontSize=8.1,
            leading=12,
            textColor=INK,
            wordWrap="CJK",
        ),
        "DiagramCaption": ParagraphStyle(
            "DiagramCaption",
            parent=base["BodyText"],
            fontName="OceanScopeHeading",
            fontSize=8.2,
            leading=11,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "Footer": ParagraphStyle(
            "Footer",
            fontName="OceanScopeSerif",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "TOCHeading": ParagraphStyle(
            "TOCHeading",
            fontName="OceanScopeHeading",
            fontSize=11,
            leading=17,
            leftIndent=12,
            firstLineIndent=-12,
            textColor=NAVY,
            spaceBefore=2,
        ),
        "TOCSub": ParagraphStyle(
            "TOCSub",
            fontName="OceanScopeSerif",
            fontSize=9,
            leading=14,
            leftIndent=24,
            firstLineIndent=-12,
            textColor=MUTED,
            spaceBefore=1,
        ),
    }


class ProjectPlanDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, styles: dict[str, ParagraphStyle]) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="OceanScope Project Plan, Collaboration and Development Roadmap Version 2.1",
            author="OceanScope",
            subject="Global Maritime Situational Awareness & Analytics Platform",
        )
        self.styles = styles
        body_frame = Frame(
            MARGIN_X,
            MARGIN_BOTTOM,
            PAGE_WIDTH - 2 * MARGIN_X,
            PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=6,
            bottomPadding=0,
        )
        cover_frame = Frame(0, 0, PAGE_WIDTH, PAGE_HEIGHT, id="cover", showBoundary=0)
        self.addPageTemplates(
            [
                PageTemplate(id="Cover", frames=[cover_frame], onPage=self._cover_page),
                PageTemplate(id="Body", frames=[body_frame], onPage=self._body_page),
            ]
        )

    def afterFlowable(self, flowable: object) -> None:
        if not isinstance(flowable, Paragraph):
            return
        style_name = flowable.style.name
        if style_name != "Heading1":
            return
        level = 0
        text = flowable.getPlainText()
        if text == "目录":
            return
        key = f"heading-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=False)
        self.notify("TOCEntry", (level, text, self.page, key))

    def _cover_page(self, canvas: object, doc: object) -> None:
        canvas.saveState()
        canvas.restoreState()

    def _body_page(self, canvas: object, doc: object) -> None:
        canvas.saveState()
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
        canvas.setFont("OceanScopeSerif", 8)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(PAGE_WIDTH / 2, 8 * mm, str(doc.page))
        canvas.restoreState()


def cover_story(styles: dict[str, ParagraphStyle]) -> list[object]:
    title = ParagraphStyle(
        "CoverTitle",
        fontName="Times-Bold",
        fontSize=28,
        leading=34,
        textColor=INK,
        alignment=TA_CENTER,
    )
    chinese = ParagraphStyle(
        "CoverChinese",
        fontName="OceanScopeHeading",
        fontSize=17,
        leading=25,
        textColor=INK,
        alignment=TA_CENTER,
    )
    subtitle = ParagraphStyle(
        "CoverSubtitle",
        fontName="OceanScopeSerif",
        fontSize=12,
        leading=20,
        textColor=INK,
        alignment=TA_CENTER,
    )
    meta = ParagraphStyle(
        "CoverMeta",
        fontName="OceanScopeSerif",
        fontSize=10,
        leading=17,
        textColor=INK,
    )
    disclaimer = ParagraphStyle(
        "CoverDisclaimer",
        fontName="OceanScopeSerif",
        fontSize=9.2,
        leading=16,
        textColor=INK,
        alignment=TA_CENTER,
    )
    label = ParagraphStyle("CoverLabel", parent=meta, fontName="OceanScopeHeading")
    metadata = Table(
        [
            [Paragraph("版本", label), Paragraph("2.1 / 项目规划与开发路线图", meta)],
            [
                Paragraph("开发方式", label),
                Paragraph("双人协作开发 / Codex 辅助软件工程", meta),
            ],
            [
                Paragraph("用途", label),
                Paragraph("非商业、学习研究、GitHub 作品集、软件工程项目", meta),
            ],
            [Paragraph("日期", label), Paragraph("2026 年 9 月 18 日", meta)],
            [
                Paragraph("当前阶段", label),
                Paragraph("Phase 0-2 已完成；Phase 3 待项目负责人批准", meta),
            ],
        ],
        colWidths=[30 * mm, 105 * mm],
        hAlign="CENTER",
    )
    metadata.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 0.7, INK),
                ("LINEBELOW", (0, -1), (-1, -1), 0.7, INK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [
        Spacer(1, 33 * mm),
        Paragraph("OCEANSCOPE", title),
        Spacer(1, 5 * mm),
        Paragraph("全球港航态势感知与智能分析平台", chinese),
        Spacer(1, 12 * mm),
        Paragraph("项目规划、双人协作与开发路线图", subtitle),
        Spacer(1, 17 * mm),
        metadata,
        Spacer(1, 15 * mm),
        Paragraph(
            "本文档以当前仓库代码、测试和验证记录为依据。规划内容不代表系统可以替代真实航海系统、碰撞规避系统、应急调度系统、政府监管系统或执法系统。",
            disclaimer,
        ),
        NextPageTemplate("Body"),
        PageBreak(),
    ]


def table_widths(rows: list[list[str]], available: float) -> list[float]:
    columns = len(rows[0])
    lengths: list[float] = []
    for index in range(columns):
        values = [row[index] if index < len(row) else "" for row in rows]
        longest = max(len(re.sub(r"[*`]", "", value)) for value in values)
        average = sum(min(len(value), 36) for value in values) / max(len(values), 1)
        lengths.append(max(5.0, min(longest, 40) * 0.65 + average * 0.35))
    minimum = 31 if columns >= 8 else 40 if columns >= 6 else 55
    raw = [max(minimum, value * 4.0) for value in lengths]
    scale = available / sum(raw)
    return [value * scale for value in raw]


def build_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> LongTable:
    width = PAGE_WIDTH - 2 * MARGIN_X
    columns = len(rows[0])
    body_style = styles["Table"]
    head_style = styles["TableHead"]
    if columns >= 8:
        body_style = ParagraphStyle(
            "DenseTable",
            parent=styles["Table"],
            fontSize=7.5,
            leading=10.6,
        )
        head_style = ParagraphStyle(
            "DenseTableHead",
            parent=styles["TableHead"],
            fontSize=7.5,
            leading=10.6,
        )
    formatted: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        style = head_style if row_index == 0 else body_style
        formatted.append([Paragraph(inline_markup(cell), style) for cell in row])
    column_widths = table_widths(rows, width)
    if columns == 9:
        weights = [52, 58, 56, 46, 46, 32, 60, 47, 84]
        column_widths = [width * weight / sum(weights) for weight in weights]
    elif columns == 10:
        weights = [44, 52, 58, 56, 38, 38, 58, 34, 36, 67]
        column_widths = [width * weight / sum(weights) for weight in weights]
    table = LongTable(
        formatted,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEABOVE", (0, 0), (-1, 0), 0.65, INK),
                ("LINEBELOW", (0, 0), (-1, 0), 0.45, INK),
                ("LINEBELOW", (0, -1), (-1, -1), 0.65, INK),
                ("INNERHORIZONTAL", (0, 0), (-1, -1), 0.25, GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_diagram(lines: list[str], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    cleaned = "\n".join(lines).strip("\n")
    first_line = cleaned.splitlines()[0] if cleaned else "DIAGRAM"
    pre_style = ParagraphStyle(
        "Diagram",
        fontName="Courier",
        fontSize=6.5,
        leading=9.0,
        textColor=INK,
        leftIndent=0,
        rightIndent=0,
    )
    diagram = Preformatted(cleaned, pre_style, maxLineLength=94)
    shell = Table([[diagram]], colWidths=[PAGE_WIDTH - 2 * MARGIN_X - 12])
    shell.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.55, INK),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return KeepTogether(
        [
            Paragraph(
                f"图：{html.escape(localize_text(first_line))}",
                styles["DiagramCaption"],
            ),
            Spacer(1, 3),
            shell,
            Spacer(1, 8),
        ]
    )


def parse_markdown(source: str, styles: dict[str, ParagraphStyle]) -> list[object]:
    lines = source.splitlines()
    story: list[object] = cover_story(styles)

    first_rule = next(
        (index for index, line in enumerate(lines) if line.strip() == "---"), 0
    )
    index = first_rule + 1
    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_buffer:
            text = " ".join(part.strip() for part in paragraph_buffer).strip()
            if text:
                style = (
                    styles["Lead"] if text.startswith("本文档以") else styles["Body"]
                )
                story.append(Paragraph(inline_markup(text), style))
            paragraph_buffer.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped == "---":
            flush_paragraph()
            story.append(Spacer(1, 4))
            index += 1
            continue

        if stripped.startswith("```diagram"):
            flush_paragraph()
            block: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index].rstrip())
                index += 1
            story.append(build_diagram(block, styles))
            index += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            block = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index].rstrip())
                index += 1
            story.append(build_diagram(block, styles))
            index += 1
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            text = heading.group(2)
            if text == "目录":
                story.append(Paragraph("目录", styles["Heading1"]))
                toc = TableOfContents()
                toc.levelStyles = [styles["TOCHeading"], styles["TOCSub"]]
                story.append(toc)
                story.append(PageBreak())
                index += 1
                while index < len(lines) and lines[index].strip() != "---":
                    index += 1
                continue
            story.append(Paragraph(inline_markup(text), styles[f"Heading{level}"]))
            index += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows: list[list[str]] = []
            for table_line in table_lines:
                cells = [cell.strip() for cell in table_line.strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    continue
                rows.append(cells)
            if rows:
                columns = len(rows[0])
                normalized = [row + [""] * (columns - len(row)) for row in rows]
                story.append(build_table(normalized, styles))
                story.append(Spacer(1, 7))
            continue

        bullet = re.match(r"^-\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            story.append(
                Paragraph(
                    inline_markup(bullet.group(1)), styles["Bullet"], bulletText="•"
                )
            )
            index += 1
            continue

        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if numbered:
            flush_paragraph()
            story.append(
                Paragraph(
                    inline_markup(numbered.group(2)),
                    styles["Numbered"],
                    bulletText=f"{numbered.group(1)}.",
                )
            )
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote_parts = [stripped.lstrip("> ")]
            index += 1
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_parts.append(lines[index].strip().lstrip("> "))
                index += 1
            story.append(
                Paragraph(inline_markup(" ".join(quote_parts)), styles["Quote"])
            )
            continue

        paragraph_buffer.append(stripped)
        index += 1

    flush_paragraph()
    return story


def build(source: Path, output: Path, sync_root: bool) -> None:
    register_fonts()
    styles = make_styles()
    markdown = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    document = ProjectPlanDocTemplate(str(output), styles)
    document.multiBuild(parse_markdown(markdown, styles))
    if sync_root:
        shutil.copyfile(output, ROOT_PDF)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sync-root",
        action="store_true",
        help="Also replace the repository's tracked Chinese-named planning PDF.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_args()
    build(arguments.source.resolve(), arguments.output.resolve(), arguments.sync_root)


if __name__ == "__main__":
    main()
