import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def generate_omr_sheet(num_questions, professor_name, school_name, class_name, subject_name):
    """
    Gera um gabarito em formato PDF com os marcadores de ancoragem, 
    cabeçalho, matriz de ID e matriz de respostas.
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    width, height = A4
    
    # Configurações de layout
    margin = 15 * mm
    marker_size = 10 * mm
    
    def draw_markers():
        c.setFillColorRGB(0, 0, 0)
        # Top-Left
        c.rect(margin, height - margin - marker_size, marker_size, marker_size, fill=1)
        # Top-Right
        c.rect(width - margin - marker_size, height - margin - marker_size, marker_size, marker_size, fill=1)
        # Bottom-Left
        c.rect(margin, margin, marker_size, marker_size, fill=1)
        # Bottom-Right
        c.rect(width - margin - marker_size, margin, marker_size, marker_size, fill=1)
        
    draw_markers()
    
    # --- CABEÇALHO ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin + marker_size + 10*mm, height - margin - 5*mm, "Folha de Respostas")
    
    c.setFont("Helvetica", 10)
    header_y = height - margin - 15*mm
    c.drawString(margin + marker_size + 10*mm, header_y, f"Professor: {professor_name}")
    c.drawString(margin + marker_size + 90*mm, header_y, f"Disciplina: {subject_name}")
    c.drawString(margin + marker_size + 10*mm, header_y - 6*mm, f"Colégio: {school_name}")
    
    # Linha separadora
    c.setLineWidth(1)
    c.line(margin, header_y - 12*mm, width - margin, header_y - 12*mm)
    
    # --- DADOS DO ALUNO ---
    student_data_y = header_y - 20*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, student_data_y, "Nome do Aluno:")
    c.setLineWidth(0.5)
    c.line(margin + 35*mm, student_data_y - 1*mm, width - margin, student_data_y - 1*mm)

    # --- MATRIZ DE ID ---
    id_start_y = student_data_y - 12*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, id_start_y, "ID do Aluno (2 dígitos):")
    c.drawString(margin + 95*mm, id_start_y, "ID da Turma (3 dígitos):")
    
    c.setFont("Helvetica", 10)
    bubble_radius = 3.5 * mm
    
    # Desenha ID do Aluno (2 linhas)
    for row in range(2):
        row_y = id_start_y - 8*mm - (row * 9*mm)
        for num in range(10):
            cx = margin + num * 8.5*mm + bubble_radius
            cy = row_y
            c.setStrokeColorRGB(0, 0, 0)
            c.circle(cx, cy, bubble_radius, stroke=1, fill=0)
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.6, 0.6, 0.6) # Cinza claro
            c.drawCentredString(cx, cy - 0.5*mm, str(num))

    # Desenha ID da Turma (3 linhas)
    for row in range(3):
        row_y = id_start_y - 8*mm - (row * 9*mm)
        for num in range(10):
            cx = margin + 95*mm + num * 8.5*mm + bubble_radius
            cy = row_y
            c.setStrokeColorRGB(0, 0, 0)
            c.circle(cx, cy, bubble_radius, stroke=1, fill=0)
            c.setFont("Helvetica", 5)
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.drawCentredString(cx, cy - 0.5*mm, str(num))
            
    # Linha separadora
    c.line(margin, id_start_y - 33*mm, width - margin, id_start_y - 33*mm)
            
    # --- MATRIZ DE QUESTÕES ---
    q_start_y = id_start_y - 40*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, q_start_y, "Matriz de Questões:")
    
    if num_questions <= 20:
        num_cols = 1 if num_questions <= 10 else 2
        q_per_col = 10
        b_radius = 3.5 * mm
        r_spacing = 9 * mm
        c_spacing = 9 * mm
        f_size = 10
        bf_size = 8
        txt_offset = 1 * mm
        x_offset = 12 * mm
    else:
        num_cols = 3
        # Se for até 30, mantém 10 por coluna. Se for maior, distribui igualmente.
        q_per_col = 10 if num_questions <= 30 else (num_questions + num_cols - 1) // num_cols
        b_radius = 2.5 * mm
        r_spacing = 7 * mm
        c_spacing = 7 * mm
        f_size = 9
        bf_size = 7
        txt_offset = 0.8 * mm
        x_offset = 9 * mm
        
    col_width = (width - 2*margin) / num_cols
    
    alt_letters = ["A", "B", "C", "D", "E"]
    num_alts = 5
        
    c.setFont("Helvetica", f_size)
        
    for i in range(num_questions):
        col = i // q_per_col
        row = i % q_per_col
        
        base_x = margin + col * col_width
        base_y = q_start_y - 10*mm - row * r_spacing
        
        # Paginação simples se passar do limite inferior
        if base_y < margin + marker_size + 10*mm:
            c.showPage()
            draw_markers()
            q_start_y = height - margin - 20*mm
            base_y = q_start_y - 10*mm - row * r_spacing

        c.setFont("Helvetica", f_size)
        c.drawString(base_x, base_y - 1*mm, f"{i+1:02d}.")
        
        for j in range(num_alts):
            cx = base_x + x_offset + j * c_spacing
            cy = base_y
            c.setStrokeColorRGB(0, 0, 0)
            c.circle(cx, cy, b_radius, stroke=1, fill=0)
            c.setFont("Helvetica", bf_size - 2)
            c.setFillColorRGB(0.6, 0.6, 0.6)
            c.drawCentredString(cx, cy - (txt_offset * 0.5), alt_letters[j])
            c.setFont("Helvetica", f_size)

    c.showPage()
    c.save()
    packet.seek(0)
    return packet
