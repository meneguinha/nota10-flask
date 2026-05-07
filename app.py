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
import shutil
import threading
from flask import Flask, render_template, request, send_file, jsonify
from omr_generator import generate_omr_sheet
from omr_processor import process_omr_image

app = Flask(__name__)
RESULTS_DIR = 'results'
os.makedirs(RESULTS_DIR, exist_ok=True)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    data = request.get_json(silent=True) or {}
    result_id = data.get('result_id')
    if result_id:
        dir_path = os.path.join(RESULTS_DIR, result_id)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
            except Exception:
                pass
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


tasks_progress = {}

def process_in_background(task_id, gabarito_oficial, nota_maxima, df_class, uploaded_files_data):
    try:
        tasks_progress[task_id] = {"status": "processing", "progress": 0, "total": 0, "current": 0, "has_class_list": False}
        
        total_items = 0
        for f in uploaded_files_data:
            if f['filename'].lower().endswith('.pdf'):
                doc = fitz.open(stream=f['bytes'], filetype="pdf")
                total_items += len(doc)
            else:
                total_items += 1
                
        tasks_progress[task_id]["total"] = total_items
        
        result_folder = os.path.join(RESULTS_DIR, task_id)
        os.makedirs(result_folder, exist_ok=True)
        
        all_results = []
        zip_path = os.path.join(result_folder, 'imagens.zip')
        
        gabarito_int_keys = {int(k): v for k, v in gabarito_oficial.items()}
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for f in uploaded_files_data:
                filename = f['filename']
                file_bytes = f['bytes']
                
                if filename.lower().endswith('.pdf'):
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(dpi=200)
                        img_bytes = pix.tobytes("png")
                        
                        results, warped_img = process_omr_image(
                            image_bytes=img_bytes,
                            num_questions=len(gabarito_int_keys),
                            alternatives_format="A-E",
                            answer_key=gabarito_int_keys,
                            max_score=nota_maxima
                        )
                        
                        del img_bytes
                        del pix
                        
                        if "error" not in results:
                            row_data = {
                                "Arquivo": filename,
                                "Página": page_num + 1,
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
                                img_name = f"{filename}_pag_{page_num+1}_turma_{results['class_id']}_id_{results['student_id']}.jpg"
                                zip_file.writestr("imagens/" + img_name, img_buf.tobytes())
                            del resized_img
                            del img_buf
                        
                        del warped_img
                        tasks_progress[task_id]["current"] += 1
                        tasks_progress[task_id]["progress"] = int((tasks_progress[task_id]["current"] / total_items) * 100)
                        
                else:
                    results, warped_img = process_omr_image(
                        image_bytes=file_bytes,
                        num_questions=len(gabarito_int_keys),
                        alternatives_format="A-E",
                        answer_key=gabarito_int_keys,
                        max_score=nota_maxima
                    )
                    
                    if "error" not in results:
                        row_data = {
                            "Arquivo": filename,
                            "Página": 1,
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
                            img_name = f"{filename}_turma_{results['class_id']}_id_{results['student_id']}.jpg"
                            zip_file.writestr("imagens/" + img_name, img_buf.tobytes())
                        del resized_img
                        del img_buf
                    del warped_img
                    tasks_progress[task_id]["current"] += 1
                    tasks_progress[task_id]["progress"] = int((tasks_progress[task_id]["current"] / total_items) * 100)

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

        excel_path = os.path.join(result_folder, 'relatorio.xlsx')
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados Completos')
        
        has_class_list = False
        if df_class_with_grades is not None:
            has_class_list = True
            lista_path = os.path.join(result_folder, 'lista.xlsx')
            with pd.ExcelWriter(lista_path, engine='openpyxl') as writer:
                df_class_with_grades.to_excel(writer, index=False, sheet_name='Lista com Notas')
            
        tasks_progress[task_id]["has_class_list"] = has_class_list
        tasks_progress[task_id]["status"] = "completed"

    except Exception as e:
        tasks_progress[task_id]["status"] = "error"
        tasks_progress[task_id]["error"] = str(e)


@app.route('/process_exams', methods=['POST'])
def process_exams():
    try:
        gabarito_oficial = json.loads(request.form.get('gabarito_oficial', '{}'))
        nota_maxima = float(request.form.get('nota_maxima', 10.0))
        
        if not gabarito_oficial:
            return jsonify({'error': 'Gabarito oficial não fornecido.'}), 400

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

        # Auto-cleanup old entries
        current_time = time.time()
        for folder_name in os.listdir(RESULTS_DIR):
            folder_path = os.path.join(RESULTS_DIR, folder_name)
            if os.path.isdir(folder_path):
                try:
                    if current_time - os.path.getmtime(folder_path) > 3600:
                        shutil.rmtree(folder_path)
                except Exception:
                    pass

        task_id = str(uuid.uuid4())
        
        uploaded_files_data = []
        for file in uploaded_files:
            uploaded_files_data.append({'filename': file.filename, 'bytes': file.read()})
            
        thread = threading.Thread(
            target=process_in_background, 
            args=(task_id, gabarito_oficial, nota_maxima, df_class, uploaded_files_data)
        )
        thread.start()

        return jsonify({
            'success': True,
            'task_id': task_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>')
def task_status(task_id):
    if task_id in tasks_progress:
        return jsonify(tasks_progress[task_id])
    return jsonify({"status": "not_found"}), 404

@app.route('/download/<result_id>/<file_type>')
def download_file(result_id, file_type):
    result_folder = os.path.join(RESULTS_DIR, result_id)
    if not os.path.exists(result_folder):
        return "Arquivo expirou ou não encontrado.", 404
        
    if file_type == 'relatorio':
        file_path = os.path.join(result_folder, 'relatorio.xlsx')
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name='relatorio_notas_omr.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif file_type == 'lista':
        file_path = os.path.join(result_folder, 'lista.xlsx')
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name='lista_alunos_com_notas.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif file_type == 'imagens':
        file_path = os.path.join(result_folder, 'imagens.zip')
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name='provas_corrigidas.zip', mimetype='application/zip')
    
    return "Tipo de arquivo inválido ou não encontrado.", 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
