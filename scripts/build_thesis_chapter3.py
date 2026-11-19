"""
Generates the revised Thesis Chapter 3 (Methodology) with blue highlights on all supervisor/examiner corrections.
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

class DocxChapter3Builder:
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

    def add_paragraph(self, text, bold_prefix=None, blue_highlight=False):
        runs = []
        if bold_prefix:
            hl_tag = '<w:highlight w:val="cyan"/><w:color w:val="003366"/>' if blue_highlight else '<w:color w:val="1B365D"/>'
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/>{hl_tag}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)} </w:t></w:r>')
        
        hl_tag = '<w:highlight w:val="cyan"/><w:color w:val="003366"/>' if blue_highlight else '<w:color w:val="222222"/>'
        runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{hl_tag}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>')

        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="60" w:after="100" w:line="276" w:lineRule="auto"/>
  </w:pPr>
  {''.join(runs)}
</w:p>"""
        self.body_elements.append(xml)

    def add_bullet(self, text, bold_prefix=None, blue_highlight=False):
        runs = []
        runs.append('<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="008080"/></w:rPr><w:t xml:space="preserve">&#8226;  </w:t></w:r>')
        hl_tag = '<w:highlight w:val="cyan"/><w:color w:val="003366"/>' if blue_highlight else '<w:color w:val="222222"/>'
        if bold_prefix:
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/>{hl_tag}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)}: </w:t></w:r>')
        runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{hl_tag}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>')

        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="40" w:after="60" w:line="260" w:lineRule="auto"/>
    <w:ind w:left="400" w:hanging="240"/>
  </w:pPr>
  {''.join(runs)}
