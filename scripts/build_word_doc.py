"""
MeritLens Project Documentation Index & System Reference Guide Generator
Generates a complete, professionally formatted Microsoft Word (.docx) document
without requiring third-party libraries.
"""

import zipfile
import html
import os
import shutil

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

class DocxBuilder:
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
            f'  <w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:sz w:val="52"/><w:color w:val="1B365D"/></w:rPr><w:t>{escape_xml(text)}</w:t></w:r>',
            '</w:p>'
        ]
        if subtitle:
            xml.extend([
                '<w:p>',
                '  <w:pPr>',
                '    <w:pStyle w:val="Subtitle"/>',
                '    <w:spacing w:before="0" w:after="300"/>',
                '    <w:jc w:val="center"/>',
                '  </w:pPr>',
                f'  <w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:i/><w:sz w:val="26"/><w:color w:val="008080"/></w:rPr><w:t>{escape_xml(subtitle)}</w:t></w:r>',
                '</w:p>'
            ])
        self.body_elements.append("\n".join(xml))

    def add_heading_1(self, text):
        xml = f"""
<w:p>
  <w:pPr>
    <w:pStyle w:val="Heading1"/>
    <w:spacing w:before="360" w:after="120"/>
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

    def add_paragraph(self, text, bold_prefix=None, italic=False):
        runs = []
        if bold_prefix:
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:sz w:val="22"/><w:color w:val="222222"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)} </w:t></w:r>')
        
        i_tag = '<w:i/>' if italic else ''
        runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>{i_tag}<w:sz w:val="22"/><w:color w:val="333333"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>')

        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="60" w:after="100" w:line="276" w:lineRule="auto"/>
  </w:pPr>
  {''.join(runs)}
</w:p>"""
        self.body_elements.append(xml)

    def add_bullet(self, text, bold_prefix=None):
        runs = []
        runs.append('<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="008080"/></w:rPr><w:t xml:space="preserve">&#8226;  </w:t></w:r>')
        if bold_prefix:
            runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:sz w:val="22"/><w:color w:val="1B365D"/></w:rPr><w:t xml:space="preserve">{escape_xml(bold_prefix)}: </w:t></w:r>')
        runs.append(f'<w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/><w:color w:val="333333"/></w:rPr><w:t xml:space="preserve">{escape_xml(text)}</w:t></w:r>')

        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="40" w:after="60" w:line="260" w:lineRule="auto"/>
    <w:ind w:left="400" w:hanging="240"/>
  </w:pPr>
  {''.join(runs)}
</w:p>"""
        self.body_elements.append(xml)

    def add_callout(self, text, title="IMPORTANT NOTICE"):
        xml = f"""
<w:p>
  <w:pPr>
    <w:spacing w:before="140" w:after="140" w:line="270" w:lineRule="auto"/>
    <w:ind w:left="360" w:right="360"/>
    <w:pBdr>
      <w:left w:val="single" w:sz="24" w:space="15" w:color="008080"/>
      <w:top w:val="none"/>
      <w:right w:val="none"/>
      <w:bottom w:val="none"/>
    </w:pBdr>
    <w:shd w:val="clear" w:color="auto" w:fill="F2F8F8"/>
  </w:pPr>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:b/>
      <w:sz w:val="20"/>
      <w:color w:val="008080"/>
    </w:rPr>
    <w:t xml:space="preserve">[{escape_xml(title)}] </w:t>
  </w:r>
  <w:r>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:sz w:val="20"/>
      <w:color w:val="222222"/>
    </w:rPr>
    <w:t>{escape_xml(text)}</w:t>
  </w:r>
