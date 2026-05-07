import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

def generate_filled_omr_sheet(num_questions=10, filename="prova_preenchida_teste.pdf"):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    margin = 15 * mm
    marker_size = 10 * mm
    
    def draw_markers():
        c.setFillColorRGB(0, 0, 0)
        c.rect(margin, height - margin - marker_size, marker_size, marker_size, fill=1)
        c.rect(width - margin - marker_size, height - margin - marker_size, marker_size, marker_size, fill=1)
        c.rect(margin, margin, marker_size, marker_size, fill=1)
        c.rect(width - margin - marker_size, margin, marker_size, marker_size, fill=1)
        
    draw_markers()
    
    # --- CABEÇALHO ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin + marker_size + 10*mm, height - margin - 5*mm, "Folha de Respostas OMR (PREENCHIDA)")
    
    c.setFont("Helvetica", 10)
    header_y = height - margin - 15*mm
    c.drawString(margin + marker_size + 10*mm, header_y, f"Professor: Mestre dos Magos")
    c.drawString(margin + marker_size + 90*mm, header_y, f"Disciplina: Python Avançado")
    c.drawString(margin + marker_size + 10*mm, header_y - 6*mm, f"Colégio: Escola de Magia")
    c.drawString(margin + marker_size + 90*mm, header_y - 6*mm, f"Turma: 105")
    
    c.setLineWidth(1)
    c.line(margin, header_y - 12*mm, width - margin, header_y - 12*mm)
    
    # --- DADOS DO ALUNO ---
    student_data_y = header_y - 20*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, student_data_y, "Nome do Aluno: ALUNO TESTE DA SILVA")
    c.setLineWidth(0.5)
    c.line(margin + 35*mm, student_data_y - 1*mm, width - margin, student_data_y - 1*mm)

    # --- MATRIZ DE ID ---
    id_start_y = student_data_y - 12*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, id_start_y, "ID do Aluno (2 dígitos):")
    c.drawString(margin + 95*mm, id_start_y, "ID da Turma (3 dígitos):")
    
    c.setFont("Helvetica", 10)
    bubble_radius = 3.5 * mm
    
    student_id_fills = [4, 2] # ID = 42
    for row in range(2):
        row_y = id_start_y - 8*mm - (row * 9*mm)
        for num in range(10):
            cx = margin + num * 8.5*mm + bubble_radius
            cy = row_y
            fill = 1 if num == student_id_fills[row] else 0
            c.circle(cx, cy, bubble_radius, stroke=1, fill=fill)
            if not fill:
                c.drawCentredString(cx, cy - 1*mm, str(num))

    class_id_fills = [1, 0, 5] # Turma 105
    for row in range(3):
        row_y = id_start_y - 8*mm - (row * 9*mm)
        for num in range(10):
            cx = margin + 95*mm + num * 8.5*mm + bubble_radius
            cy = row_y
            fill = 1 if num == class_id_fills[row] else 0
            c.circle(cx, cy, bubble_radius, stroke=1, fill=fill)
            if not fill:
                c.drawCentredString(cx, cy - 1*mm, str(num))
            
    c.line(margin, id_start_y - 33*mm, width - margin, id_start_y - 33*mm)
            
    # --- MATRIZ DE QUESTÕES ---
    q_start_y = id_start_y - 40*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, q_start_y, "Matriz de Questões:")
    
    num_cols = 1 if num_questions <= 10 else 2
    q_per_col = 10
    b_radius = 3.5 * mm
    r_spacing = 9 * mm
    c_spacing = 9 * mm
    f_size = 10
    bf_size = 8
    txt_offset = 1 * mm
    x_offset = 12 * mm
        
    col_width = (width - 2*margin) / num_cols
    alt_letters = ["A", "B", "C", "D", "E"]
    num_alts = 5
        
    c.setFont("Helvetica", f_size)
    random.seed(42) # Para ser sempre o mesmo preenchimento
        
    for i in range(num_questions):
        col = i // q_per_col
        row = i % q_per_col
        
        base_x = margin + col * col_width
        base_y = q_start_y - 10*mm - row * r_spacing
        
        c.setFont("Helvetica", f_size)
        c.drawString(base_x, base_y - 1*mm, f"{i+1:02d}.")
        
        filled_idx = random.randint(0, num_alts - 1) # Escolhe uma letra aleatória
        
        for j in range(num_alts):
            cx = base_x + x_offset + j * c_spacing
            cy = base_y
            fill = 1 if j == filled_idx else 0
            c.circle(cx, cy, b_radius, stroke=1, fill=fill)
            if not fill:
                c.setFont("Helvetica", bf_size)
                c.drawCentredString(cx, cy - txt_offset, alt_letters[j])
                c.setFont("Helvetica", f_size)

    c.showPage()
    c.save()

if __name__ == "__main__":
    generate_filled_omr_sheet(10, "prova_preenchida_teste.pdf")
    print("PDF gerado com sucesso!")