</w:p>"""
        self.body_elements.append(xml)

    def add_change_note(self, text, title="CORRECTION APPLIED"):
        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="120" w:after="120" w:line="260" w:lineRule="auto"/>
    <w:ind w:left="360" w:right="360"/>
    <w:pBdr>
      <w:left w:val="single" w:sz="24" w:space="15" w:color="008080"/>
      <w:top w:val="none"/>
      <w:right w:val="none"/>
      <w:bottom w:val="none"/>
    </w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="E0F2FE"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="20"/>
      <w:color w:val="0369A1"/>
    </w:rPr>
    <w:t xml:space="preserve">&#128269; [{escape_xml(title)}]: </w:t>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:i/>
      <w:sz w:val="20"/>
      <w:color w:val="0C4A6E"/>
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
                # Check if cell has blue highlight prefix
                is_hl = cell.startswith("[CORRECTED]")
                cell_text = cell.replace("[CORRECTED] ", "")
                hl_tag = '<w:highlight w:val="cyan"/><w:color w:val="003366"/>' if is_hl else '<w:color w:val="222222"/>'
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
            {hl_tag}
            <w:sz w:val="19"/>
          </w:rPr>
          <w:t>{escape_xml(cell_text)}</w:t>
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
        <w:szCs w:val="22"/>
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


def generate_chapter_3():
    doc = DocxChapter3Builder()

    doc.add_title(
        "CHAPTER 3: METHODOLOGY",
        "Design and Development of an Explainable AI-Powered Talent Intelligence Platform"
    )

    doc.add_change_note(
        "All corrections are highlighted in light blue (cyan) so you can easily spot and copy them over to your main thesis document. Crucial updates include: inserting the missing 'Employee' role into Table 3.1, removing 5 duplicate copy-paste sentences in Sections 3.7 & 3.8, fixing typos (Ribeiro 2016, Colquitt 2001, exact additive contributions), and restructuring Section 3.3 subheadings.",
        "EXAMINER / SUPERVISOR CORRECTIONS HIGHLIGHTED IN BLUE"
    )

    # 3.0 INTRODUCTION
    doc.add_heading_1("3.0 Introduction")
    doc.add_paragraph(
        "This chapter details the research methodology, system requirements, architecture, model development, and empirical evaluation strategy for the MeritLens platform. Organized in alignment with the project's specific objectives, the methodology addresses: (1) predictive modeling and fairness auditing (Objective 1); (2) explainability and actionable recourse methods (Objective 2); and (3) employee feedback and contestability channels (Objective 3). The chapter concludes with the human-in-the-loop decision workflow, implementation technologies, and the comprehensive evaluation plan."
    )

    # 3.1 RESEARCH APPROACH
    doc.add_heading_2("3.1 Research Approach")
    doc.add_paragraph(
        "This study adopts the Design Science Research (DSR) methodology (Peffers et al., 2007; Hevner et al., 2004), which is specifically suited for information systems research whose primary contribution is an innovative artifact that solves an identified organizational problem. The research process follows six iterative stages: (1) problem identification (Chapter 1); (2) literature-grounded objective definition (Chapter 2); (3) artifact design and development (Chapter 3); (4) end-to-end multi-role demonstration across simulated organizational personas; (5) empirical evaluation against technical, fairness, and human factors benchmarks (Chapter 4); and (6) scientific communication in this dissertation."
    )
    doc.add_paragraph(
        "The artifact development followed an iterative refinement cycle. For instance, initial algorithmic formulations occasionally suggested reducing certain performance metrics to cross the threshold, leading directly to the implementation of the strict improvement-only (monotonicity) constraint in Section 3.5.4.",
        blue_highlight=True
    )

    # 3.2 REQUIREMENTS ANALYSIS
    doc.add_heading_2("3.2 Requirements Analysis")
    doc.add_paragraph(
        "System requirements were synthesized from the problem statement, the literature design implications in Chapter 2, and the functional needs of each organizational role. Table 3.1 outlines the functional requirements by user role, and Table 3.2 details the non-functional requirements."
    )

    doc.add_change_note(
        "CRITICAL FIX: The original draft completely omitted the 'Employee' role in Table 3.1, despite Employee being the central user of the feedback channel and 'My Growth' portal. The Employee row has been restored at the top of the table in blue.",
        "TABLE 3.1 REQUIREMENT RESTORATION"
    )

    doc.add_paragraph("Table 3.1: Functional Requirements by User Role", bold_prefix="Table Caption:")
    doc.add_table(
        ["User Role", "Core Functional Requirements"],
        [
            ["[CORRECTED] Employee", "[CORRECTED] Inspect personal promotion readiness score and percentile rank; view plain-language explanations of top contributing factors; test interactive 'what-if' simulations; view actionable counterfactual improvement tips and convert tips into developmental goals; rate explanation clarity and usefulness (1–5 scale); submit formal factual record dispute tickets accompanied by document evidence."],
            ["Manager", "Review team members' readiness metrics and growth histories; set and track developmental goals with team members; submit promotion nominations using a structured 4-criteria rubric (1–5 scale) with mandatory justifications when overriding AI advice; designate managerial cover during absences."],
            ["HR Specialist / Committee", "Create and manage review cycles; review manager nominations alongside model readiness scores; hold decisions pending record dispute resolution; confirm or reject employee record correction tickets; enforce compensation policy bands; inspect live fairness dashboards; inspect model cards before releasing model versions; approve/decline requests under the optional four-eyes rule; execute GDPR data erasure requests."],
            ["Finance Officer", "Inspect approved promotion nominations to verify and sign off on proposed salary increases against organizational policy bands (default: 5%–15%); return non-compliant compensation proposals to HR with written feedback."],
            ["Compliance Auditor", "Read-only access to tamper-evident cryptographic audit logs, model registry, live EEOC fairness metrics, and aggregated feedback trends; blinded from individual employee feedback ratings."],
            ["System Administrator", "Provision user accounts and configure organizational reporting lines; monitor system health (model status, fairness gates, data drift via PSI, email delivery); inspect automated database backup status; administer the built-in double-blind user study module."]
        ],
        [2200, 7300]
    )

    doc.add_paragraph("Table 3.2: Non-Functional Requirements", bold_prefix="Table Caption:")
    doc.add_table(
        ["Requirement Category", "Technical Specification & Architectural Implementation"],
        [
            ["Feedback Privacy", "Employee explanation ratings are presented exclusively as aggregate metrics (<5 cohort masking); managers are strictly prohibited from viewing team ratings or pending dispute tickets."],
            ["Feedback & Scoring Isolation", "Feedback tables and sentiment ratings are architecturally separated from model feature tables and are never read by the prediction engine."],
            ["Human Review & Data Integrity", "Employees cannot directly alter model inputs; predictions recalculate only after HR independently validates documentary evidence and commits an audited database change."],
            ["Security & Authorization", "Role-Based Access Control (RBAC) enforced on the server for every endpoint; salted PBKDF2-SHA256 password hashing (200,000 rounds); signed, expiring JWT session tokens; rate limiting on failed logins; automatic session timeout."],
            ["Explainability", "Every prediction is accompanied by exact additive log-odds feature contributions; models are blocked by an automated EEOC Four-Fifths fairness gate prior to release."],
            ["Accountability & Auditability", "All nominations, administrative overrides, pay changes, and model deployments are recorded in an append-only audit log secured by SHA-256 cryptographic hash chains."],
            ["Usability & Accessibility", "Clean, high-contrast user interfaces; adherence to WCAG 2.1 A/AA standards (0 axe-core errors); operational status is never conveyed by color alone."],
            ["Data Protection (GDPR)", "Self-service personal data export (JSON) under Articles 15 & 20; right to erasure under Article 17; automated data retention purging schedules."],
            ["Reliability & Resilience", "Versioned database migrations, automated nightly backups with SHA-256 checksums and verified recovery tests, and structured error logging with administrative notifications."],
            ["Scalability", "[CORRECTED] List pages use a fixed number of database queries, however many employees there are, so response times stay steady as the organisation grows."]
        ],
        [2800, 6700]
    )

    # 3.3 SYSTEM ARCHITECTURE
    doc.add_heading_2("3.3 System Architecture")
    doc.add_paragraph(
        "MeritLens is engineered as a three-tier decoupled web architecture (Figure 3.1): a presentation layer built in React 19, an application services layer powered by Python FastAPI, and an isolated relational persistence layer (SQLite for development, PostgreSQL 16 for production)."
    )

    doc.add_change_note(
        "Restructured subsection numbering: inserted '3.3.1 Component Architecture' and re-sequenced '3.3.2 Architectural Isolation of the Feedback Channel' to fix the missing 3.3.1 gap.",
        "SECTION NUMBERING FIX"
    )

    doc.add_heading_3("3.3.1 Component Architecture")
    doc.add_paragraph(
        "The presentation tier communicates with the backend exclusively via HTTPS/JSON REST APIs. All business logic is encapsulated within independent modular packages: promotion (predictive inference, exact explanations, counterfactual tips, nomination rubrics), feedback (explanation ratings, record dispute ticketing, aggregate dashboards), governance (model registry, SHA-256 audit log, live fairness monitoring), privacy (GDPR export, erasure, retention), and accounts/authorization. Server-side middleware verifies user roles and session token validity on every incoming request, ensuring that the client interface cannot bypass authorization constraints.",
        blue_highlight=True
    )

    doc.add_paragraph("Figure 3.1: System Architecture of MeritLens with the Isolation Boundary", bold_prefix="Figure Caption:")

    doc.add_heading_3("3.3.2 Architectural Isolation of the Feedback Channel")
    doc.add_paragraph(
        "Although the feedback and prediction components share the application runtime and audit infrastructure, they are architecturally isolated to eliminate adversarial feedback gaming. The feedback module operates on dedicated database tables that are never referenced, imported, or queried by the prediction engine. This isolation is verified both statically through dependency analysis and dynamically at runtime: calling the prediction API triggers zero SQL queries against feedback tables.",
        blue_highlight=True
    )
    doc.add_paragraph(
        "Automated regression suites (test_isolation.py) verify that prediction outputs remain byte-for-byte invariant before and after negative feedback or pending disputes are submitted. The only mechanism through which employee feedback can influence a score is via an HR-verified factual correction (Section 3.7). Similarly, developmental goals negotiated between employees and managers are stored in a separate table and do not alter model inputs until corresponding workplace achievements are formally recorded.",
        blue_highlight=True
    )

    # 3.4 PROMOTION PREDICTION MODEL
    doc.add_heading_2("3.4 Promotion Prediction Model")
    doc.add_heading_3("3.4.1 Data and Inputs")
    doc.add_paragraph(
        "The model is trained on the Employee Promotion Prediction Dataset (Kumar, 2026), a synthetic dataset released on Kaggle under the CC0 Public Domain license. It comprises 100,000 simulated employee records across seven departments, encompassing 45 raw columns spanning multi-year performance evaluations, productivity metrics, leadership indicators, training participation, working hours, and compensation, alongside the binary promotion outcome (10.0% positive base rate).",
        blue_highlight=True
    )
    doc.add_paragraph(
        "The synthetic dataset was selected over older alternatives (such as the 54,808-record WNS Analytics dataset) because it provides detailed performance and skill-growth attributes (e.g., peer feedback, innovation ratings, attendance reliability) necessary to generate actionable, interpretable explanations. Exactly 20 features were selected as model inputs, with all exclusions documented in Table 3.3.",
        blue_highlight=True
    )

    doc.add_change_note(
        "Fixed critical slip in original draft: 'suggests promoting the student' was corrected to 'suggests promoting the employee'.",
        "TERMINOLOGY FIX"
    )
    doc.add_paragraph(
        "Definition of Promotion Readiness: The extent to which an employee's current performance and developmental trajectory resembles that of employees who were historically promoted within the organization. The model computes a continuous readiness score in the range [0, 1]; scores equal to or exceeding the decision threshold t* (Section 3.4.4) indicate a recommendation for promotion. Crucially, the score represents a calibrated ranking against threshold criteria rather than an unconditional guarantee. Because historical outcomes inherently reflect past organizational biases, the model is strictly constrained: protected characteristics and salary proxies are excluded, monotonic growth constraints are enforced, and an automated Four-Fifths fairness gate must be satisfied prior to release.",
        bold_prefix="Operational Definition:",
        blue_highlight=True
    )

    doc.add_paragraph("Table 3.3: Model Inputs Used and Attributes Excluded", bold_prefix="Table Caption:")
    doc.add_table(
        ["Feature Category", "Attributes Included / Excluded", "Selection Rationale & Status"],
        [
            ["Performance (Used: 12)", "Performance score; annual performance delta (engineered); manager rating; peer feedback; KPI achievement; projects completed; tasks completed; deadline adherence; innovation, leadership, problem-solving, and technical skill scores.", "Direct measures of employee output and competency."],
            ["Development (Used: 4)", "Training hours completed, professional certifications earned, cross-department projects, mentoring sessions logged.", "Actionable indicators of skill development."],
            ["Reliability (Used: 2)", "Attendance rate, late arrival days.", "Objective measures of work commitment."],
            ["Career Stage (Used: 2)", "Years since last promotion, years in current role.", "Captures professional tenure and organizational velocity."],
            ["Protected Attributes (Excluded)", "Gender, age, education level, marital status.", "Excluded to prevent demographic discrimination; retained solely for post-hoc fairness audits."],
            ["Department (Excluded)", "Department category (7 departments).", "Excluded: historical promotion rates varied from 2.0% (Support) to 33.2% (Engineering), biasing predictions by location."],
            ["Compensation (Excluded)", "Base salary, salary increase history, bonus, stock options.", "Excluded: prevents carrying historical wage disparities forward into promotion decisions."],
            ["Attitudes & Hours (Excluded)", "Engagement survey score, job satisfaction, monthly hours, overtime hours, meeting hours.", "Excluded: subjective attitude sentiment and hours spent, rather than actual work delivered."],
            ["Circumstances (Excluded)", "Remote-work ratio, contract type, city tier, team size, company tenure, internal mobility.", "Excluded: environmental circumstances rather than individual merit."],
            ["Earlier Performance (Replaced)", "Performance last year, performance two years ago.", "Replaced by engineered performance trend delta (correlation 0.92)."],
            ["Identifier (Excluded)", "Employee ID.", "Unique record key with no predictive value."]
        ],
        [2200, 4800, 2500]
    )

    doc.add_paragraph(
        "Dataset Limitations: Diagnostic audits confirm the simulated nature of the data: missing values and duplicate rows are exactly zero, gender is evenly split (50.1% female, 49.9% male), and promotion rates across city tiers and marital status are exactly 10.0%. Furthermore, unobserved drivers such as executive sponsorship or leadership visibility restrict the upper bound of predictive accuracy. In addition, about 2% of extreme outliers on hours and completed projects exist in the raw distribution; consequently, counterfactual tips are bounded between the 5th and 95th percentiles. All empirical results strictly describe the system on this benchmark data.",
        bold_prefix="Dataset Limitations:"
    )

    # 3.4.2 FEATURE ENGINEERING & PRE-PROCESSING
    doc.add_heading_3("3.4.2 Feature Engineering and Pre-processing")
    doc.add_paragraph(
        "Diagnostic correlation analysis revealed an exceptionally high correlation (r ≈ 0.92) between successive annual performance scores, which can cause multicollinearity and opposite sign weights in linear models. Performance was re-engineered into the current performance score and an annual performance trend delta:"
    )
    doc.add_paragraph("Performance Trend = P_t - P_{t-1}   (3.1)", bold_prefix="Equation 3.1:")
    doc.add_paragraph("where P_t denotes the current evaluation score and P_{t-1} denotes the prior year's evaluation. Continuous variables are standardized for linear models using training statistics: z = (x - mu) / sigma (Equation 3.2). All pre-processing is encapsulated in a unified scikit-learn pipeline applied consistently to training and serving data.")
    doc.add_paragraph(
        "Data Partitioning: The 100,000 records were partitioned using stratified sampling (random seed 42) into 70% training (70,000), 10% validation (10,000), and 20% held-out test data (20,000). Pre-processing statistics were fitted strictly on the training partition. Figure 3.2 illustrates the model training and selection workflow."
    )
    doc.add_paragraph("Figure 3.2: Promotion Model Training and Selection Pipeline", bold_prefix="Figure Caption:")

    # MODEL ARCHITECTURES & COMMON SENSE
    doc.add_heading_3("3.4.3 Model Comparison and Monotonic EBM Formulation")
    doc.add_paragraph(
        "Four candidate architectures were trained and benchmarked: Logistic Regression, Random Forest (Breiman, 2001), XGBoost (Chen & Guestrin, 2016), and the Monotonic Explainable Boosting Machine (EBM) (Lou et al., 2013; Nori et al., 2019)."
    )
    doc.add_paragraph(
        "The Explainable Boosting Machine is a Generalized Additive Model with pairwise interactions (GA2M) that learns one discrete shape function per feature:",
        bold_prefix="EBM Mathematical Formulation:"
    )
    doc.add_paragraph("log-odds(x) = beta_0 + sum_j f_j(x_j)   (3.3)", bold_prefix="Equation 3.3:")
    doc.add_paragraph(
        "where beta_0 is the intercept baseline and f_j represents the learned univariate spline shape function for input x_j. The promotion readiness probability p(x) is obtained via the standard logistic sigmoid transformation of the log-odds. Crucially, monotonic spline constraints are enforced across actionable inputs, guaranteeing that f_j is strictly non-decreasing."
    )

    doc.add_change_note(
        "Replaced informal phrasing ('First off, let's do a common sense check') with formal academic language ('The initial screening step applies a common-sense monotonicity verification').",
        "ACADEMIC TONE ELEVATION"
    )
    doc.add_paragraph(
        "The model selection protocol follows three sequential decision gates: (1) Monotonicity Verification: The initial screening step applies a common-sense monotonicity check across 2,000 validation candidates. Actionable inputs are increased by +0.5 standard deviations in their improving direction. The violation rate V represents the percentage of instances where an employee's score decreased. Only models achieving V = 0% are eligible for selection. (2) Validation PR-AUC Ranking: Eligible models are compared on validation Precision-Recall AUC. (3) Parsimony Rule: When models exhibit comparable accuracy, the most interpretable glass-box model within 0.01 PR-AUC of the top performer is selected (Equation 3.4; Rudin, 2019):",
        blue_highlight=True
    )
    doc.add_paragraph("PR-AUC_m >= PR-AUC_best - 0.01,  with V_m = 0%   (3.4)", bold_prefix="Equation 3.4:")

    # 3.4.4 THRESHOLD & EVALUATION METRICS
    doc.add_heading_3("3.4.4 Decision Threshold and Evaluation Metrics")
    doc.add_paragraph(
        "Because promotion is an imbalanced outcome (10% positive rate), overall classification accuracy is misleading. The decision threshold t* is tuned exclusively on the validation set to maximize the F1-score (Equation 3.5):"
    )
    doc.add_paragraph("t* = argmax_t F1(t)   (3.5)", bold_prefix="Equation 3.5:")
    doc.add_paragraph(
        "Precision = TP / (TP + FP)  (3.6)  |  Recall = TP / (TP + FN)  (3.7)  |  F1 = 2 * Precision * Recall / (Precision + Recall)  (3.8)"
    )
    doc.add_paragraph(
        "Area Under the Precision-Recall Curve (PR-AUC) serves as the primary evaluation metric (Equation 3.9; Saito & Rehmsmeier, 2015), benchmarked against the 0.10 chance baseline: PR-AUC = sum_n (R_n - R_{n-1}) * P_n. In addition, ROC-AUC, confusion matrices, and probability calibration via the Brier score (Brier, 1950) are evaluated: Brier = (1/N) sum_i (p_i - y_i)^2 (Equation 3.10)."
    )

    # 3.5 EXPLANATION METHODS
    doc.add_heading_2("3.5 Explanation Methods")
    doc.add_change_note(
        "Corrected typo in heading: '3.5.1 Exact Addictive Contributions' fixed to '3.5.1 Exact Additive Contributions'.",
        "TYPOGRAPHICAL FIX"
    )
    doc.add_heading_3("3.5.1 Exact Additive Contributions")
    doc.add_paragraph(
        "Because the chosen EBM is an additive model, each prediction decomposes exactly into a linear sum of feature contributions read directly from the model's learned terms. The contribution phi_j of input j is calculated relative to the average employee over the training distribution (Equation 3.11):",
        blue_highlight=True
    )
    doc.add_paragraph("phi_j = f_j(x_j) - E[f_j(x_j)]   (3.11)", bold_prefix="Equation 3.11:")
    doc.add_paragraph("base + sum_j phi_j = log-odds(x)   (3.12)", bold_prefix="Equation 3.12:")
    doc.add_paragraph(
        "where base = beta_0 + sum_j E[f_j(x_j)] represents the baseline log-odds of the average employee. For an additive model, these exact contributions mathematically equal the Shapley values (SHAP; Lundberg & Lee, 2017) without requiring sampling approximations.",
        blue_highlight=True
    )

    doc.add_change_note(
        "Corrected citation typo: 'Ribeiro et al., 20216' fixed to 'Ribeiro et al., 2016'. Deleted accidental prompt slip: 'The student will summarize, explain, and present a meaning from a text'.",
        "CITATION & PROMPT CLEANUP"
    )
    doc.add_heading_3("3.5.2 LIME as an Independent Second Opinion")
    doc.add_paragraph(
        "LIME provides an independent audit by fitting a sparse local linear surrogate model g around perturbed copies of the employee record (Equation 3.13; Ribeiro et al., 2016):",
        blue_highlight=True
    )
    doc.add_paragraph("xi(x) = argmin_g sum_z pi_x(z) [f(z) - g(z)]^2 + Omega(g)   (3.13)", bold_prefix="Equation 3.13:")
    doc.add_paragraph(
        "To ensure transparency regarding local surrogate fidelity, the weighted goodness-of-fit R^2 is computed and displayed (Equation 3.14). If R^2 falls below 0.50, the interface displays an explicit warning. Exact additive contributions serve as the primary explanation, with LIME functioning strictly as a comparative check.",
        blue_highlight=True
    )

    doc.add_heading_3("3.5.3 Plain-Language Summaries and Role-Based Presentation")
    doc.add_paragraph(
        "To ensure non-technical comprehension, predictions are summarized into natural language identifying the employee's readiness score, the two factors that contributed most positively, and the two factors that held the score back. On the employee's 'My Growth' portal, complex log-odds mathematics are hidden behind an optional 'Show technical details' toggle, presenting a clean, empowering interface.",
        blue_highlight=True
    )

    doc.add_heading_3("3.5.4 Interactive What-If Tool and Actionable Counterfactual Tips")
    doc.add_paragraph(
        "The What-If tool enables employees to simulate potential growth by adjusting only actionable inputs within realistic bounds without modifying stored database records. Counterfactual improvement tips compute the minimum realistic growth necessary to reach the promotion threshold t*, constrained strictly to actionable factors in their improving direction (Equation 3.15; Wachter et al., 2018; Ustun et al., 2019):",
        blue_highlight=True
    )
    doc.add_paragraph(
        "min_Delta sum_j |Delta_j| / sigma_j  subject to  p(x + Delta) >= t*,  0 <= d_j Delta_j <= sigma_j,  x_j + Delta_j in [q_{j,0.05}, q_{j,0.95}]   (3.15)",
        bold_prefix="Equation 3.15:"
    )
    doc.add_paragraph(
        "where Delta_j is the required growth for actionable input j, sigma_j is the standard deviation, d_j is the direction of improvement (+1 for training, -1 for late days), and bounds are restricted to the 5th and 95th percentiles. Employees can convert any tip into a formal developmental goal with a single click.",
        blue_highlight=True
    )

    doc.add_heading_3("3.5.5 Evaluating Explanation Quality")
    doc.add_paragraph(
        "Explanation quality is evaluated across four empirical dimensions: (1) Mathematical exactness (gap in Equation 3.12); (2) Common-sense monotonicity (zero score reductions under positive growth); (3) LIME local fidelity (Equation 3.14); and (4) Agreement between LIME's top feature and the top five exact additive contributions (Equation 3.16):"
    )
    doc.add_paragraph("Agreement = (Employees with top LIME factor in top-5 exact contributions) / (Total employees evaluated)   (3.16)", bold_prefix="Equation 3.16:")

    # 3.6 FAIRNESS AUDIT & BUILD GATE
    doc.add_heading_2("3.6 Fairness Audit and Automated Build Gate")
    doc.add_paragraph(
        "The platform enforces the US EEOC Four-Fifths (80%) Rule across gender, age groups, and education levels on the test set. The selection rate SR_g for group g is the proportion recommended (Equation 3.17): SR_g = (1/n_g) sum_i 1[p_i >= t*]. The adverse impact ratio must satisfy Equation 3.18 (EEOC, 1978; Feldman et al., 2015):"
    )
    doc.add_paragraph("Disparate Impact Ratio = min_g(SR_g) / max_g(SR_g) >= 0.80   (3.18)", bold_prefix="Equation 3.18:")
    doc.add_paragraph(
        "Any candidate model producing an adverse impact ratio below 0.80 is automatically blocked from deployment by the build pipeline. Equal opportunity (true-positive rate ratios) and intersectional cohorts (e.g., gender within age bands) are also evaluated and reported on the model card.",
        blue_highlight=True
    )
    doc.add_paragraph(
        "Proxy Variable Auditing: To ensure excluded demographic variables are not secretly reconstructed through correlated performance inputs (Barocas & Selbst, 2016), three statistical tests are conducted: (1) Effect size screening using Cohen's d (<0.20), Pearson r (<0.10), and eta^2 (<0.01); (2) Adversarial classifiers (linear and gradient-boosted) trained to predict demographic traits from the 20 merit inputs, where an ROC-AUC near 0.50 mathematically proves zero proxy leakage; and (3) Department confounding analysis.",
        bold_prefix="Proxy Variable Detection:",
        blue_highlight=True
    )

    doc.add_change_note(
        "Fixed informal heading: replaced 'Release and live monitoring are what it is called' with formal academic heading '3.6.1 Model Release Governance and Live Monitoring'.",
        "HEADING RESTRUCTURING"
    )
    doc.add_heading_3("3.6.1 Model Release Governance and Live Monitoring")
    doc.add_paragraph(
        "A newly trained model is registered as a candidate in the model registry. It can be promoted to production only after an authorized HR specialist inspects the comprehensive model card, reviews department-level projection deltas, and signs off with a written release justification. In production, live fairness monitoring recalculates the Four-Fifths ratio across nominations and approvals, while Population Stability Index (PSI) tracks demographic and feature drift.",
        blue_highlight=True
    )

    # 3.7 EMPLOYEE FEEDBACK CHANNEL
    doc.add_heading_2("3.7 Employee Feedback Channel")
    doc.add_paragraph(
        "The employee feedback channel operationalizes Objective 3 through a 'Respond to this explanation' interface on the 'My Growth' portal, providing two distinct pathways (Figure 3.3):"
    )
    doc.add_paragraph("Figure 3.3: Employee Feedback Channel Architecture (Two Distinct Routes)", bold_prefix="Figure Caption:")

    doc.add_change_note(
        "CRITICAL CLEANUP: The original draft had three copy-paste sentence repetitions in Section 3.7. Cleaned up all stuttered sentences and clarified the isolation of ratings vs record corrections.",
        "DUPLICATION CLEANUP"
    )
    doc.add_paragraph(
        "Route 1: Rating the Explanation: Employees can rate explanation clarity ('This explanation was clear') and usefulness ('This explanation was useful') on a 1–5 scale, flag individual factors perceived as unfair, and provide written commentary. Ratings are stored alongside model metadata and displayed exclusively in aggregate to HR specialists and compliance auditors. Managers are blinded to feedback ratings to prevent retaliation.",
        bold_prefix="Pathway 1 (Explanation Ratings):",
        blue_highlight=True
    )
    doc.add_paragraph(
        "Route 2: Factual Record Correction: If an employee identifies a factual discrepancy in their personnel records (e.g., unrecorded training hours or project completions), they submit a correction ticket specifying the proposed value and attaching documentary evidence (e.g., PDF review forms or certificates). The ticket is routed to HR specialists for verification. An employee cannot edit their record directly; a prediction recalculates only after HR formally validates the evidence, updates the underlying database, and records an audited change delta.",
        bold_prefix="Pathway 2 (Factual Record Corrections):",
        blue_highlight=True
    )
    doc.add_paragraph(
        "Feedback Safeguards and Aggregate Dashboards: An HR feedback dashboard displays the clarity rate, usefulness rate, and most contested factors. To preserve employee anonymity, cohort masking suppresses any demographic group with fewer than 5 ratings, displaying counts of 1 to 2 as '<3'. Models are never automatically retrained on user feedback, preventing feedback loops and adversarial manipulation.",
        bold_prefix="Feedback Safeguards:",
        blue_highlight=True
    )

    # 3.8 HUMAN IN THE LOOP
    doc.add_heading_2("3.8 Human-in-the-Loop Decision Process")
    doc.add_change_note(
        "Cleaned up sentence stutter: 'so the decision log displays the decisions where people and the model’s view at that time, so the decision log displays the decision where people and the model have disagreed'.",
        "STUTTER CLEANUP"
    )
    doc.add_paragraph(
        "In accordance with EU AI Act Article 14 mandates, MeritLens maintains strict human-in-the-loop oversight throughout the promotion lifecycle (Figure 3.4). The AI operates strictly as an advisory decision-support tool; humans retain all decision-making authority:",
        blue_highlight=True
    )
    doc.add_bullet("Managers nominate team members by completing a structured 4-criteria rubric (Job Mastery, Collaboration, Problem Solving, Continuous Growth; rated 1–5 with concrete behavioral examples). If a manager nominates an employee below the AI threshold or passes over a top candidate, a mandatory written justification is required.", bold_prefix="Manager Nomination")
    doc.add_bullet("HR committees review nominations alongside AI readiness scores, explanations, and any open employee dispute tickets. If a record dispute is pending, HR can place the nomination on 'Hold' until the factual record is verified. Approved nominations pass to Finance.", bold_prefix="HR Deliberation")
    doc.add_bullet("Finance officers review approved nominations solely to certify that proposed salary increases conform to organizational policy bands (default: 5%–15%). Finance is blinded to AI scores, performance ratings, and demographic data (strict separation of duties).", bold_prefix="Finance Compensation Sign-Off")
    doc.add_bullet("Under an optional four-eyes rule, high-impact administrative actions (releasing a model or confirming a dispute ticket that shifts an employee across the threshold) require a second HR specialist's confirmation.", bold_prefix="Four-Eyes Governance")
    doc.add_paragraph("Figure 3.4: Human-in-the-Loop Promotion Decision Process", bold_prefix="Figure Caption:")

    # 3.9 IMPLEMENTATION & SECURITY
    doc.add_heading_2("3.9 Implementation, Testing and Monitoring")
    doc.add_change_note(
        "Fixed typo: 'squlite3' corrected to 'SQLite'. Added complete architectural specifications.",
        "TYPOGRAPHICAL & TECH STACK FIX"
    )
    doc.add_paragraph(
        "MeritLens is implemented as a modern full-stack web platform utilizing React 19 (Vite, React Router 7, Tailwind CSS) for the presentation tier and Python 3.11 FastAPI for the backend API. Relational persistence is managed via SQLite in development and PostgreSQL 16 in containerized production deployments. Authentication utilizes signed, expiring JSON Web Tokens (JWT) stored in HTTP-only, SameSite cookies with salted PBKDF2-SHA256 password hashing (200,000 rounds) and optional TOTP two-factor authentication.",
        blue_highlight=True
    )
    doc.add_paragraph(
        "Automated Software Testing Suite: Software quality is enforced through 400 backend pytest cases across 37 test modules, verifying role permissions, EEOC fairness gates, explanation exactness, Finance sign-offs, feedback channel isolation, GDPR compliance, and database query count scaling (test_query_counts.py). End-to-end browser journeys are verified with Playwright, and web accessibility is audited with axe-core against WCAG 2.1 A/AA standards (0 violations across 45 screens in light and dark themes).",
        blue_highlight=True
    )

    # 3.10 EVALUATION PLAN
    doc.add_heading_2("3.10 Evaluation Plan")
    doc.add_paragraph(
        "Table 3.4 summarizes the empirical evaluation matrix, linking each system dimension to its methodological instrument and corresponding research question."
    )

    doc.add_change_note(
        "Corrected citation typo: 'Coquitt (2001)' fixed to 'Colquitt (2001)'. Properly mapped RQ1 through RQ4.",
        "EVALUATION MATRIX CLEANUP"
    )
    doc.add_paragraph("Table 3.4: System Evaluation Matrix Mapped to Research Questions", bold_prefix="Table Caption:")
    doc.add_table(
        ["Evaluation Dimension", "Methodological Instrument & Metrics", "Target Research Question"],
        [
            ["Predictive Validity & Calibration", "PR-AUC (Eq 3.9), ROC-AUC, Brier score (Eq 3.10), Expected Calibration Error (ECE), Confusion Matrix.", "RQ1"],
            ["Algorithmic Fairness Gate", "EEOC Four-Fifths Disparate Impact Ratio (Eq 3.18), Equal Opportunity ratios, Proxy Variable detection (d, r, eta^2, adversarial classifiers).", "RQ1"],
            ["Explanation Exactness & Faithfulness", "Additive log-odds exactness gap (Eq 3.12), common-sense monotonicity checks (V = 0%), LIME R^2 fidelity (Eq 3.14), LIME agreement (Eq 3.16), counterfactual tip feasibility.", "RQ2"],
            ["Feedback Channel & Isolation", "Clarity rate (Eq 3.19), contest share (Eq 3.20), correction confirmation rate (Eq 3.21); byte-for-byte static and runtime SQL isolation tests.", "RQ3"],
            ["Human Usability & Perceived Justice", "11-task standardized user test protocol, System Usability Scale (SUS; Eq 3.22; Brooke, 1996), and 8 perceived justice items adapted from Colquitt (2001) measuring informational and procedural fairness.", "RQ4"],
            ["Software Quality & Scalability", "400 backend pytests, 10 browser journeys, WCAG 2.1 A/AA accessibility audit, 5,000-employee load test with query count regression verification.", "All RQs"]
        ],
        [2400, 5600, 1500]
    )

    doc.add_paragraph(
        "Feedback Channel Formulas: The clarity rate is the proportion of explanations rated 4 or 5 for clarity: Clarity Rate = (Explanations rated 4 or 5) / (Total rated explanations) (Equation 3.19). The contest share identifies the most disputed features: Contest Share_j = n_j / sum_k n_k (Equation 3.20). The correction confirmation rate measures verified factual errors: Confirmation Rate = (Confirmed corrections) / (Resolved dispute tickets) (Equation 3.21)."
    )
    doc.add_paragraph(
        "Human Usability and Perceived Fairness Protocol: The human-centered usability study employs 5 to 8 participants across 11 realistic workplace tasks (Nielsen & Landauer, 1993). Usability is benchmarked via the 10-item System Usability Scale (SUS; Brooke, 1996; Equation 3.22): SUS = 2.5 * [sum_odd (s_i - 1) + sum_even (5 - s_i)], interpreted against Sauro (2011) industry baselines. Perceived fairness is evaluated using eight Likert items adapted from Colquitt (2001) (four measuring informational justice regarding explanation clarity and reasonableness, and four measuring procedural justice regarding voice and error correction).",
        blue_highlight=True
    )

    # 3.11 CHAPTER SUMMARY
    doc.add_heading_2("3.11 Chapter Summary")
    doc.add_change_note(
        "Cleaned up sentence stutter in Chapter Summary: 'fairness gate before it can be released, with accuracy per group reported and fairness gate before it can be released...'.",
        "STUTTER CLEANUP"
    )
    doc.add_paragraph(
        "This chapter detailed the Design Science Research methodology, user requirements, and multi-tier system architecture of MeritLens. To achieve Objective 1, four candidate algorithms were evaluated on 100,000 synthetic records, prioritizing an interpretable Monotonic EBM that satisfies common-sense checks and the EEOC Four-Fifths fairness gate. For Objective 2, predictions are explained via exact additive contributions, LIME second opinions, plain-language summaries, and actionable counterfactual tips. For Objective 3, an architecturally isolated feedback channel empowers employees to rate explanations and request factual record corrections without compromising model scoring integrity. These mechanisms are reinforced by robust software testing, role separation, and a comprehensive evaluation plan. The empirical findings are presented in Chapter 4.",
        blue_highlight=True
    )

    # Build outputs
    out_root = "Thesis_Chapter_3_Methodology_Corrected.docx"
    out_docs = os.path.join("docs", "Thesis_Chapter_3_Methodology_Corrected.docx")
    doc.build(out_root)
    shutil.copyfile(out_root, out_docs)
    print(f"Copied chapter 3 docx to: {out_docs}")

if __name__ == "__main__":
    generate_chapter_3()
