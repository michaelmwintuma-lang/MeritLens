"""
Generates the revised Thesis Chapters 1 and 2 with highlighted corrections and revision changelog.
"""

import os
import shutil
import zipfile

def escape_xml(text):
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

class DocxThesisBuilder:
    def __init__(self):
        self.body_elements = []

    def add_title(self, text, subtitle=None):
        xml = [
            '<w:p>',
            '  <w:pPr>',
            '    <w:pStyle w:val="Title"/>',
            '    <w:spacing w:before="360" w:after="120"/>',
            '    <w:jc w:val="center"/>',
            '  </w:pPr>',
            f'  <w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:sz w:val="48"/><w:color w:val="1B365D"/></w:rPr><w:t>{escape_xml(text)}</w:t></w:r>',
            '</w:p>'
        ]
        if subtitle:
            xml.extend([
                '<w:p>',
                '  <w:pPr>',
                '    <w:pStyle w:val="Subtitle"/>',
                '    <w:spacing w:before="0" w:after="280"/>',
                '    <w:jc w:val="center"/>',
                '  </w:pPr>',
                f'  <w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:i/><w:sz w:val="24"/><w:color w:val="008080"/></w:rPr><w:t>{escape_xml(subtitle)}</w:t></w:r>',
                '</w:p>'
            ])
        self.body_elements.append("\n".join(xml))

    def add_heading_1(self, text):
        xml = f"""
<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading1"/>
    <w:spacing w:before="320" w:after="120"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="32"/>
      <w:color w:val="1B365D"/>
    </w:rPr>
    <w:t>{escape_xml(text)}</w:t>
  </w:r>
</w:p>"""
        self.body_elements.append(xml)

    def add_heading_2(self, text):
        xml = f"""
<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading2"/>
    <w:spacing w:before="240" w:after="100"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="26"/>
      <w:color w:val="008080"/>
    </w:rPr>
    <w:t>{escape_xml(text)}</w:t>
  </w:r>
</w:p>"""
        self.body_elements.append(xml)

    def add_heading_3(self, text):
        xml = f"""
<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading3"/>
    <w:spacing w:before="180" w:after="80"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="22"/>
      <w:color w:val="2B547E"/>
    </w:rPr>
    <w:t>{escape_xml(text)}</w:t>
  </w:r>
</w:p>"""
        self.body_elements.append(xml)

    def add_paragraph(self, text, bold_prefix=None, highlight=False):
        runs = []
        if bold_prefix:
            hl_tag = '<w:highlight w:val="yellow"/>' if highlight else ''
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/>{hl_tag}<w:sz w:val="22"/><w:color w:val="1B365D"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)} </w:t></w:r>')
        
        hl_tag = '<w:highlight w:val="yellow"/>' if highlight else ''
        runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{hl_tag}<w:sz w:val="22"/><w:color w:val="222222"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>')

        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="60" w:after="100" w:line="276" w:lineRule="auto"/>
  </w:pPr>
  {''.join(runs)}
</w:p>"""
        self.body_elements.append(xml)

    def add_bullet(self, text, bold_prefix=None, highlight=False):
        runs = []
        runs.append('<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="008080"/></w:rPr><w:t xml:space="preserve">&#8226;  </w:t></w:r>')
        hl_tag = '<w:highlight w:val="yellow"/>' if highlight else ''
        if bold_prefix:
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/>{hl_tag}<w:sz w:val="22"/><w:color w:val="1B365D"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)}: </w:t></w:r>')
        runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{hl_tag}<w:sz w:val="22"/><w:color w:val="222222"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>')

        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="40" w:after="60" w:line="260" w:lineRule="auto"/>
    <w:ind w:left="400" w:hanging="240"/>
  </w:pPr>
  {''.join(runs)}
</w:p>"""
        self.body_elements.append(xml)

    def add_change_note(self, text, title="SUPERVISOR CORRECTION APPLIED"):
        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="120" w:after="120" w:line="260" w:lineRule="auto"/>
    <w:ind w:left="360" w:right="360"/>
    <w:pBdr>
      <w:left w:val="single" w:sz="24" w:space="15" w:color="D97706"/>
      <w:top w:val="none"/>
      <w:right w:val="none"/>
      <w:bottom w:val="none"/>
    </w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="FEF3C7"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="20"/>
      <w:color w:val="B45309"/>
    </w:rPr>
    <w:t xml:space="preserve">&#9888; [{escape_xml(title)}]: </w:t>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:i/>
      <w:sz w:val="20"/>
      <w:color w:val="78350F"/>
    </w:rPr>
    <w:t>{escape_xml(text)}</w:t>
  </w:r>
