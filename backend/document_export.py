import io
import logging
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

logger = logging.getLogger(__name__)


def generate_word_document(title: str, content: str, doc_type: str = "memo",
                           header_option: str = "", firm_name: str = "") -> bytes:
    """Generate a formatted Word document."""
    doc = Document()
    
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.18)
        section.right_margin = Cm(2.54)
    
    # Header option
    if header_option:
        header_para = doc.add_paragraph()
        header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header_run = header_para.add_run(header_option.upper())
        header_run.bold = True
        header_run.font.size = Pt(10)
    
    # Firm name
    if firm_name:
        firm_para = doc.add_paragraph()
        firm_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        firm_run = firm_para.add_run(firm_name)
        firm_run.bold = True
        firm_run.font.size = Pt(14)
    
    # Title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(title)
    title_run.bold = True
    title_run.font.size = Pt(14)
    title_para.space_after = Pt(12)
    
    doc.add_paragraph()  # spacing
    
    # Content - parse markdown-like headers
    para_num = 1
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            doc.add_paragraph()
            continue
        
        if line.startswith('### '):
            heading = doc.add_paragraph()
            heading_run = heading.add_run(line[4:].upper())
            heading_run.bold = True
            heading_run.font.size = Pt(12)
            heading.space_before = Pt(12)
        elif line.startswith('## '):
            heading = doc.add_paragraph()
            heading_run = heading.add_run(line[3:].upper())
            heading_run.bold = True
            heading_run.font.size = Pt(13)
            heading.space_before = Pt(12)
        elif line.startswith('# '):
            heading = doc.add_paragraph()
            heading_run = heading.add_run(line[2:].upper())
            heading_run.bold = True
            heading_run.font.size = Pt(14)
            heading.space_before = Pt(12)
        else:
            para = doc.add_paragraph()
            if doc_type in ["notice", "petition", "application"]:
                run = para.add_run(f"{para_num}. {line}")
                para_num += 1
            else:
                run = para.add_run(line)
            run.font.size = Pt(12)
    
    # Signature block
    doc.add_paragraph()
    doc.add_paragraph()
    sig = doc.add_paragraph()
    sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    sig_run = sig.add_run("_________________________")
    sig.add_run("\n")
    sig.add_run("Authorized Signatory")
    
    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_content(title: str, content: str, header_option: str = "",
                          watermark: str = "") -> str:
    """Generate HTML content for PDF conversion via WeasyPrint."""
    watermark_css = ""
    if watermark:
        watermark_css = f"""
        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 80px;
            color: rgba(0, 0, 0, 0.06);
            font-weight: bold;
            z-index: -1;
            pointer-events: none;
        }}"""
    
    header_html = ""
    if header_option:
        header_html = f'<div class="header-option">{header_option.upper()}</div>'
    
    # Convert markdown content to HTML
    html_content = content
    html_content = html_content.replace('\n### ', '\n<h3>')
    html_content = html_content.replace('\n## ', '\n<h2>')
    html_content = html_content.replace('\n# ', '\n<h1>')
    
    lines = html_content.split('\n')
    processed = []
    for line in lines:
        if line.startswith('<h3>'):
            processed.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('<h2>'):
            processed.append(f'<h2>{line[4:]}</h2>')
        elif line.startswith('<h1>'):
            processed.append(f'<h1>{line[4:]}</h1>')
        elif line.strip():
            processed.append(f'<p>{line}</p>')
        else:
            processed.append('<br/>')
    
    body_html = '\n'.join(processed)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{
        size: A4;
        margin: 2.54cm 2.54cm 2.54cm 3.18cm;
        @bottom-center {{
            content: counter(page);
            font-size: 10px;
        }}
    }}
    body {{
        font-family: 'Times New Roman', Times, serif;
        font-size: 12pt;
        line-height: 1.6;
        color: #000;
    }}
    h1 {{ font-size: 16pt; font-weight: bold; text-align: center; margin: 20pt 0 12pt; }}
    h2 {{ font-size: 14pt; font-weight: bold; margin: 16pt 0 8pt; }}
    h3 {{ font-size: 12pt; font-weight: bold; margin: 12pt 0 6pt; text-transform: uppercase; }}
    p {{ margin: 6pt 0; text-align: justify; }}
    .header-option {{
        text-align: right;
        font-weight: bold;
        font-size: 10pt;
        margin-bottom: 20pt;
    }}
    .title {{
        text-align: center;
        font-weight: bold;
        font-size: 14pt;
        margin: 20pt 0;
    }}
    {watermark_css}
</style>
</head>
<body>
{f'<div class="watermark">{watermark}</div>' if watermark else ''}
{header_html}
<div class="title">{title}</div>
{body_html}
</body>
</html>"""
    return html


def generate_pdf_bytes(title: str, content: str, header_option: str = "",
                        watermark: str = "") -> bytes:
    """Generate PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML
        html_str = generate_pdf_content(title, content, header_option, watermark)
        pdf_bytes = HTML(string=html_str).write_pdf()
        return pdf_bytes
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return b""
