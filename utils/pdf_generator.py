# utils/pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os
import uuid

def generate_lecturer_verification_pdf(lecturer_data, verification_code, expires_at):
    """Generate a professional PDF with verification code"""
    
    # Create filename and path
    filename = f"lecturer_verification_{lecturer_data['staff_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join('static', 'pdfs', filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filepath, 
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Story container
    story = []
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#10b981'),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#374151'),
        spaceAfter=6,
        leading=16
    )
    
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontSize=20,
        textColor=colors.HexColor('#059669'),
        alignment=TA_CENTER,
        backColor=colors.HexColor('#ecfdf5'),
        borderPadding=15,
        spaceAfter=20,
        fontName='Courier-Bold'
    )
    
    # Header
    story.append(Paragraph("SUBMITA", title_style))
    story.append(Paragraph("Lecturer Verification Code", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Date
    story.append(Paragraph(f"<b>Date Generated:</b> {datetime.now().strftime('%B %d, %Y at %H:%M')}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Greeting
    story.append(Paragraph(f"Dear <b>{lecturer_data['full_name']}</b>,", heading_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "Congratulations! Your request to register as a lecturer on the Submita platform has been approved. "
        "Please find below your unique verification code.", 
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Verification Code Box
    story.append(Paragraph("<b>Your Verification Code:</b>", normal_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(f"<b>{verification_code}</b>", code_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Lecturer Details Table
    data = [
        ['Staff ID:', lecturer_data['staff_id']],
        ['Full Name:', lecturer_data['full_name']],
        ['Email:', lecturer_data['email']],
        ['Department:', lecturer_data['department']],
        ['College:', lecturer_data.get('college', 'Not specified')],
    ]
    
    table = Table(data, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Important Information
    story.append(Paragraph("<b>Important Information:</b>", heading_style))
    info_items = [
        f"• This code will expire on: <b>{expires_at.strftime('%B %d, %Y at %H:%M')}</b>",
        "• The code can only be used once",
        "• Keep this code confidential - do not share with anyone",
        "• You will need this code to complete your registration",
        "• After registration, you will have full access to the platform"
    ]
    
    for item in info_items:
        story.append(Paragraph(item, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Instructions
    story.append(Paragraph("<b>How to Register:</b>", heading_style))
    story.append(Paragraph("1. Visit the Submita registration page", normal_style))
    story.append(Paragraph("2. Select 'Lecturer' as your role", normal_style))
    story.append(Paragraph("3. Enter your details", normal_style))
    story.append(Paragraph("4. Enter the verification code above", normal_style))
    story.append(Paragraph("5. Complete the registration form", normal_style))
    story.append(Paragraph("6. You will be automatically logged in", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Security Notice
    security_notice = Paragraph(
        "<i>🔒 Security Notice: This is an official verification document from Submita. "
        "If you did not request this verification, please contact your system administrator immediately.</i>",
        ParagraphStyle('SecurityNotice', parent=normal_style, textColor=colors.HexColor('#ef4444'), alignment=TA_LEFT)
    )
    story.append(security_notice)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    story.append(Paragraph("-" * 70, normal_style))
    story.append(Spacer(1, 0.1*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=9,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )
    story.append(Paragraph("© 2024 Submita - University Assignment Management System", footer_style))
    story.append(Paragraph("This is an automated message. Please do not reply to this document.", footer_style))
    
    # Build PDF
    doc.build(story)
    
    return filepath