</w:p>"""
        self.body_elements.append(xml)

    def add_table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [int(9500 / len(headers))] * len(headers)
        
        table_xml = [
            '<w:tbl>',
            '  <w:tblPr>',
            '    <w:tblW w:w="9500" w:type="dxa"/>',
            '    <w:tblBorders>',
            '      <w:top w:val="single" w:sz="6" w:space="0" w:color="CCCCCC"/>',
            '      <w:left w:val="none"/>',
            '      <w:bottom w:val="single" w:sz="12" w:space="0" w:color="1B365D"/>',
            '      <w:right w:val="none"/>',
            '      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>',
            '      <w:insideV w:val="none"/>',
            '    </w:tblBorders>',
            '    <w:tblCellMar>',
            '      <w:top w:w="120" w:type="dxa"/>',
            '      <w:left w:w="160" w:type="dxa"/>',
            '      <w:bottom w:w="120" w:type="dxa"/>',
            '      <w:right w:w="160" w:type="dxa"/>',
            '    </w:tblCellMar>',
            '  </w:tblPr>'
        ]

        # Header Row
        table_xml.append('  <w:tr>')
        table_xml.append('    <w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>')
        for idx, h in enumerate(headers):
            w = col_widths[idx]
            table_xml.append(f"""
    <w:tc>
      <w:tcPr>
        <w:tcW w:w="{w}" w:type="dxa"/>
        <w:shd w:val="clear" w:color="auto" w:fill="1B365D"/>
      </w:tcPr>
      <w:p>
        <w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>
        <w:r>
          <w:rPr>
            <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
            <w:b/>
            <w:sz w:val="20"/>
            <w:color w:val="FFFFFF"/>
          </w:rPr>
          <w:t>{escape_xml(h)}</w:t>
        </w:r>
      </w:p>
    </w:tc>""")
        table_xml.append('  </w:tr>')

        # Body Rows
        for r_idx, row in enumerate(rows):
            shading = ' w:fill="F8FAFC"' if (r_idx % 2 == 1) else ' w:fill="FFFFFF"'
            table_xml.append('  <w:tr>')
            table_xml.append('    <w:trPr><w:cantSplit/></w:trPr>')
            for c_idx, cell in enumerate(row):
                w = col_widths[c_idx]
                table_xml.append(f"""
    <w:tc>
      <w:tcPr>
        <w:tcW w:w="{w}" w:type="dxa"/>
        <w:shd w:val="clear" w:color="auto"{shading}/>
      </w:tcPr>
      <w:p>
        <w:pPr><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>
        <w:r>
          <w:rPr>
            <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
            <w:sz w:val="19"/>
            <w:color w:val="222222"/>
          </w:rPr>
          <w:t>{escape_xml(cell)}</w:t>
        </w:r>
      </w:p>
    </w:tc>""")
            table_xml.append('  </w:tr>')

        table_xml.append('</w:tbl>')
        table_xml.append('<w:p><w:pPr><w:spacing w:before="60" w:after="100"/></w:pPr></w:p>')
        self.body_elements.append("\n".join(table_xml))

    def add_page_break(self):
        self.body_elements.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def build(self, output_path):
        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

        root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

        word_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:eastAsia="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>
        <w:sz w:val="22"/>
        <w:color w:val="222222"/>
        <w:lang w:val="en-US"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault>
      <w:pPr>
        <w:spacing w:before="60" w:after="100" w:line="276" w:lineRule="auto"/>
      </w:pPr>
    </w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:rPr>
      <w:b/>
      <w:sz w:val="32"/>
      <w:color w:val="1B365D"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:rPr>
      <w:b/>
      <w:sz w:val="26"/>
      <w:color w:val="008080"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:rPr>
      <w:b/>
      <w:sz w:val="22"/>
      <w:color w:val="2B547E"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr>
      <w:b/>
      <w:sz w:val="48"/>
      <w:color w:val="1B365D"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr>
      <w:i/>
      <w:sz w:val="24"/>
      <w:color w:val="008080"/>
    </w:rPr>
  </w:style>
</w:styles>"""

        document_xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            '  <w:body>',
            "\n".join(self.body_elements),
            '    <w:sectPr>',
            '      <w:pgSz w:w="12240" w:h="15840"/>',
            '      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>',
            '    </w:sectPr>',
            '  </w:body>',
            '</w:document>'
        ]

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('[Content_Types].xml', content_types)
            z.writestr('_rels/.rels', root_rels)
            z.writestr('word/_rels/document.xml.rels', word_rels)
            z.writestr('word/styles.xml', styles_xml)
            z.writestr('word/document.xml', "\n".join(document_xml))

        print(f"Generated docx at: {output_path} ({os.path.getsize(output_path)} bytes)")


