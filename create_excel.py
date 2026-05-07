import pandas as pd

data = {
    'ID Aluno': ['01', '02', '03'],
    'ID Turma': ['001', '002', '001'],
    'Nome': ['João Silva', 'Maria Souza', 'Carlos Pereira'],
    'Email': ['joao@emailfalso.com', 'maria@emailfalso.com', 'carlos@emailfalso.com'],
    'Nota 1': [8.5, 9.0, 7.5],
    'Nota 2': [7.0, 8.5, 8.0]
}

df = pd.DataFrame(data)
df.to_excel('alunos_teste.xlsx', index=False)
print("Arquivo alunos_teste.xlsx criado com sucesso!")
