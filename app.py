import os
import re
import fitz
import pandas as pd
import io
import zipfile
import cv2
import json
import uuid
import time
from flask import Flask, render_template, request, send_file, jsonify
from omr_generator import generate_omr_sheet
from omr_processor import process_omr_image

app = Flask(__name__)
RESULTS_CACHE = {}

@app.route('/cleanup', methods=['POST'])
def cleanup():
    data = request.get_json(silent=True) or {}
    result_id = data.get('result_id')
    if result_id and result_id in RESULTS_CACHE:
        del RESULTS_CACHE[result_id]
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_matrix', methods=['POST'])
def generate_matrix():
    data = request.form
    professor_name = data.get('professor_name', '')
    school_name = data.get('school_name', '')
    subject_name = data.get('subject_name', '')
    num_questions = int(data.get('num_questions', 10))

    pdf_packet = generate_omr_sheet(
        num_questions=num_questions,
        professor_name=professor_name,
        school_name=school_name,
        class_name="",
        subject_name=subject_name
    )
    
    return send_file(
        pdf_packet,
        as_attachment=True,
        download_name=f"matriz_{subject_name.lower().replace(' ', '_')}.pdf",
        mimetype='application/pdf'
    )

@app.route('/process_exams', methods=['POST'])
def process_exams():
    try:
        # Parse official answer key
        gabarito_oficial = json.loads(request.form.get('gabarito_oficial', '{}'))
        nota_maxima = float(request.form.get('nota_maxima', 10.0))
        
        if not gabarito_oficial:
            return jsonify({'error': 'Gabarito oficial não fornecido.'}), 400

        # Parse class list if uploaded
        class_list_file = request.files.get('class_list_file')
        df_class = None
        if class_list_file and class_list_file.filename:
            if class_list_file.filename.lower().endswith(".csv"):
                df_class = pd.read_csv(class_list_file)
            else:
                df_class = pd.read_excel(class_list_file)
                
            def normalize_col_name(col):
                col_normalized = str(col).lower().replace("_", " ").strip()
                if col_normalized == "id turma":
                    return "ID Turma"
                if col_normalized == "id aluno":
                    return "ID Aluno"
                return str(col).strip()
            
            df_class.columns = [normalize_col_name(c) for c in df_class.columns]
            df_class["ID Turma"] = df_class["ID Turma"].astype(str).str.strip()
            df_class["ID Aluno"]  = df_class["ID Aluno"].astype(str).str.strip()
            
        uploaded_files = request.files.getlist('exam_files')
        if not uploaded_files or not uploaded_files[0].filename:
            return jsonify({'error': 'Nenhum arquivo de prova enviado.'}), 400

        all_results = []
        images_zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(images_zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in uploaded_files:
                file_bytes = file.read()
                images_to_process = []
                
                if file.filename.lower().endswith('.pdf'):
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(dpi=200)
                        images_to_process.append(pix.tobytes("png"))
                else:
                    images_to_process.append(file_bytes)
                    
                for idx, img_bytes in enumerate(images_to_process):
                    # Keys in gabarito_oficial from json are strings, we need ints
                    gabarito_int_keys = {int(k): v for k, v in gabarito_oficial.items()}
                    results, warped_img = process_omr_image(
                        image_bytes=img_bytes,
                        num_questions=len(gabarito_int_keys),
                        alternatives_format="A-E",
                        answer_key=gabarito_int_keys,
                        max_score=nota_maxima
                    )
                    
                    if "error" not in results:
                        row_data = {
                            "Arquivo": file.filename,
                            "Página": idx + 1,
                            "ID Turma": results["class_id"],
                            "ID Aluno": results["student_id"],
                            "Acertos": results["correct"],
                            "Erros": results["wrong"],
                            "Nota": round(results["score"], 2)
                        }
                        for q_num, ans in results["answers"].items():
                            row_data[f"Q{q_num}"] = ans
                        all_results.append(row_data)
                        
                        resized_img = cv2.resize(warped_img, (0,0), fx=0.35, fy=0.35)
                        is_success, img_buf = cv2.imencode(".jpg", resized_img, [int(cv2.IMWRITE_JPEG_QUALITY), 55])
                        if is_success:
                            img_name = f"{file.filename}_pag_{idx+1}_turma_{results['class_id']}_id_{results['student_id']}.jpg"
                            zip_file.writestr("imagens/" + img_name, img_buf.tobytes())
        
        df = pd.DataFrame(all_results)
        
        df_class_with_grades = None
        if df_class is not None:
            def normalize_id_for_merge(val):
                val_str = str(val).strip()
                if val_str.endswith(".0"):
                    val_str = val_str[:-2]
                return str(int(val_str)) if val_str.isdigit() else val_str
                
            if not df.empty:
                df["_merge_turma"] = df["ID Turma"].apply(normalize_id_for_merge)
                df["_merge_aluno"] = df["ID Aluno"].apply(normalize_id_for_merge)
            else:
                df["_merge_turma"] = pd.Series(dtype='object')
                df["_merge_aluno"] = pd.Series(dtype='object')
                
            df_class["_merge_turma"] = df_class["ID Turma"].apply(normalize_id_for_merge)
            df_class["_merge_aluno"] = df_class["ID Aluno"].apply(normalize_id_for_merge)

            extra_cols = [c for c in df_class.columns if c not in ["ID Turma", "ID Aluno", "_merge_turma", "_merge_aluno"]]
            filtered_extra_cols = [c for c in extra_cols if "nome" in str(c).lower() or "email" in str(c).lower() or "e-mail" in str(c).lower()]
            
            if not df.empty:
                df = df.merge(df_class[["_merge_turma", "_merge_aluno"] + filtered_extra_cols],
                              on=["_merge_turma", "_merge_aluno"], how="left")
            else:
                for col in filtered_extra_cols:
                    df[col] = pd.Series(dtype='object')
                              
            if not df.empty:
                df_class_with_grades = df_class.merge(
                    df[["_merge_turma", "_merge_aluno", "Nota"]].drop_duplicates(subset=["_merge_turma", "_merge_aluno"]), 
                    on=["_merge_turma", "_merge_aluno"], 
                    how="left"
                )
            else:
                df_class_with_grades = df_class.copy()
                df_class_with_grades["Nota"] = pd.Series(dtype='object')
                
            df_class_with_grades.drop(columns=["_merge_turma", "_merge_aluno"], inplace=True)
            
            base_cols = ["Arquivo", "Página", "ID Turma", "ID Aluno"] + filtered_extra_cols
            remain_cols = [c for c in df.columns if c not in base_cols and c not in ["_merge_turma", "_merge_aluno"]]
            df = df[[c for c in base_cols + remain_cols if c in df.columns]]
            
            if "_merge_turma" in df.columns: df.drop(columns=["_merge_turma", "_merge_aluno"], inplace=True)


        # Auto-cleanup old entries (older than 1 hour)
        current_time = time.time()
        keys_to_delete = [k for k, v in RESULTS_CACHE.items() if current_time - v.get('timestamp', current_time) > 3600]
        for k in keys_to_delete:
            del RESULTS_CACHE[k]

        # Save to memory cache instead of ZIP
        result_id = str(uuid.uuid4())
        RESULTS_CACHE[result_id] = {'timestamp': current_time}
        
        # 1. Excel Relatorio
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados Completos')
        RESULTS_CACHE[result_id]['relatorio'] = excel_buffer.getvalue()
        
        # 2. Excel Class List (if exists)
        has_class_list = False
        if df_class_with_grades is not None:
            has_class_list = True
            excel_class_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_class_buffer, engine='openpyxl') as writer:
                df_class_with_grades.to_excel(writer, index=False, sheet_name='Lista com Notas')
            RESULTS_CACHE[result_id]['lista'] = excel_class_buffer.getvalue()
            
        # 3. Images ZIP
        RESULTS_CACHE[result_id]['imagens'] = images_zip_buffer.getvalue()

        return jsonify({
            'success': True,
            'result_id': result_id,
            'has_class_list': has_class_list
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<result_id>/<file_type>')
def download_file(result_id, file_type):
    if result_id not in RESULTS_CACHE:
        return "Arquivo expirou ou não encontrado.", 404
        
    data = RESULTS_CACHE[result_id]
    
    if file_type == 'relatorio':
        return send_file(io.BytesIO(data['relatorio']), as_attachment=True, download_name='relatorio_notas_omr.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif file_type == 'lista' and 'lista' in data:
        return send_file(io.BytesIO(data['lista']), as_attachment=True, download_name='lista_alunos_com_notas.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif file_type == 'imagens':
        return send_file(io.BytesIO(data['imagens']), as_attachment=True, download_name='provas_corrigidas.zip', mimetype='application/zip')
    
    return "Tipo de arquivo inválido", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
