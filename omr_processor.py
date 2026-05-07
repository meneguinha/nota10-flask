import cv2
import numpy as np

def order_points(pts):
    # inicializa uma lista de coordenadas que serão ordenadas:
    # topo-esquerda, topo-direita, baixo-direita, baixo-esquerda
    rect = np.zeros((4, 2), dtype="float32")

    # a soma do topo-esquerda será a menor, e a da baixo-direita a maior
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    # a diferença para topo-direita será a menor, e baixo-esquerda a maior
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect

def process_omr_image(image_bytes, num_questions, alternatives_format, answer_key, max_score=10.0):
    """
    Processa a imagem enviada, alinha a perspectiva pelos marcadores,
    extrai o ID do aluno, ID da turma e corrige as questões com base no gabarito.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Converte para tons de cinza e aplica threshold adaptativo
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)

    # Usar RETR_LIST para achar contornos mesmo se houver uma borda externa
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    markers = []
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        
        if len(approx) == 4:
            _, _, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            area = w * h
            
            # Os marcadores têm 10x10mm. Isso dá uma área média razoável, eliminando a página inteira ou ruídos.
            if 0.8 <= aspect_ratio <= 1.2 and 500 < area < 50000:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    markers.append((area, cX, cY))
                    
    # Remove marcadores duplicados (as vezes acha a borda interna e externa do mesmo quadrado)
    unique_markers = []
    for m in markers:
        is_duplicate = False
        for um in unique_markers:
            dist = np.sqrt((m[1]-um[1])**2 + (m[2]-um[2])**2)
            if dist < 20: 
                is_duplicate = True
                break
        if not is_duplicate:
            unique_markers.append(m)
            
    # Precisamos de pelo menos 4 marcadores
    if len(unique_markers) < 4:
        return {"error": f"Encontrados apenas {len(unique_markers)} marcadores nos cantos. Verifique se a foto pegou a página toda."}, img
    
    # Pega os 4 maiores quadrados encontrados (assumindo que são as âncoras e não caixas de texto acidentais)
    unique_markers.sort(key=lambda x: x[0], reverse=True)
    top_4_markers = unique_markers[:4]
    
    pts = np.array([[m[1], m[2]] for m in top_4_markers], dtype="float32")
    rect = order_points(pts)
    
    # ----- DIMENSÕES ALVO (A4 em Alta Resolução) -----
    pdf_width = 595.27
    pdf_height = 841.89
    scale = 3.0 # Fator de escala para manter a qualidade alta ao fazer warp
    width = int(pdf_width * scale)
    height = int(pdf_height * scale)
    
    mm = 2.83465 * scale
    margin = 15 * mm
    marker_size = 10 * mm
    
    # Coordenadas esperadas dos centros dos marcadores na imagem transformada
    dst_pts = np.array([
        [margin + marker_size/2, margin + marker_size/2], # TL
        [width - margin - marker_size/2, margin + marker_size/2], # TR
        [width - margin - marker_size/2, height - margin - marker_size/2], # BR
        [margin + marker_size/2, height - margin - marker_size/2] # BL
    ], dtype="float32")
    
    # Matriz de transformação de perspectiva
    transform_matrix = cv2.getPerspectiveTransform(rect, dst_pts)
    warped_gray = cv2.warpPerspective(gray, transform_matrix, (width, height))
    warped_color = cv2.warpPerspective(img, transform_matrix, (width, height))
    
    # Binarização para ler as bolhas (Invertido: bolhas preenchidas ficam brancas)
    thresh = cv2.threshold(warped_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    # ------ LÓGICA DE EXTRAÇÃO DE COORDENADAS (Mapeamento 1:1 com omr_generator) ------
    mm_pt = 2.83465
    margin_pt = 15 * mm_pt
    header_y_pt = pdf_height - margin_pt - 15*mm_pt
    student_data_y_pt = header_y_pt - 20*mm_pt
    id_start_y_pt = student_data_y_pt - 12*mm_pt
    
    def to_cv(x_pt, y_pt):
        # Converte pontos do PDF (origem inferior esquerda) para pixels OpenCV (origem superior esquerda)
        return int(x_pt * scale), int((pdf_height - y_pt) * scale)
        
    results = {
        "student_id": "",
        "class_id": "",
        "answers": {},
        "correct": 0,
        "wrong": 0,
        "score": 0.0
    }
    
    # 1. Extrair ID do Aluno
    for row in range(2):
        row_y_pt = id_start_y_pt - 8*mm_pt - (row * 9*mm_pt)
        best_num = ""
        max_fill = 0
        for num in range(10):
            cx_pt = margin_pt + num * 8.5*mm_pt + 3.5*mm_pt
            cx, cy = to_cv(cx_pt, row_y_pt)
            r = int(2.5 * mm_pt * scale) # Raio de leitura
            roi = thresh[cy-r:cy+r, cx-r:cx+r]
            fill = cv2.countNonZero(roi)
            
            if fill > max_fill:
                max_fill = fill
                best_num = str(num)
        
        # Reduzido para 30% pois marcações de caneta mais fracas podem não preencher todo o ROI,
        # e o texto impresso no fundo ocupa menos de 10% da área.
        if max_fill < ( (r*2)**2 ) * 0.30:
            best_num = ""
            
        results["student_id"] += best_num
        
    # 2. Extrair ID da Turma
    for row in range(3):
        row_y_pt = id_start_y_pt - 8*mm_pt - (row * 9*mm_pt)
        best_num = ""
        max_fill = 0
        for num in range(10):
            cx_pt = margin_pt + 95*mm_pt + num * 8.5*mm_pt + 3.5*mm_pt
            cx, cy = to_cv(cx_pt, row_y_pt)
            r = int(2.5 * mm_pt * scale)
            roi = thresh[cy-r:cy+r, cx-r:cx+r]
            fill = cv2.countNonZero(roi)
            
            if fill > max_fill:
                max_fill = fill
                best_num = str(num)
        
        # Reduzido para 30% também para a Turma.
        if max_fill < ( (r*2)**2 ) * 0.30:
            best_num = ""
            
        results["class_id"] += best_num
        
    # 3. Extrair Questões
    q_start_y_pt = id_start_y_pt - 40*mm_pt
    if num_questions <= 20:
        num_cols = 1 if num_questions <= 10 else 2
        q_per_col = 10
        r_spacing_pt = 9 * mm_pt
        c_spacing_pt = 9 * mm_pt
        x_offset_pt = 12 * mm_pt
    else:
        num_cols = 3
        q_per_col = 10 if num_questions <= 30 else (num_questions + num_cols - 1) // num_cols
        r_spacing_pt = 7 * mm_pt
        c_spacing_pt = 7 * mm_pt
        x_offset_pt = 9 * mm_pt
        
    col_width_pt = (pdf_width - 2*margin_pt) / num_cols
    alt_letters = ["A", "B", "C", "D", "E"]
    num_alts = 5
    if alternatives_format == "A-C": num_alts = 3
    elif alternatives_format == "A-D": num_alts = 4
    
    for i in range(num_questions):
        col = i // q_per_col
        row = i % q_per_col
        
        base_x_pt = margin_pt + col * col_width_pt
        base_y_pt = q_start_y_pt - 10*mm_pt - row * r_spacing_pt
        
        marked_alts = []
        best_alt_idx = -1
        max_fill = 0
        
        # Coleta de preenchimento
        for j in range(num_alts):
            cx_pt = base_x_pt + x_offset_pt + j * c_spacing_pt
            cx, cy = to_cv(cx_pt, base_y_pt)
            r = int(2.5 * mm_pt * scale)
            roi = thresh[cy-r:cy+r, cx-r:cx+r]
            fill = cv2.countNonZero(roi)
            total_pixels = roi.shape[0] * roi.shape[1]
            
            # Se for mais que 30% branco no threshold (bolha pintada), consideramos marcada
            if fill > total_pixels * 0.30:
                marked_alts.append(alt_letters[j])
                
        # Validação (Nula, Branca ou Válida)
        if len(marked_alts) == 1:
            ans = marked_alts[0]
        elif len(marked_alts) > 1:
            ans = "ANULADA"
        else:
            ans = ""
                
        results["answers"][i+1] = ans
        
        # Correção e feedback visual
        official = answer_key.get(i+1, "")
        if ans == "ANULADA" or ans == "":
            color = (0, 165, 255) # Laranja para anulada/branco
        elif ans == official:
            results["correct"] += 1
            color = (0, 255, 0) # Verde
        else:
            results["wrong"] += 1
            color = (0, 0, 255) # Vermelho
            
        # Desenha círculo de correção apenas na resposta que o aluno marcou (ou na que ele deveria marcar se errou?)
        # Vamos desenhar o círculo na resposta oficial como um contorno fino
        if official in alt_letters:
            idx = alt_letters.index(official)
            cx_pt = base_x_pt + x_offset_pt + idx * c_spacing_pt
            cx, cy = to_cv(cx_pt, base_y_pt)
            cv2.circle(warped_color, (cx, cy), r+4, (255, 255, 0), 2) # Círculo Ciano/Amarelo no correto
            
        # E pinta a bolinha que ele marcou com verde/vermelho
        if ans in alt_letters:
            idx = alt_letters.index(ans)
            cx_pt = base_x_pt + x_offset_pt + idx * c_spacing_pt
            cx, cy = to_cv(cx_pt, base_y_pt)
            cv2.circle(warped_color, (cx, cy), r, color, 4)
            
    # Calcula nota com base na nota máxima
    if num_questions > 0:
        results["score"] = (results["correct"] / num_questions) * max_score
        
    return results, warped_color
