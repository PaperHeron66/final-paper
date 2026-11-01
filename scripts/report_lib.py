# -*- coding: utf-8 -*-
"""DOCX 排版工具：严格继承模板样式，提供标题/正文/图表题注/三线表等基础块。

模板约定（读取自 styles.xml）：
  Normal    ：五号宋体、1.5 倍行距、首行缩进 2 字符、两端对齐
  Heading 1 ：小四黑体、居中、自动编号 "1"
  Heading 2 ：小四黑体、左对齐、自动编号 "1.1"
"""
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


def set_run(run, size=10.5, bold=False, ea="宋体", ascii_="Times New Roman", color=None, italic=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = ascii_
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    rf.set(qn("w:ascii"), ascii_)
    rf.set(qn("w:hAnsi"), ascii_)
    rf.set(qn("w:eastAsia"), ea)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    return run


def clear(par):
    for r in list(par.runs):
        r._element.getparent().remove(r._element)


def clear_char_indent(par):
    """删除 w:ind 上的 *Chars 属性。

    Normal 样式带有 firstLineChars=200，若不显式清除，Word 会忽略以 Pt 设置的
    firstLine / hanging 值，导致“不缩进”与“悬挂缩进”失效。
    """
    ppr = par._element.get_or_add_pPr()
    for ind in ppr.findall(qn("w:ind")):
        for attr in ("w:firstLineChars", "w:leftChars", "w:rightChars", "w:hangingChars"):
            if ind.get(qn(attr)) is not None:
                del ind.attrib[qn(attr)]


def set_indent(par, first_line_pt=0, left_pt=0, hanging_pt=0):
    """统一以磅为单位设置缩进，并清除字符单位属性。"""
    clear_char_indent(par)
    pf = par.paragraph_format
    pf.left_indent = Pt(left_pt)
    if hanging_pt:
        pf.first_line_indent = Pt(-hanging_pt)
    else:
        pf.first_line_indent = Pt(first_line_pt)


class Paper:
    def __init__(self, doc):
        self.doc = doc

    # ---------------- 段落 ----------------
    def body(self, text, size=10.5, indent=True, align=None, space_after=0, bold=False, first_line_chars=2):
        p = self.doc.add_paragraph(style="Normal")
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        pf.space_before = Pt(0)
        pf.space_after = Pt(space_after)
        if indent:
            ppr = p._element.get_or_add_pPr()
            ind = ppr.find(qn("w:ind"))
            if ind is None:
                ind = OxmlElement("w:ind")
                ppr.append(ind)
            ind.set(qn("w:firstLineChars"), str(int(first_line_chars * 100)))
            ind.set(qn("w:firstLine"), str(int(size * first_line_chars * 20)))
        else:
            set_indent(p, 0, 0, 0)
        p.alignment = align if align is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
        if text:
            set_run(p.add_run(text), size=size, bold=bold)
        return p

    def para_runs(self, parts, size=10.5, indent=True, align=None):
        """parts = [(text, {bold/size/ea/...}), ...]"""
        p = self.body("", size=size, indent=indent, align=align)
        for text, kw in parts:
            set_run(p.add_run(text), **{"size": size, **kw})
        return p

    def h1(self, text):
        p = self.doc.add_paragraph(style="Heading 1")
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        set_run(p.add_run(text), size=12, bold=False, ea="黑体", ascii_="Times New Roman")
        return p

    def h2(self, text):
        p = self.doc.add_paragraph(style="Heading 2")
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        set_run(p.add_run(text), size=12, bold=False, ea="黑体", ascii_="Times New Roman")
        return p

    # ---------------- 图表 ----------------
    def caption(self, text, before=3, after=6):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_indent(p, 0, 0, 0)
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        set_run(p.add_run(text), size=10.5, bold=False, ea="宋体")
        return p

    def figure(self, path, cap, width_cm=14.2):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_indent(p, 0, 0, 0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.add_run().add_picture(str(path), width=Cm(width_cm))
        p.paragraph_format.keep_with_next = True   # 图片与题注不分页
        cap_par = self.caption(cap, before=3, after=8)
        if cap_par is not None:
            cap_par.paragraph_format.keep_with_next = True   # 题注与紧随的解读段不分页

    # ---------------- 三线表 ----------------
    @staticmethod
    def _three_line(table):
        """标准三线表：仅保留顶线、表头下线、底线；同时固定列宽。"""
        tbl = table._tbl
        tblPr = tbl.tblPr
        # 三线表边框（严格按 OOXML 子元素顺序：top, left, bottom, right, insideH, insideV）
        for old in tblPr.findall(qn("w:tblBorders")):
            tblPr.remove(old)
        borders = OxmlElement("w:tblBorders")
        for edge, val, sz in (("top", "single", 12), ("left", "none", 0),
                              ("bottom", "single", 12), ("right", "none", 0),
                              ("insideH", "none", 0), ("insideV", "none", 0)):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), val)
            el.set(qn("w:sz"), str(sz))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000" if val == "single" else "auto")
            borders.append(el)
        Paper._put(tblPr, borders, "w:tblBorders")
        # 表头下横线
        for cell in table.rows[0].cells:
            tcPr = cell._tc.get_or_add_tcPr()
            for old in tcPr.findall(qn("w:tcBorders")):
                tcPr.remove(old)
            tcB = OxmlElement("w:tcBorders")
            el = OxmlElement("w:bottom")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "8")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "000000")
            tcB.append(el)
            tcPr.append(tcB)

    @staticmethod
    def _put(tblPr, el, tag):
        """按 OOXML 规定顺序插入 tblPr 子元素，否则 Word/LO 会忽略该设置。"""
        order = ["w:tblStyle", "w:tblpPr", "w:tblOverlap", "w:bidiVisual",
                 "w:tblStyleRowBandSize", "w:tblStyleColBandSize", "w:tblW", "w:jc",
                 "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd", "w:tblLayout",
                 "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription"]
        succ = {qn(t) for t in order[order.index(tag) + 1:]}
        for child in list(tblPr):
            if child.tag in succ:
                child.addprevious(el)
                return
        tblPr.append(el)

    @staticmethod
    def _fixed_layout(table, widths_cm):
        """固定列宽：tblLayout=fixed + tblW + 每列 gridCol 与单元格 tcW。"""
        tbl = table._tbl
        tblPr = tbl.tblPr
        for old in tblPr.findall(qn("w:tblLayout")):
            tblPr.remove(old)
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        Paper._put(tblPr, layout, "w:tblLayout")

        for old in tblPr.findall(qn("w:tblW")):
            tblPr.remove(old)
        tblW = OxmlElement("w:tblW")
        total = int(sum(widths_cm) * 567)
        tblW.set(qn("w:w"), str(total))
        tblW.set(qn("w:type"), "dxa")
        Paper._put(tblPr, tblW, "w:tblW")

        # 收窄单元格左右边距，为窄列留出空间
        for old in tblPr.findall(qn("w:tblCellMar")):
            tblPr.remove(old)
        mar = OxmlElement("w:tblCellMar")
        for side, w in (("left", 60), ("right", 60)):
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:w"), str(w))
            el.set(qn("w:type"), "dxa")
            mar.append(el)
        Paper._put(tblPr, mar, "w:tblCellMar")

        grid = tbl.tblGrid
        for gc, w in zip(grid.gridCol_lst, widths_cm):
            gc.w = Cm(w)
        for row in table.rows:
            for cell, w in zip(row.cells, widths_cm):
                cell.width = Cm(w)
        # 行不跨页断开，表头跨页重复
        for i, row in enumerate(table.rows):
            trPr = row._tr.get_or_add_trPr()
            cant = OxmlElement("w:cantSplit")
            trPr.append(cant)
            if i == 0:
                hdr = OxmlElement("w:tblHeader")
                trPr.append(hdr)

    def table(self, rows, cap, font_size=9.5, widths=None, header_bold=True,
              align_first_left=True, col_align=None):
        cap_par = self.caption(cap, before=8, after=3)
        cap_par.paragraph_format.keep_with_next = True   # 题注与表格不分页
        t = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = t.cell(i, j)
                cell.text = ""
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                set_indent(p, 0, 0, 0)
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                if col_align and j < len(col_align):
                    p.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT,
                                   "c": WD_ALIGN_PARAGRAPH.CENTER,
                                   "r": WD_ALIGN_PARAGRAPH.RIGHT}[col_align[j]]
                elif j == 0 and align_first_left and len(rows[0]) > 2:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                set_run(p.add_run(str(val)), size=font_size, bold=(header_bold and i == 0), ea="宋体")
        if widths:
            self._fixed_layout(t, widths)
        self._three_line(t)
        # 表后留白
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(0)
        sp.paragraph_format.line_spacing = Pt(8)
        set_run(sp.add_run(""), size=6)
        return t