def generate_thesis_chapters():
    doc = DocxThesisBuilder()

    # Title & Metadata
    doc.add_title(
        "Design and Development of an Explainable AI-Powered Talent Intelligence Platform for Employee Promotion Prediction and Workforce Decision Support",
        "Revised & Corrected Chapters 1 & 2 (With Highlighted Supervisor Fixes)"
    )

    doc.add_change_note(
        "This revised version resolves all grammatical errors, broken citations, duplicate paragraphs, missing section headers, and academic tone inconsistencies identified by your supervisor. Key changes and newly inserted elements are marked with amber callout notices and yellow text highlights.",
        "SUPERVISOR CORRECTION SUMMARY"
    )

    doc.add_table(
        ["Correction Category", "Original Draft Flaw", "Implemented Academic Fix"],
        [
            ["Text Duplication", "Section 2.2 duplicated entire post-hoc XAI paragraph word-for-word.", "Deleted duplicate paragraph; consolidated SHAP and LIME discussion."],
            ["Text Duplication", "Section 2.1 & 2.3 had duplicated opening sentence fragments.", "Consolidated into coherent academic lead-in sentences."],
            ["Missing Section", "Section 1.5 was missing its numbered heading entirely.", "Added formal section: '1.5 Significance of the Study'."],
            ["Broken Numbering", "Chapter 2 jumped from 2.0 to 2.2, then 2.1.2, and repeated 2.2.", "Restructured into logical sequence: 2.1, 2.1.1, 2.1.2, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7."],
            ["Citation Typos", "Santos et al., 2028 (future year!); Thanker (2019); Bei al. (2025).", "Corrected to Santos et al. (2018), Thaker (2019), Bei et al. (2025), Krishna et al. (2022)."],
            ["Terminology Typos", "'exact addictive explanations' and 'compliance author'.", "Corrected to 'exact additive explanations' and 'compliance auditor'."],
            ["Academic Tone", "'fourth-fifth rule', 'lean from past decisions', 'tell you why they need to change'.", "Upgraded to formal scholarly terminology (Four-Fifths Rule, institutional disparities, actionable recourse)."]
        ],
        [2200, 3500, 3800]
    )

    doc.add_page_break()

    # CHAPTER 1
    doc.add_heading_1("CHAPTER 1: INTRODUCTION")
    
    doc.add_paragraph(
        "Promotion is among the most consequential human resource decisions an organization makes. It dictates leadership trajectories, rewards individual performance, and fundamentally shapes employees' perceptions of fairness and equity in the workplace. However, in many contemporary organizations, promotion decisions remain largely dependent on the subjective discretion of individual managers. This reliance often introduces disparate evaluation criteria, cognitive biases, and opaque deliberation processes that leave employees with minimal insight into how decisions are reached."
    )
    doc.add_paragraph(
        "Applied machine learning offers an opportunity to introduce systematic consistency by modeling an employee's readiness for promotion based on objective performance and developmental records (Benabou & Touhami, 2026). Nevertheless, algorithmic automation does not inherently ensure fairness; rather, it risks transferring subjectivity from managerial discretion to mathematical models. When trained on historical personnel data, predictive algorithms frequently encode and perpetuate pre-existing institutional biases (Rudin, 2019). Furthermore, existing algorithmic implementations operate predominantly as one-way informational pipelines: when employees suspect an assessment is flawed—due to factual inaccuracies in their personnel records or algorithmic misattribution—they lack formal institutional mechanisms to inspect, challenge, or rectify the decision."
    )
    doc.add_paragraph(
        "This project addresses these systemic limitations through the design and implementation of MeritLens, a web-based decision-support platform organized around a closed-loop operational paradigm: predict, explain, and respond. The platform estimates candidate promotion readiness, delivers faithful and transparent explanations for every prediction, and establishes an active employee feedback channel. Through this channel, employees can evaluate explanation clarity or submit formal record correction requests supported by verifiable evidence. Crucially, the platform enforces human-in-the-loop governance: the artificial intelligence functions strictly as an advisory system, preserving final decision-making authority for managers, human resource specialists, and finance officers."
    )
    doc.add_paragraph("Figure 1.1 illustrates this operational cycle.")
    doc.add_paragraph("Figure 1.1: The Predict, Explain, and Respond Cycle Followed by MeritLens", bold_prefix="Figure Caption:")

    doc.add_heading_2("1.1 Field and Subject Area of Study")
    doc.add_paragraph(
        "This research lies at the intersection of computer science, machine learning, and human resource management. Specifically, it contributes to applied machine learning with a focus on Explainable Artificial Intelligence (XAI) and algorithmic fairness within workforce analytics (people analytics). The interactive feedback architecture draws upon Human-Computer Interaction (HCI) principles, specifically operationalizing the concept of contestable AI. The final artifact is implemented as an enterprise-grade, full-stack web application developed through iterative agile software engineering methodologies."
    )

    doc.add_heading_2("1.2 Problem Statement")
    doc.add_paragraph(
        "Many organizations rely on promotion processes characterized by inconsistency, managerial ambiguity, and unexamined historical bias, while denying employees meaningful transparency or procedural recourse.",
        bold_prefix="Primary Problem:"
    )
    doc.add_paragraph("This overarching problem encompasses three distinct dimensions:")
    
    doc.add_change_note("Corrected citation from 'Santos et al., 2028' to 'Santos et al. (2018)' to eliminate the impossible future year error.", "CITATION CORRECTION")
    doc.add_bullet(
        "Managers apply disparate criteria across departments, resulting in unequal outcomes for similarly qualified employees. Although machine learning can foster consistency, most published promotion prediction models rely solely on overall accuracy. In personnel datasets where promotion is a rare event (typically 8–10%), accuracy is a deceptive metric. Furthermore, many existing models fail to address data leakage during pre-processing, omit calibration analyses, or incorporate confounding variables such as department or salary, thereby rewarding organizational placement rather than individual merit (Santos et al., 2018).",
        bold_prefix="1. Inconsistent and Biased Decision Evidence",
        highlight=True
    )
    doc.add_bullet(
        "Traditional promotion decisions and conventional machine learning models fail to provide interpretable explanations. Black-box models output scores without auditable reasoning, preventing HR committees from validating recommendations and denying employees actionable guidance regarding how to achieve future advancement.",
        bold_prefix="2. Opaque and Unactionable Predictions (The Black-Box Problem)"
    )
    doc.add_bullet(
        "Current systems operate as unilateral pipelines. Employees possess no structured mechanism to contest algorithmic assessments or correct erroneous records. As a consequence, data entry errors and ungrounded appraisals remain uncorrected, undermining trust in organizational justice.",
        bold_prefix="3. Absence of Recourse and Feedback Channels"
    )
    doc.add_paragraph(
        "Therefore, an urgent need exists for a decision-support system that generates accurate and statistically fair promotion readiness estimates, provides exact and understandable explanations, and integrates an architecturally isolated feedback channel that empowers employees without compromising model integrity."
    )

    doc.add_heading_2("1.3 Aim and Objectives")
    doc.add_heading_3("1.3.1 General Aim")
    doc.add_paragraph(
        "The primary aim of this study is to design, develop, and empirically evaluate a web-based decision-support platform that estimates employee promotion readiness, provides transparent and faithful explanations for every prediction, and incorporates an employee feedback mechanism that enables procedural contestability while maintaining human decision authority."
    )

    doc.add_heading_3("1.3.2 Specific Objectives")
    doc.add_bullet("To train and evaluate a fair machine learning model that estimates promotion readiness exclusively from performance and skill-growth data, validate its performance on held-out test data, and enforce an automated algorithmic fairness gate based on the US EEOC Four-Fifths Rule across protected demographic groups (gender, age, and education level).", bold_prefix="Objective 1 (Predict)")
    doc.add_bullet("To generate faithful, plain-language explanations for every individual prediction by decomposing additive model contributions, validating them against local surrogate models (LIME), and formulating actionable, realistic counterfactual tips to guide employee career development.", bold_prefix="Objective 2 (Explain)")
    doc.add_bullet("To engineer a secure employee feedback channel that allows staff to evaluate explanation clarity and contest factual inaccuracies with documentary evidence, ensuring that sentiment feedback cannot manipulate model predictions and that human decision-makers retain ultimate promotional authority.", bold_prefix="Objective 3 (Respond)")
    doc.add_bullet("To assess system usability, explanation faithfulness, algorithmic fairness, and perceived procedural and informational justice through automated test suites and an empirical human-centered usability study.", bold_prefix="Objective 4 (Evaluate)")

    doc.add_heading_3("1.3.3 Research Questions")
    doc.add_bullet("To what extent can employee promotion readiness be accurately and calibrationally predicted using performance and development data alone, without demographic, compensatory, or departmental attributes, while satisfying the EEOC Four-Fifths fairness criterion?", bold_prefix="RQ1 (Predictive Validity & Fairness)")
    doc.add_bullet("Can promotion readiness predictions be explained with mathematical exactness in natural language, and to what degree do intrinsic additive contributions agree with post-hoc local surrogate models (LIME)?", bold_prefix="RQ2 (Explainability & Agreement)")
    doc.add_bullet("How can an employee feedback channel be architecturally designed so that staff can voice concerns and rectify factual record errors without introducing adversarial feedback loops or gamified score inflation?", bold_prefix="RQ3 (Contestability & Feedback Isolation)")
    doc.add_bullet("How do organizational stakeholders perceive the usability of the system, and does the provision of transparent explanations and contestability mechanisms significantly enhance perceived informational and procedural justice?", bold_prefix="RQ4 (Usability & Perceived Justice)")

    doc.add_heading_2("1.4 Background of the Study")
    doc.add_paragraph(
        "People analytics leverages statistical and machine learning methodologies to enhance human resource decision-making. Prior literature demonstrates that historical evaluations, training competencies, and project deliverables serve as reliable indicators of employee potential (Benabou & Touhami, 2026; Thaker, 2019). However, standard implementations focus narrowly on binary classification accuracy while ignoring individual variance, calibration, and transparency.",
        bold_prefix="People Analytics and Algorithmic Promotion:"
    )
    doc.add_paragraph(
        "Interpretability is essential for organizational adoption. Explainable Boosting Machines (EBM) offer glass-box transparency by computing exact, readable shape functions for each predictor (Lou et al., 2013). Conversely, post-hoc methods such as SHAP (Lundberg & Lee, 2017) and LIME (Ribeiro et al., 2016) attempt to explain black-box models after training, though they often exhibit local instability. Transparent decision-support is increasingly mandated by regulatory frameworks: the European Union's AI Act (2024) classifies AI used in employment and promotion as High-Risk (Annex III), while the General Data Protection Regulation (GDPR, 2016) grants individuals rights against purely automated decisions (Article 22).",
        bold_prefix="Explainability and Emerging Regulations:"
    )
    doc.add_paragraph(
        "Statistical fairness metrics assess whether algorithms disproportionately disadvantage protected groups (Hardt et al., 2016). In employment law, the Four-Fifths (80%) Rule serves as the benchmark for establishing prima facie adverse impact (EEOC, 1978). Research indicates that employees perceive purely algorithmic management decisions as less procedurally just than human evaluations (Newman et al., 2020), emphasizing the necessity of human-in-the-loop governance.",
        bold_prefix="Algorithmic Fairness in Employment:"
    )
    doc.add_paragraph(
        "Organizational justice theory establishes that when employees are granted a meaningful voice during evaluations, their trust in management and acceptance of outcomes increase significantly (Cawley et al., 1998; Colquitt, 2001). Within human-AI interaction, contestable AI provides affected stakeholders with structural mechanisms to question, audit, and request corrections to automated assessments (Alfrink et al., 2023; Yurrita et al., 2023).",
        bold_prefix="Employee Voice and Contestability:"
    )

    doc.add_change_note("Inserted formal heading '1.5 Significance of the Study' which was missing in the original draft (originally started abruptly with 'Justifying the study is the first step').", "STRUCTURAL CORRECTION")
    doc.add_heading_2("1.5 Significance of the Study")
    doc.add_paragraph("This study contributes to academia, organizational governance, and corporate practice in four key areas:")
    doc.add_bullet("Provides unprecedented transparency regarding promotion criteria, delivers personalized, actionable development roadmaps, and guarantees procedural recourse to contest inaccurate records.", bold_prefix="For Employees", highlight=True)
    doc.add_bullet("Delivers well-calibrated, unbiased decision-support metrics, provides structured behavioral nomination rubrics, and eliminates arbitrary favoritism.", bold_prefix="For HR Specialists and Managers", highlight=True)
    doc.add_bullet("Embeds automated regulatory compliance (EU AI Act, EEOC Four-Fifths Rule), mitigates systemic discrimination liabilities, and maintains an immutable, tamper-evident SHA-256 cryptographic audit trail of all deliberations.", bold_prefix="For Organizations and Compliance Bodies", highlight=True)
    doc.add_bullet("Bridges the gap between predictive XAI theory and human-centered contestability, operationalizing a bidirectional 'predict, explain, and respond' framework that had previously been proposed only as conceptual future work.", bold_prefix="For Scientific Research", highlight=True)

    doc.add_heading_2("1.6 Scope and Delimitations of the Study")
    doc.add_change_note("Corrected typographical error 'exact addictive explanations' to 'exact additive explanations' and 'compliance author' to 'compliance auditor'. Removed duplicated sentence fragment.", "TYPOGRAPHICAL CORRECTION")
    doc.add_paragraph(
        "The project does not construct an autonomous decision-maker, but rather an explainable decision-support platform designed for six organizational roles: Employee, Manager, HR Specialist, Finance Officer, System Administrator, and Compliance Auditor.",
        highlight=True
    )
    doc.add_paragraph("Within Scope:", bold_prefix="Scope Boundaries:")
    doc.add_bullet("Modeling promotion readiness using a public, validated dataset of 100,000 synthetic employee records (Kumar, 2026).")
    doc.add_bullet("Training a Monotonic Explainable Boosting Machine (EBM) to ensure common-sense monotonicity and exact additive explanations.", highlight=True)
    doc.add_bullet("Comparative explainer auditing between exact additive feature attributions and LIME.")
    doc.add_bullet("Automated enforcement of the EEOC Four-Fifths Rule for gender, age, and education levels.")
    doc.add_bullet("A dual-path feedback channel enabling explanation rating and evidence-backed factual dispute ticketing.")
    doc.add_bullet("A human-centered usability study measuring System Usability Scale (SUS) scores and Colquitt (2001) organizational justice metrics.")

    doc.add_paragraph("Outside Scope (Delimitations):", bold_prefix="Delimitations:")
    doc.add_bullet("Processing live, proprietary corporate data (synthetic records were utilized to uphold ethical data privacy standards).")
    doc.add_bullet("Fully autonomous decision-making (the software explicitly prohibits automated promotions).")
    doc.add_bullet("Direct manipulation of AI readiness scores via feedback or complaints (scores adjust solely when HR verifies factual record corrections).")
    doc.add_bullet("Automated real-time model retraining from user feedback (to prevent model drift and adversarial poisoning).")

    doc.add_heading_2("1.7 Thesis Structure")
    doc.add_paragraph(
        "The remainder of this dissertation is organized as follows: Chapter 2 reviews the literature on promotion prediction, XAI, fairness, and contestability. Chapter 3 presents the system architecture and methodology. Chapter 4 provides the empirical results answering RQ1 through RQ4. Chapter 5 concludes with discussions, limitations, and future work."
    )

    doc.add_page_break()

    # CHAPTER 2
    doc.add_heading_1("CHAPTER 2: LITERATURE REVIEW")
    doc.add_heading_2("2.0 Introduction")
    doc.add_paragraph(
        "This chapter synthesizes the multidisciplinary literature informing the MeritLens platform across four domains: talent analytics and machine learning in promotion prediction; explainable artificial intelligence (XAI); algorithmic fairness and disparate impact; and employee voice and contestability. The chapter concludes with a systematic comparative review of existing systems and formalizes the research gaps addressed by this study."
    )

    doc.add_change_note("Re-sequenced Chapter 2 section numbering from the broken original (which jumped from 2.0 to 2.2, had subsection 2.1.2 out of place, and repeated 2.2). Removed duplicated opening sentence.", "STRUCTURAL & NUMBERING FIX")
    doc.add_heading_2("2.1 Talent Analytics and Machine Learning in Promotion Prediction")
    doc.add_heading_3("2.1.1 Overview of Predictive Modeling in HR")
    doc.add_paragraph(
        "Talent analytics applies data-driven modeling to workforce decisions, traditionally formalizing promotion readiness as a supervised binary classification problem. A substantial portion of published research in this domain relies on a benchmark dataset of 54,808 employee records released by WNS Analytics (Analytics Vidhya, 2018), in which only 8.5% of candidates were historically promoted.",
        highlight=True
    )
    doc.add_paragraph(
        "Within this literature, various classifiers have been benchmarked: Thaker (2019) reported that an XGBoost ensemble achieved an overall accuracy of 94.02%, noting that historical performance ratings, training test scores, and employee awards were the strongest predictors. Sahinbas (2022) utilized Random Forest classifiers combined with random oversampling, reporting an accuracy of 98.0%. Benabou and Touhami (2026) evaluated ensemble algorithms, reporting a 96.21% classification accuracy with Random Forest architectures."
    )
    doc.add_paragraph(
        "More recent studies have introduced post-hoc interpretability and debiasing frameworks: Bei et al. (2025) applied SHAP and LIME to gradient boosting classifiers, reporting an Area Under the ROC Curve (ROC-AUC) of 0.92. Wang et al. (2026) proposed FairPromote, integrating adversarial debiasing with SHAP attributions on a synthetic organizational dataset."
    )

    doc.add_change_note("Added Table 2.1 caption and corrected author spelling: 'Thanker(2019)' fixed to 'Thaker (2019)' and 'Bei al.' fixed to 'Bei et al.'.", "TABLE & CITATION CORRECTION")
    doc.add_paragraph("Table 2.1: Methodological Summary of Prior Promotion Prediction Studies", bold_prefix="Table Caption:")
    doc.add_table(
        ["Study Citation", "Dataset Scale", "Primary Methodology", "Headline Performance", "Critical Limitations"],
        [
            ["Thaker (2019)", "54,808 records", "XGBoost Ensemble", "94.02% Accuracy", "Severe class imbalance; low recall on minority promoted class (0.13–0.34)."],
            ["Sahinbas (2022)", "54,808 records", "Random Forest + Oversampling", "98.00% Accuracy", "Relied exclusively on accuracy; potential leakage from pre-split oversampling."],
            ["Jafor et al. (2023)", "Benchmark HR data", "Improved AdaBoost", "92.40% Accuracy", "Evaluated on global metrics only; lacked individual explanation mechanisms."],
            ["Bei et al. (2025)", "54,808 records", "Gradient Boosting + SHAP/LIME", "ROC-AUC: 0.92", "Unilateral pipeline; offered no actionable recourse or candidate interaction."],
            ["Benabou & Touhami (2026)", "54,808 records", "Random Forest", "96.21% Accuracy", "Discrepancies in test-set class distributions indicate potential evaluation leakage."],
            ["Wang et al. (2026)", "Synthetic Dataset", "FairPromote (Adversarial + SHAP)", "91.30% Accuracy", "Promotion target derived synthetically from salary levels rather than performance."]
        ],
        [2000, 1600, 2000, 1700, 2200]
    )

    doc.add_heading_3("2.1.2 Class Imbalance and Evaluation Pitfalls")
    doc.add_paragraph(
        "A critical weakness in published promotion prediction literature is the improper handling of severe class imbalance. Because promotions occur for a small minority of employees (typically 8–10%), overall classification accuracy is highly misleading. A naive classifier that blindly predicts 'not promoted' for all employees achieves 90–92% accuracy while offering zero practical utility. As Thaker (2019) demonstrated, although overall accuracy exceeded 94%, the recall for the promoted class hovered between 13% and 34%, indicating that the majority of qualifying employees were missed."
    )
    doc.add_paragraph(
        "Under extreme class imbalance, the Precision-Recall Curve (PR-AUC) is substantially more informative than the standard ROC-AUC, as it explicitly evaluates performance on the minority class relative to baseline occurrence (Saito & Rehmsmeier, 2015)."
    )
    doc.add_paragraph(
        "A second prevalent methodological flaw involves data leakage via improper resampling. Synthetic oversampling techniques such as SMOTE (Chawla et al., 2002) generate interpolated examples of the minority class. However, if oversampling is executed prior to partitioning data into training and test sets, synthetic test samples share topological feature space with training observations, artificially inflating test metrics (Santos et al., 2018). For example, Benabou and Touhami (2026) reported an evaluation set containing over 15,000 promoted and 15,000 non-promoted cases from an original dataset containing fewer than 5,000 total promotions, indicating that resampled observations contaminated the test partition."
    )

    doc.add_heading_2("2.2 Explainable Artificial Intelligence (XAI) and Actionable Recourse")
    doc.add_change_note("CRITICAL SUPERVISOR FIX: The original draft accidentally pasted the SHAP/LIME paragraph TWICE in succession. Removed the redundant duplicate block and streamlined the theoretical explanation.", "DUPLICATION REMOVAL")
    doc.add_paragraph(
        "Rudin (2019) argues that in high-stakes socio-technical domains (including criminal justice, healthcare, and employment), researchers should utilize intrinsically interpretable models rather than attempting to explain complex black-box architectures after the fact. Post-hoc explainers do not reflect the actual internal reasoning of black boxes; they merely approximate local behavior, introducing fidelity errors that can mislead decision-makers.",
        bold_prefix="Intrinsic Interpretability versus Post-Hoc Explainability:"
    )
    doc.add_paragraph(
        "Explainable Boosting Machines (EBM) represent a state-of-the-art implementation of Generalized Additive Models with pairwise interactions (GA2M) (Lou et al., 2013; Nori et al., 2019). The mathematical formulation of an EBM is: g(E[y]) = beta_0 + sum f_i(x_i) + sum f_ij(x_i, x_j), where g is the logit link function, beta_0 is the intercept baseline, f_i is a univariate spline shape function, and f_ij captures localized pairwise interactions. Because each shape function can be extracted and plotted, EBM models are completely transparent ('glass-box'). Crucially, the implementation provided by InterpretML allows practitioners to enforce monotonicity constraints, guaranteeing that an increase in a desirable attribute (e.g., training hours completed) can never decrease the resulting log-odds of promotion.",
        highlight=True
    )
    doc.add_paragraph(
        "Two post-hoc methods predominate in the machine learning literature: SHAP (Lundberg & Lee, 2017) and LIME (Ribeiro et al., 2016). Grounded in cooperative game theory, SHAP allocates additive feature attribution values that satisfy desirable properties including local accuracy. LIME fits a sparse linear surrogate model to estimate local decision boundaries. Despite their versatility, empirical evaluations demonstrate frequent divergence between SHAP and LIME when identifying the top contributing predictors for individual predictions (Krishna et al., 2022). Furthermore, standard attribution methods inform an individual why a score was received, but fail to demonstrate what specific actions would alter the outcome. Actionable recourse addresses this limitation through counterfactual explanations, identifying the minimum, realistic modifications an individual must achieve to transition across the classification threshold (Wachter et al., 2018; Ustun et al., 2019).",
        bold_prefix="Surrogate Limitations and Actionable Recourse:"
    )

    doc.add_change_note("Formatted Section 2.3 properly with heading number and title (the original draft had no section number and repeated the fragment 'The concept of algorithmic fairness in HR decisions').", "SECTION HEADING FIX")
    doc.add_heading_2("2.3 Algorithmic Fairness in Human Resource Decisions")
    doc.add_paragraph(
        "Predictive algorithms trained on historical human decisions inevitably reproduce societal and organizational disparities. In machine learning literature, algorithmic fairness is evaluated across several formal criteria, including demographic parity and equalized odds (Hardt et al., 2016). In organizational employment practice, demographic fairness is legally codified under the Four-Fifths (80%) Rule established by the US Equal Employment Opportunity Commission (EEOC, 1978; Feldman et al., 2015). Under this standard, a selection procedure produces prima facie adverse impact if the selection rate for any protected demographic group is less than 80% (0.80) of the rate for the highest-selected group.",
        bold_prefix="Group Fairness Metrics and Disparate Impact:"
    )
    doc.add_paragraph(
        "Simply removing protected attributes from model training data ('fairness through unawareness') fails to prevent discriminatory outcomes, as unconstrained models exploit correlated features as demographic proxies (Barocas & Selbst, 2016). In workforce settings, attributes such as department, commuting distance, or compensation frequently encode historical segregation. Furthermore, empirical studies demonstrate that employees perceive automated HR decisions as inherently less procedurally and interpersonally fair than decisions involving human managers (Newman et al., 2020), emphasizing the necessity of human-in-the-loop governance (Köchling & Wehner, 2020).",
        bold_prefix="The Fallacy of Fairness Through Unawareness:"
    )

    doc.add_heading_2("2.4 Employee Voice and Contestability")
    doc.add_paragraph(
        "In high-stakes socio-technical systems, explainability alone is insufficient if affected individuals cannot act upon the information provided. The human-in-the-loop paradigm must expand to embrace contestable AI—systems explicitly architected to facilitate human inquiry, challenge, and dispute (Alfrink et al., 2023). Kulesza et al. (2015) demonstrated that 'explanatory debugging,' wherein users actively inspect and correct algorithmic reasoning, improves user conceptual comprehension by 52% and facilitates rapid error correction.",
        bold_prefix="The Philosophy of Contestable AI:"
    )
    doc.add_paragraph(
        "The psychological mechanisms underlying contestability are grounded in Colquitt's (2001) multidimensional framework of organizational justice. Informational justice pertains to the adequacy and clarity of explanations, while procedural justice pertains to the fairness of the decision process itself, including employee voice (Cawley et al., 1998; Colquitt, 2001). Integrating transparent explanations enhances informational justice, while contestation mechanisms elevate procedural justice (Yurrita et al., 2023).",
        bold_prefix="Organizational Justice Theory:"
    )
    doc.add_paragraph(
        "However, naive implementations that allow employee feedback to directly alter predictive models introduce severe gaming vulnerabilities. If employee complaints directly adjust AI readiness scores, employees are incentivized to engage in adversarial manipulation. Therefore, robust system design requires an architectural quarantine: feedback must be routed to human HR specialists for independent evidentiary verification, ensuring that model predictions adjust only when underlying factual records are formally amended (Alfrink et al., 2023).",
        bold_prefix="Preventing Feedback Gaming:"
    )

    doc.add_heading_2("2.5 Systematic Review of Related Systems")
    doc.add_paragraph(
        "Table 2.2 provides a detailed comparative analysis of commercial enterprise HR suites (Workday, SAP), talent intelligence platforms (Eightfold, Visier), whistleblowing systems (NAVEX), and academic prototypes against the proposed MeritLens platform.",
        bold_prefix="Comparative Analysis:"
    )
    doc.add_table(
        ["System Capability", "Enterprise HR Suites", "Talent Platforms", "Ethics Hotlines", "Academic Prototypes", "Proposed MeritLens"],
        [
            ["Promotion Readiness Estimation", "Partial / Rule-Based", "Yes (Predictive)", "No", "Yes (Classifiers)", "Yes (Calibrated EBM)"],
            ["Glass-Box Explanations", "Limited / Proprietary", "Minimal Summary", "Not Applicable", "Rarely (Scripts)", "Yes (Exact Additive)"],
            ["Actionable Counterfactual Tips", "Limited", "Minimal", "Not Applicable", "No", "Yes (Feasible Milestones)"],
            ["EEOC Four-Fifths Build Gate", "No", "Proprietary", "Not Applicable", "Rarely", "Yes (Automated Gate)"],
            ["Bilateral Feedback & Disputes", "Partial (Notes)", "No", "Yes (Grievances)", "No (Unilateral)", "Yes (Isolated Paths)"],
            ["Cryptographic SHA-256 Audit", "Partial (RBAC)", "Partial", "Partial", "No", "Yes (Hash-Chained Log)"]
        ],
        [2200, 1600, 1500, 1300, 1500, 1400]
    )

    doc.add_heading_2("2.6 Research Gap")
    doc.add_paragraph("A synthesis of the literature reveals four critical research gaps:")
    doc.add_bullet("The majority of promotion prediction studies rely on headline classification accuracy on severely imbalanced datasets, fail to report PR-AUC, calibration error, or confidence intervals, and frequently suffer from pre-split resampling leakage.", bold_prefix="1. Evaluation and Methodological Rigor")
    doc.add_bullet("Prior studies utilizing XAI frameworks rely heavily on post-hoc local approximations (SHAP, LIME) without verifying attribution stability or mathematical faithfulness, while failing to translate attributions into realistic, actionable development roadmaps for employees.", bold_prefix="2. Explanation Faithfulness and Actionability")
    doc.add_bullet("Algorithmic promotion research treats prediction as a unilateral broadcast. While several notable studies highlight interactive recourse and candidate feedback as vital future work (Bei et al., 2025; Thaker, 2019; Wang et al., 2026), no operational platform bridges this divide by providing employees with a structured mechanism to challenge records and voice dissent.", bold_prefix="3. Absence of Procedural Contestability")
    doc.add_bullet("Existing literature vacillates between fully automated algorithmic decision-making and manual managerial discretion, lacking an integrated sociotechnical framework that unites calibrated advisory AI, structured managerial rubrics, independent HR adjudication, and cryptographic auditability.", bold_prefix="4. Integrated Human-in-the-Loop Governance")

    doc.add_heading_2("2.7 Chapter Summary")
    doc.add_paragraph(
        "This chapter critically examined the academic literature spanning talent analytics, explainable artificial intelligence, algorithmic fairness, and contestable organizational systems. The analysis revealed that while machine learning can standardize promotion evaluations, standard models suffer from class imbalance pitfalls, post-hoc explanation instability, and demographic bias. Furthermore, the absence of employee voice undermines organizational justice and legal compliance under the EU AI Act and GDPR. The theoretical foundations established herein directly inform the design and architectural implementation of the MeritLens platform, which is detailed comprehensively in Chapter 3."
    )

    # Save outputs
    out_root = "Thesis_Chapters_1_and_2_Corrected.docx"
    out_docs = os.path.join("docs", "Thesis_Chapters_1_and_2_Corrected.docx")
    doc.build(out_root)
    shutil.copyfile(out_root, out_docs)
    print(f"Copied thesis docx to: {out_docs}")

if __name__ == "__main__":
    generate_thesis_chapters()