</w:p>"""
        self.body_elements.append(xml)

    def add_table(self, headers, rows, col_widths=None):
        total_width = 9500
        if col_widths is None:
            col_widths = [int(total_width / len(headers))] * len(headers)
        
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
      <w:sz w:val="52"/>
      <w:color w:val="1B365D"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr>
      <w:i/>
      <w:sz w:val="26"/>
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

        print(f"Successfully wrote Word document to: {output_path} ({os.path.getsize(output_path)} bytes)")


def generate_meritlens_guide():
    doc = DocxBuilder()

    # Title & Metadata
    doc.add_title(
        "Project Documentation Index & System Reference Guide",
        "MeritLens: Fair, Explainable Promotion Decisions with a Voice for Every Employee"
    )

    doc.add_callout(
        "This master document serves as the primary technical specification, testing audit report, and team presentation guide for the MeritLens platform. It consolidates all system architecture, machine learning evaluations, governance protocols, and validation benchmarks.",
        "EXECUTIVE SUMMARY & SYSTEM SCOPE"
    )

    # Document Metadata Table
    doc.add_table(
        ["Attribute", "Specification Details"],
        [
            ["System Name", "MeritLens (Explainable AI Decision-Support Platform)"],
            ["Repository Path", "c:\\Projects\\HR-simple"],
            ["Core Framework", "FastAPI (Python 3.11+), React 18, Tailwind CSS, InterpretML (EBM)"],
            ["Target Domain", "Human Resource Promotion Decision-Support & Algorithmic Fairness"],
            ["Primary Ethical Standards", "EU AI Act (High-Risk Employment AI), US EEOC 4/5ths Disparate Impact Rule, Colquitt Justice Theory"],
            ["Verification Status", "400 Automated Backend Tests Passing; 100% Monotonic Explanations; Zero Proxy Leakage"]
        ],
        [3000, 6500]
    )

    doc.add_heading_1("Table of Contents")
    toc_items = [
        "1. Executive Summary & Core Philosophy",
        "2. The Six System Roles & Separation of Duties",
        "3. The Promotion Round Lifecycle (End-to-End Workflow)",
        "4. Machine Learning & Explainability Pipeline (Monotonic EBM)",
        "5. Comprehensive Testing & Validation Methodology (All 10 Domains)",
        "   5.1 Predictive Performance on Held-out Test Set (ROC-AUC & PR-AUC)",
        "   5.2 Probability Calibration & Decile Analysis (Brier & ECE)",
        "   5.3 Algorithmic Fairness: The EEOC Four-Fifths Build Gate",
        "   5.4 Subgroup Accuracy & Intersectional Parity",
        "   5.5 Elimination of Proxies & Department Confounding",
        "   5.6 Explainability Faithfulness & Monotonicity Checks",
        "   5.7 Feedback Channel Isolation Regression Tests (Zero Gaming)",
        "   5.8 Backend Software Quality & Test Suite Coverage (400 Tests)",
        "   5.9 UI, Viewport & Accessibility Validation (WCAG 2.1 A/AA)",
        "   5.10 Database Performance & N+1 Query Elimination",
        "   5.11 Human Usability & Organizational Justice Protocol (SUS & Colquitt)",
        "6. Security, Cryptographic Audit Chains & Regulatory Compliance",
        "7. Supervisory Defense & Q&A Strategy (Role Division & Model Answers)",
        "8. Master Performance & Calibration Metrics Cheat Sheet",
        "9. Project Documentation Index & Navigation Map"
    ]
    for item in toc_items:
        doc.add_paragraph(item)

    doc.add_page_break()

    # SECTION 1
    doc.add_heading_1("1. Executive Summary & Core Philosophy")
    doc.add_paragraph(
        "Workplace promotion processes are frequently criticized for being opaque 'black boxes' vulnerable to managerial favoritism, unspoken rules, and unconscious bias. Conversely, standard AI systems that predict promotions often automate and entrench historical discrimination, provide unintelligible scores, and offer employees zero procedural recourse."
    )
    doc.add_paragraph(
        "MeritLens is an Explainable AI (XAI) Decision-Support Platform engineered to resolve this fundamental organizational dilemma. It establishes a closed-loop decision support cycle:"
    )
    doc.add_bullet("Predict: An additive machine learning model scores candidate promotion readiness based strictly on objective performance and skill-growth data. Demographic variables and department labels are fully excluded, and a strict EEOC Four-Fifths fairness check blocks discriminatory models.", "1. Predict")
    doc.add_bullet("Explain: Every readiness score is decomposed into exact feature contributions and translated into natural-language statements. For employees below the promotion threshold, the system computes actionable, realistic counterfactual tips ('What-If' scenarios).", "2. Explain")
    doc.add_bullet("Respond: Employees are provided an active voice. They can rate explanation clarity, contest perceived unfairness, and submit formal factual record correction requests accompanied by documentary evidence.", "3. Respond")
    doc.add_bullet("Human-in-the-Loop Governance: Managers nominate candidates using structured behavioral rubrics; HR committees evaluate holistic dossiers and resolve disputes; Finance certifies compensation bounds. Every action is sealed in a cryptographic SHA-256 audit log.", "4. Govern")

    doc.add_callout(
        "Cardinal Rule: The AI never makes the promotion decision. Humans decide. Furthermore, employee ratings or contestations never modify their AI score directly. A score updates only if HR verifies factual documentary evidence and amends the underlying performance database.",
        "CORE GOVERNANCE PRINCIPLE"
    )

    # SECTION 2
    doc.add_heading_1("2. The Six System Roles & Separation of Duties")
    doc.add_paragraph(
        "MeritLens enforces rigorous Role-Based Access Control (RBAC) across six organizational personas to maintain procedural justice and organizational separation of duties:"
    )

    doc.add_table(
        ["Role Persona", "Primary System Capabilities", "Access Boundaries & Blindspots"],
        [
            ["Employee", "Views 'My Growth' portal; inspects readiness score, exact additive contributions, and actionable tips; runs interactive 'what-if' simulators; submits factual dispute tickets with evidence.", "Can only see their own file. Cannot access manager nomination notes, peer scores, or HR deliberation logs."],
            ["Manager", "Inspects team member readiness metrics; reviews historical trends; nominates candidates for review cycles using a 4-criteria behavioral rubric; writes mandatory justifications when overriding the AI.", "Can only see direct/indirect department reports. Completely blinded to employee explanation ratings and pending correction tickets (anti-retaliation)."],
            ["HR Specialist / Committee", "Creates and manages company promotion cycles; evaluates manager nominations alongside AI explanations; resolves employee record corrections; grants approvals, holds, or rejections; tracks organization-wide fairness.", "Has organizational visibility over performance and nominations. Strictly blinded from approving salary compensation adjustments (separation of financial powers)."],
            ["Finance Officer", "Inspects approved promotions solely to verify and approve proposed salary increases within company policy bands (e.g., 5% to 15% limits); manages payroll transitions.", "Blinded to AI readiness scores, performance notes, manager commentary, and employee demographic data. Focus is strictly budgetary."],
            ["Compliance Auditor", "Conducts compliance reviews; inspects cryptographic SHA-256 tamper-evident audit trails; audits EEOC fairness metrics and aggregated feedback trends.", "Global read-only access. Strictly prohibited from creating, updating, or deleting operational records."],
            ["System Administrator", "User account provisioning; reporting tree configuration; database backups; monitoring model drift (Population Stability Index).", "Administrative systems access. Cannot nominate candidates or approve promotions."]
        ],
        [2000, 4200, 3300]
    )

    # SECTION 3
    doc.add_heading_1("3. The Promotion Round Lifecycle (End-to-End Workflow)")
    doc.add_paragraph(
        "A standard promotion cycle flows through five tightly coordinated phases:"
    )
    doc.add_bullet("HR initializes an official promotion round with defined start and end dates. The system triggers batch scoring, generating immutable snapshot predictions and baseline fairness metrics for all eligible staff.", "Phase 1: Activation & Snapshot")
    doc.add_bullet("Department managers review their team dashboards. Nominations require completing an anchored 4-part rubric (Job Mastery, Team Collaboration, Problem Solving, Continuous Growth; rated 1–5). If a manager nominates an employee below the 0.2283 AI threshold, or passes over a top candidate, the system enforces a mandatory written rationale.", "Phase 2: Manager Nominations")
    doc.add_bullet("HR reviews the nomination dossiers. If an employee has an active factual dispute ticket regarding their performance records, the decision is placed on 'Hold' until resolved. HR formally Approves, Holds, or Rejects.", "Phase 3: HR Review & Dispute Resolution")
    doc.add_bullet("Approved candidates are routed to the Finance dashboard. Finance validates that proposed compensation increases conform to organizational policy bands, preventing unbudgeted or inequitable pay awards.", "Phase 4: Finance Compensation Sign-Off")
    doc.add_bullet("Upon Finance approval, the promotion is finalized. An entry is appended to the SHA-256 cryptographic audit chain, and an automated notification is dispatched to the employee.", "Phase 5: Audit Sealing & Notification")

    # SECTION 4
    doc.add_heading_1("4. Machine Learning & Explainability Pipeline")
    doc.add_paragraph(
        "The predictive engine is built on 100,000 synthetic employee records (Kumar, 2026, Kaggle, CC0) partitioned into 70,000 training, 10,000 validation, and 20,000 test records using stratified random sampling."
    )
    doc.add_heading_2("Feature Auditing & Exclusion Policy")
    doc.add_paragraph(
        "To satisfy legal and ethical guidelines, candidate features were scrutinized under strict exclusion criteria:"
    )
    doc.add_bullet("Gender, age, education level, and marital status were excluded from all model inputs and reserved strictly for post-hoc fairness audits.", "Protected Attributes")
    doc.add_bullet("Department was removed because historical promotion rates varied wildly from 2.0% in Support to 33.2% in Engineering. Including department rewarded employees based on office politics and organizational silos rather than individual merit.", "Systemic Biases")
    doc.add_bullet("Base salary, overtime/working hours, subjective attitude surveys, and office location tiers were eliminated to prevent contaminated proxy leakage.", "Contaminated Proxies")
    doc.add_bullet("20 objective, development-oriented metrics were retained, including annual performance improvement (+51.5% total model weight), completed projects (10.7%), tasks completed on schedule (6.9%), leadership rating (4.5%), and verified training hours.", "Retained Merit Inputs")

    doc.add_heading_2("Model Selection & The Common-Sense Monotonicity Test")
    doc.add_paragraph(
        "Four candidate architectures were trained and subjected to an automated common-sense monotonicity test on 2,000 validation employees. Actionable growth inputs were nudged upward by +0.5 standard deviations. Any reduction in an employee's score was recorded as a common-sense violation:"
    )
    doc.add_table(
        ["Candidate Architecture", "Validation PR-AUC", "Validation ROC-AUC", "Common-Sense Violations", "Eligibility Status"],
        [
            ["Monotonic EBM (Chosen)", "0.4671", "0.8806", "0.0%", "PASSED & SELECTED"],
            ["XGBoost Ensemble", "0.4699", "0.8777", "21.9%", "REJECTED (Severe Violations)"],
            ["Logistic Regression", "0.4618", "0.8793", "16.7%", "REJECTED (Multicollinearity Drops)"],
            ["Random Forest", "0.4528", "0.8769", "30.1%", "REJECTED (High Violation Rate)"]
        ],
        [2500, 1800, 1800, 1800, 1600]
    )

    doc.add_callout(
        "Why Explainable Boosting Machines (EBM)? EBM belongs to the Generalized Additive Model family with pairwise interactions. By enforcing monotonic spline constraints, MeritLens mathematically guarantees that an employee who takes more training or finishes more projects will NEVER see their readiness score decrease. Standard gradient boosting (XGBoost) failed this basic test in over 21% of instances.",
        "THE MONOTONICITY BREAKTHROUGH"
    )

    doc.add_page_break()

    # SECTION 5: THE COMPLETE TESTING & VALIDATION METHODOLOGY
    doc.add_heading_1("5. Comprehensive Testing & Validation Methodology")
    doc.add_paragraph(
        "The testing and validation of MeritLens was conducted across ten rigorous, independent technical and human-centered dimensions. Every empirical claim in this system is backed by an automated script and reproducible test fixture."
    )

    doc.add_heading_2("5.1 Predictive Performance on Held-out Test Set (20,000 Employees)")
    doc.add_paragraph(
        "The final monotonic EBM model was evaluated on 20,000 unseen test employees at the validation-optimized decision threshold of 0.2283:"
    )
    doc.add_table(
        ["Metric Name", "Empirical Value", "Baseline / Target", "Technical Interpretation"],
        [
            ["ROC-AUC", "0.8833", "0.5000 (Random)", "Excellent discrimination across varying decision thresholds."],
            ["PR-AUC", "0.4736", "0.1000 (Base Rate)", "Primary metric for imbalanced data (10% positive class). Represents a 4.7x lift over random guessing."],
            ["Precision", "41.02%", "-", "41% of recommended candidates were historically promoted."],
            ["Recall", "59.50%", "-", "Captures 60% of all historically promoted employees."],
            ["F1-Score", "0.4856", "-", "Harmonic mean optimized at threshold 0.2283."],
            ["Overall Accuracy", "87.40%", "-", "High true-negative recognition on imbalanced data."],
            ["Selection Share", "14.50%", "10.00% (Historical)", "Identifies an expanded pool of high-readiness candidates."]
        ],
        [2000, 1800, 2200, 3500]
    )

    doc.add_heading_2("5.2 Probability Calibration & Decile Analysis")
    doc.add_paragraph(
        "A model used for human decision-support must produce well-calibrated probabilities, not arbitrary relative rankings. Evaluated using Brier score and Expected Calibration Error (ECE):"
    )
    doc.add_bullet("Brier Score: 0.0677 (compared to 0.0900 for a naive model guessing the 10% base rate).", "Brier Score")
    doc.add_bullet("Brier Skill Score: 0.248 (24.8% improvement over standard baseline).", "Brier Skill")
    doc.add_bullet("Expected Calibration Error (ECE across 10 deciles): 0.0056 (under 0.6% deviation).", "ECE")
    doc.add_bullet("Reliability Curve Fit: Slope = 0.998, Intercept = -0.013. Scores near the 0.23 threshold map to an observed empirical promotion rate of 23.7%.", "Reliability")

    doc.add_heading_2("5.3 Algorithmic Fairness: The EEOC Four-Fifths Build Gate")
    doc.add_paragraph(
        "Under US Equal Employment Opportunity Commission (EEOC) guidelines, an adverse impact is detected if a protected demographic's selection rate is less than 80% (0.80) of the highest group's rate. MeritLens embeds this check as an automated CI/CD gate—any model failing this test cannot be deployed:"
    )
    doc.add_table(
        ["Demographic Characteristic", "Group Selection Rates", "Adverse Impact Ratio", "EEOC Gate Outcome"],
        [
            ["Gender", "Female: 14.6%, Male: 14.4%", "0.982 (Well above 0.80)", "PASSED (No Disparate Impact)"],
            ["Age Group", "Under 40: 14.8%, 40+: 14.2%", "0.963 (Well above 0.80)", "PASSED (No Disparate Impact)"],
            ["Education Level", "Bachelor: 14.3%, Master: 14.7%, PhD: 16.1%", "0.887 (Lowest-to-highest)", "PASSED (No Disparate Impact)"]
        ],
        [2400, 3100, 2200, 1800]
    )

    doc.add_heading_2("5.4 Subgroup Accuracy & Intersectional Parity")
    doc.add_paragraph(
        "In addition to selection rates, the system was validated across intersectional demographic slices to prevent hidden harms:"
    )
    doc.add_bullet("Gender True-Positive Rate (TPR) Ratio: 0.952 (Female TPR 61.0% vs Male TPR 58.1%).", "Gender Equal Opportunity")
    doc.add_bullet("Age True-Positive Rate Ratio: 0.899 (Under 40 TPR 63.0% vs Age 40+ TPR 56.6%).", "Age Equal Opportunity")
    doc.add_bullet("Intersectional Selection Ratio: Female Under 40 (15.0%) vs Male 40+ (14.1%) yielded a ratio of 0.945.", "Intersectional Parity")
    doc.add_bullet("False-Positive Rate Parity: False-positive rates across all seven demographic and intersectional cohorts remained tightly bounded between 9.1% and 10.4% (maximum disparity of only 1.3 percentage points).", "FPR Parity")

    doc.add_heading_2("5.5 Elimination of Proxies & Department Confounding")
    doc.add_paragraph(
        "To verify that the 20 merit inputs did not secretly encode demographic proxies, adversarial classifiers were trained to predict gender, age, and education exclusively from performance data:"
    )
    doc.add_bullet("Gender Classifier: ROC-AUC = 0.500 (Pure random guessing; zero demographic signal in performance inputs).", "Gender Proxy Check")
    doc.add_bullet("Age Group Classifier: ROC-AUC = 0.500 (Cohen's d < 0.016, statistically negligible).", "Age Proxy Check")
    doc.add_bullet("Education Classifier: ROC-AUC = 0.500 (No degree proxy leakage).", "Education Proxy Check")
    doc.add_bullet("Department Analysis: Excluding department was a deliberate ethical choice. While including department increased PR-AUC to 0.6325, it severely penalized low-promotion departments. Without department, the model recommends 24.7% of Engineering vs 7.9% of Support (compared to historical rates of 33.2% vs 2.0%), significantly leveling the playing field.", "Department Confounder")

    doc.add_page_break()

    doc.add_heading_2("5.6 Explainability Faithfulness & Monotonicity Checks")
    doc.add_paragraph(
        "Explanations were validated on the 120-employee validation sample using automated scripts (evaluate_explanations.py):"
    )
    doc.add_bullet("Mathematical Exactness: The maximum gap between the baseline log-odds plus the sum of all individual feature contributions and the model's direct output was 0.000347, proving exact mathematical faithfulness.", "Mathematical Exactness")
    doc.add_bullet("Explanatory Monotonicity: 2,040 individual perturbation checks (17 continuous features x 120 employees) confirmed that improving a performance metric NEVER lowered a score or produced a negative contribution delta.", "Perturbation Checks")
    doc.add_bullet("Actionable Tips Validity: For 90.7% (98 of 108) of employees currently below threshold, the counterfactual tips generated a viable path to cross the 0.2283 promotion threshold within reasonable growth parameters.", "Counterfactual Feasibility")
    doc.add_bullet("LIME Sanity Audit: LIME local linear models exhibited poor fit (median R2 = 0.135) due to flat decision boundaries far from the threshold, proving why intrinsic EBM glass-box models are vastly superior to post-hoc explainers.", "LIME Comparative Audit")

    doc.add_heading_2("5.7 Feedback Channel Isolation Regression Tests (Zero Gaming)")
    doc.add_paragraph(
        "A central vulnerability in algorithmic governance is feedback gaming. The isolation test suite (test_isolation.py) verified total architectural separation:"
    )
    doc.add_bullet("The prediction API responses for target employees were recorded as cryptographic byte baselines.", "Baseline Recording")
    doc.add_bullet("Aggressive negative user ratings (e.g., rating = 1, 'Extremely unfair') and pending/rejected factual dispute tickets were submitted.", "Adversarial Injection")
    doc.add_bullet("Subsequent prediction calls returned byte-for-byte identical scores, confirming that user sentiment cannot contaminate the scoring model.", "Invariance Verification")
    doc.add_bullet("A score updates ONLY when an HR specialist verifies physical documentation, updates the record in the database, and triggers an audited recalculation.", "Controlled Update Pipeline")

    doc.add_heading_2("5.8 Backend Software Quality & Test Suite Coverage")
    doc.add_paragraph(
        "The backend is covered by 400 automated pytest cases across 37 dedicated test suites executing in under five minutes:"
    )
    doc.add_table(
        ["Test Module", "Test Focus & Security Boundary", "Status"],
        [
            ["test_auth_and_roles.py", "JWT token signing, role-based endpoint permissions, deactivation lockout", "PASSED"],
            ["test_isolation.py", "Proves employee feedback and ratings never modify AI predictions", "PASSED"],
            ["test_governance.py", "SHA-256 cryptographic audit hash chaining and tamper detection", "PASSED"],
            ["test_cycles.py", "Promotion review round state transitions, batch scoring, deadline controls", "PASSED"],
            ["test_approvals.py", "Manager nominations, 4-part rubrics, override justifications", "PASSED"],
            ["test_finance_operations.py", "Finance salary sign-offs, policy threshold enforcement (5-15%)", "PASSED"],
            ["test_email_delivery.py", "In-app notifications, digest generation, delivery tracking", "PASSED"],
            ["test_privacy.py", "GDPR Article 15/20 data portability, demographic masking (<5 rule)", "PASSED"],
            ["test_query_counts.py", "Regression fixture ensuring database queries never grow with row counts", "PASSED"],
            ["test_backups.py", "Automated database backups, restore verification, schema integrity", "PASSED"]
        ],
        [2800, 5200, 1500]
    )

    doc.add_heading_2("5.9 UI, Viewport & Accessibility Validation")
    doc.add_paragraph(
        "The front-end was evaluated using automated browser automation scripts (scripts/browser_test.py):"
    )
    doc.add_bullet("Automated Headless Journeys: 10 complex multi-role workflows were executed end-to-end without errors.", "E2E Journeys")
    doc.add_bullet("Accessibility Compliance: Evaluated with axe-core across 45 unique screens in both light and dark themes. Achieved 0 WCAG 2.1 A/AA violations.", "axe-core WCAG Audit")
    doc.add_bullet("Mobile Responsiveness: Verified on emulated 390px mobile viewports; zero horizontal overflow detected.", "Mobile Viewport")

    doc.add_heading_2("5.10 Database Performance & N+1 Query Elimination")
    doc.add_paragraph(
        "A load test on a 5,000-employee database (results/load_test.json) confirmed that query optimization eliminated all N+1 query loops:"
    )
    doc.add_table(
        ["Endpoint / Operation", "Queries Before Fix", "Queries After Fix", "Median Latency (5k Employees)"],
        [
            ["Batch Scoring 5,000 Staff", "5,000+ roundtrips", "Vectorized Batch", "13 milliseconds"],
            ["Opening Review Cycle", "5,022 queries", "23 queries", "0.69 seconds"],
            ["HR Nominations Dashboard", "1,204 queries", "6 queries", "0.05 seconds"],
            ["Finance Salary Reviews", "604 queries", "8 queries", "0.02 seconds"],
            ["Decision Log Inspection", "903 queries", "6 queries", "0.03 seconds"]
        ],
        [3200, 2100, 2100, 2100]
    )

    doc.add_heading_2("5.11 Human Usability & Organizational Justice Protocol")
    doc.add_paragraph(
        "MeritLens embeds an automated User Study Module (docs/USER_TEST.md) directly into the Admin portal to measure human factors:"
    )
    doc.add_bullet("11 Structured Task Scenarios: Participants execute tasks across Employee (T1-T5), Manager (T6-T7), HR (T8-T10), and Verification (T11) roles.", "Standardized Tasks")
    doc.add_bullet("System Usability Scale (SUS): 10-item standardized usability instrument measuring operational friction.", "SUS Benchmark")
    doc.add_bullet("Colquitt Organizational Justice Survey: 8 validated Likert items measuring informational justice (clarity and reasonableness of explanations) and procedural justice (voice, consistency, and ability to request factual correction).", "Justice Perception")
    doc.add_bullet("Built-in Administration Portal: Enables researchers to assign anonymous subject IDs (P1, P2), guide sessions with timed tasks, and export structured analysis reports with Cronbach's alpha.", "Double-Blind Lab Tool")

    doc.add_page_break()

    # SECTION 6
    doc.add_heading_1("6. Security, Cryptographic Audit Chains & Regulatory Compliance")
    doc.add_heading_2("6.1 EU AI Act High-Risk Compliance")
    doc.add_paragraph(
        "Employment decision-support systems are classified as High-Risk under Annex III of the EU AI Act. MeritLens was built to comply with these stringent regulations:"
    )
    doc.add_bullet("Article 14 (Human Oversight): MeritLens enforces human-in-the-loop governance. The AI cannot execute promotions autonomously; it advises managers and HR committees.", "Human Oversight")
    doc.add_bullet("Article 12 (Traceability & Record-Keeping): All predictions, human overrides, and managerial justifications are persistently logged in immutable storage.", "Traceability")
    doc.add_bullet("Article 10 (Data Governance & Bias Monitoring): Four-Fifths fairness gates block biased deployments, and the Population Stability Index (PSI) monitors live data drift.", "Bias Auditing")

    doc.add_heading_2("6.2 SHA-256 Cryptographic Audit Hash Chains")
    doc.add_paragraph(
        "To prevent retroactive manipulation by rogue administrators or compromised accounts, the audit trail operates as a tamper-evident blockchain-style hash chain:"
    )
    doc.add_paragraph(
        "Block_Hash[n] = SHA-256(Block_Hash[n-1] + Timestamp + Actor_ID + Action + Payload_Digest)",
        bold_prefix="Cryptographic Chain Formulation:"
    )
    doc.add_paragraph(
        "Any modification to a past nomination, score, or manager justification breaks all downstream hashes. Auditors can click 'Verify Chain' in the UI to mathematically validate the entire organizational history in seconds."
    )

    doc.add_heading_2("6.3 Privacy by Design & GDPR Alignment")
    doc.add_bullet("GDPR Articles 15 & 20: One-click personal data export allows employees to download their full dossier, predictions, and dispute history in structured JSON.", "Right to Access & Portability")
    doc.add_bullet("GDPR Article 17: Right to Erasure support with anonymization safeguards for historic aggregate fairness audits.", "Right to Erasure")
    doc.add_bullet("Demographic Cohort Masking: Aggregate fairness reports mask any demographic cohort containing fewer than 5 employees (<5) to eliminate re-identification risks.", "K-Anonymity Safeguard")

    # SECTION 7
    doc.add_heading_1("7. Supervisory Defense & Q&A Strategy")
    doc.add_paragraph(
        "Suggested distribution of presentation responsibilities for project group members:"
    )
    doc.add_table(
        ["Team Member Role", "Assigned Topic Focus", "Primary Live System Demo"],
        [
            ["Speaker 1: Product & Ethics", "The problem of promotion opacity; 3-step cycle (Predict, Explain, Respond); procedural justice principles.", "Employee Portal ('My Growth'), Natural-Language Explanations, Interactive 'What-If' Sliders"],
            ["Speaker 2: Machine Learning", "Dataset properties; why Monotonic EBM beat XGBoost; PR-AUC vs ROC-AUC; EEOC Four-Fifths build gate.", "Model Card, Feature Importance Chart, Live Organizational Fairness Dashboard"],
            ["Speaker 3: Governance & Workflow", "Manager 4-part rubric; override justifications; HR review; Finance separation of duties; dispute tickets.", "Submit Manager Nomination, HR Approval with Hold, Finance Compensation Sign-Off"],
            ["Speaker 4: Architecture & Security", "FastAPI/React architecture; N+1 query elimination; SHA-256 audit chain; EU AI Act compliance.", "Click 'Verify Chain' in Audit Log, 400 Backend Pytest Summary, User Study Portal"]
        ],
        [2500, 3800, 3200]
    )

    doc.add_heading_2("Top 4 Supervisor / Panel Defense Questions")
    qa_list = [
        ("Why did you select EBM over XGBoost if XGBoost had a slightly higher validation PR-AUC?",
         "XGBoost achieved a PR-AUC of 0.4699 compared to EBM's 0.4671—a negligible difference of 0.0028. However, XGBoost produced common-sense monotonicity violations in 21.9% of tests, meaning employees improving their skills could see their scores drop. EBM achieved 0.0% violations while delivering exact additive explanations without relying on post-hoc linear approximations like LIME."),
        ("Why did you eliminate the Department feature if it was highly predictive?",
         "Including department increased PR-AUC to 0.6325, but it learned historical organizational inequality: Engineering had a 33% promotion rate while Support had 2%. Using department would institutionalize past unequal opportunity. Eliminating department leveled the playing field, ensuring candidates are judged on individual growth rather than team placement."),
        ("How do you guarantee employees cannot game the AI with dispute tickets?",
         "The feedback channel is architecturally quarantined (verified in test_isolation.py). User ratings and submitted correction tickets have zero programmatic connection to feature matrices. A score recalculates ONLY if HR independently validates supporting evidence and amends the underlying database record."),
        ("What happens when a manager overrides the AI recommendation?",
         "MeritLens is a decision-support system, not an autonomous decider. Managers can nominate candidates below the threshold or pass over high-scoring candidates, but the interface forces them to complete a structured 4-part behavioral rubric and provide a written justification. This creates a transparent audit trail for HR committee scrutiny.")
    ]
    for q, a in qa_list:
        doc.add_paragraph(q, bold_prefix="Q:")
        doc.add_paragraph(a, bold_prefix="Answer:")

    doc.add_page_break()

    # SECTION 8
    doc.add_heading_1("8. Master Performance & Calibration Metrics Cheat Sheet")
    doc.add_paragraph(
        "Quick reference table summarizing all verified mathematical and system metrics for rapid recall during project presentations and defense evaluations:"
    )
    doc.add_table(
        ["Benchmark Metric Category", "Verified Quantitative Result", "Significance & Context"],
        [
            ["Dataset Scale", "100,000 synthetic rows (Kumar, 2026)", "Stratified split: 70k train, 10k val, 20k test"],
            ["Base Promotion Rate", "10.0% positive class", "Realistic imbalanced organizational distribution"],
            ["EBM Test ROC-AUC", "0.8833", "Strong global ranking and discrimination capacity"],
            ["EBM Test PR-AUC", "0.4736", "4.7x lift over 0.10 chance baseline"],
            ["Decision Threshold", "0.2283", "Optimized for maximum F1 on validation set"],
            ["EBM Test Precision / Recall", "41.02% / 59.50%", "F1-Score = 0.4856 at 0.2283 threshold"],
            ["Monotonicity Violations", "0.0% (EBM) vs 21.9% (XGBoost)", "Proves that positive growth never lowers score"],
            ["Brier Score / Brier Skill", "0.0677 / 0.248", "High probability calibration accuracy"],
            ["Expected Calibration Error", "0.0056 (10 deciles)", "Scores near 0.23 reflect 23.7% actual promotions"],
            ["Gender Four-Fifths Ratio", "0.982 (Female 14.6%, Male 14.4%)", "Passed EEOC adverse impact threshold (>0.80)"],
            ["Age Four-Fifths Ratio", "0.963 (Under 40: 14.8%, 40+: 14.2%)", "Passed EEOC adverse impact threshold (>0.80)"],
            ["Education Four-Fifths Ratio", "0.887 (Bachelor 14.3%, PhD 16.1%)", "Passed EEOC adverse impact threshold (>0.80)"],
            ["Demographic Proxy Signal", "ROC-AUC = 0.500 (Zero Signal)", "Performance inputs do not encode protected traits"],
            ["Explanation Exactness Gap", "0.000347 (Log-odds diff)", "Mathematically exact additive decomposition"],
            ["Counterfactual Tip Reach", "90.7% (98 of 108 candidates)", "Achievable milestone roadmap to promotion threshold"],
            ["Feedback Isolation Check", "Byte-for-byte invariant", "Proves sentiment feedback cannot game the AI"],
            ["Automated Test Suites", "400 backend pytest cases", "100% pass across 37 test modules"],
            ["Accessibility Audit", "0 WCAG 2.1 A/AA violations", "45 screens audited with axe-core in light/dark"],
            ["Batch Scoring Latency", "13 ms for 5,000 employees", "Vectorized inference eliminates runtime bottlenecks"]
        ],
        [2600, 3100, 3800]
    )

    # SECTION 9
    doc.add_heading_1("9. Project Documentation Index & Navigation Map")
    doc.add_paragraph(
        "Guide to all specialized documentation files located within the docs/ directory of the repository:"
    )
    doc.add_table(
        ["Document Filename", "Document Scope & Summary", "Target Audience", "Read Time"],
        [
            ["README.md", "Complete system overview, local installation guide, role quickstarts, and execution commands.", "All Team Members & Evaluators", "10 min"],
            ["docs/TEAM_PROJECT_OVERVIEW.md", "High-level summary, presentation role division, 10-minute crash course on system philosophy.", "Team Members & Presenters", "8 min"],
            ["docs/HOW_IT_WORKS.md", "Exhaustive technical deep-dive into every database table, API endpoint, auth token, and review step.", "Backend Developers & Architects", "25 min"],
            ["docs/EVALUATION_RESULTS.md", "Byte-for-byte empirical evaluation log; all benchmark tables, calibration deciles, and fairness checks.", "ML Specialists & Evaluators", "10 min"],
            ["docs/USER_TEST.md", "Complete user study protocol: 11 tasks, SUS questionnaire, Colquitt justice survey, lab procedure.", "HCI & Usability Researchers", "10 min"],
            ["docs/THESIS_GUIDE.md", "Academic framing: Research questions (RQ1-RQ4), methodology justification, literature citations.", "Report Authors & Dissertation Leads", "20 min"],
            ["docs/LIMITATIONS.md", "Critical evaluation of synthetic data constraints, department disparities, and future improvements.", "Defense Prep & Examiners", "8 min"],
            ["docs/DATA_MODEL.md", "Entity relationship descriptions, database tables, audit chain schemas, and foreign keys.", "Database & Backend Engineers", "10 min"],
            ["docs/BACKUPS.md", "Automated database backup routines, point-in-time recovery, and operational integrity.", "System Administrators", "5 min"]
        ],
        [2400, 4200, 1900, 1000]
    )

    # Build outputs
    out_root = "Project Documentation Index.docx"
    out_docs = os.path.join("docs", "Project Documentation Index.docx")
    doc.build(out_root)
    shutil.copyfile(out_root, out_docs)
    print(f"Copied to: {out_docs}")

if __name__ == "__main__":
    generate_meritlens_guide()
