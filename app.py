from flask import Flask, render_template, request, redirect, url_for, flash
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
import json
import re

app = Flask(__name__)
app.secret_key = 'd4b35yt309ggtr'

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///suggestions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo de banco de dados para as sugestões
class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    su_dados = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

# Função de sanitização centralizada
def sanitize_input(input_str):
    "Sanitiza strings, removendo scripts e caracteres perigosos"
    if not input_str:
        return None
    sem_tags = re.sub(r'<.*?>', '', input_str)  # Remove tags HTML
    return re.sub(r"[^a-zA-Z0-9\sáéíóúÁÉÍÓÚàèìòùÀÈÌÒÙãõÃÕâêîôûÂÊÎÔÛçÇ.,!?@#$%&*()\-_=+;:'\"/]", '', sem_tags)

class PetFilter:
    def __init__(self, json_file):
        with open(json_file, 'r', encoding='utf-8') as file:
            self.data = json.load(file)
    
    def filter_pets(self, category=None, raca=None, comida_permitida=None, 
        curiosidade_chave=None, exercicios_chave=None):
        results = []        
        categories = self.data.keys() if not category else [category]
    
        raca_filtro = str(raca).lower() if raca else None
        comida_filtro = [str(c).lower() for c in comida_permitida] if comida_permitida else None
        curiosidade_filtro = str(curiosidade_chave).lower()  if curiosidade_chave else None
        exercicios_filtro = str(exercicios_chave).lower() if exercicios_chave else None
    
        for cat in categories:
            if cat in self.data:
                for pet in self.data[cat]:
                    if raca_filtro and pet.get('raca', '').lower() != raca_filtro:
                        continue
                 
                    if comida_filtro:
                        comidas_pet = [str(c).lower() for c in pet.get('comida_permitida', [])]
                        if not any(
                            any(comida in item for item in comidas_pet)
                            for comida in comida_filtro
                        ):
                            continue

                    if curiosidade_filtro:             
                        curiosidades = ' '.join(pet.get('curiosidades', [])).lower()\
                            if isinstance(pet.get('curiosidades'), list) \
                            else str(pet.get('curiosidades', '')).lower()
                        if curiosidade_filtro not in curiosidades:
                            continue

                    if exercicios_filtro:
                       exercicios = str(pet.get('exercicios', '')).lower()
                       if exercicios_filtro not in exercicios:
                            continue
                        
                    results.append({
                        'categoria': cat.capitalize(),
                         **pet
                    })

        return results
    
# inicializa o filtro com arquivo JSON
pet_filter = PetFilter('data.json')

@app.route('/')
def index():
    categorias = list(pet_filter.data.keys())
    return render_template('index.html', categorias=categorias)

@app.route('/submit_suggestion', methods=['POST'])
def submit_suggestion():
    # sanitização customizada
    suggestion_raw = request.form.get('suggestion')
    suggestion_texto = sanitize_input(suggestion_raw.strip()) if suggestion_raw else ''

    if not suggestion_texto:
        flash("A sugestão não pode estar vazia!", "error")
        return redirect(url_for('index'))
    
    if len(suggestion_texto) > 500:
        flash("A sugestão não pode ter mais de 500 caracteres!", "error")
        return redirect(url_for('index'))

    new_suggestion = Suggestion(su_dados=suggestion_texto)
    db.session.add(new_suggestion)
    db.session.commit()

    flash("Sugestão enviada com sucesso!", "success")
    return redirect(url_for('index'))

@app.route('/teste_imagem')
def teste_imagem():
    return f'<img src="{url_for("static", filename="images/oriental-shorthair.jpeg")}">'

@app.route('/search')
def search():
    sanitized_args = {
        'categoria': sanitize_input(request.args.get('categoria')),
        'raca': sanitize_input(request.args.get('raca')),
        'comida_permitida': [sanitize_input(c) for c in request.args.getlist('comida_permitida')],
        'curiosidade': sanitize_input(request.args.get('curiosidade')),
        'exercicios': sanitize_input(request.args.get('exercicios')),
       
    }
    
    filters = {
        'category': sanitized_args['categoria'],
        'raca': sanitized_args['raca'],
        'comida_permitida': [c for c in sanitized_args['comida_permitida'] if c],
        'curiosidade_chave': sanitized_args['curiosidade'],
        'exercicios_chave': sanitized_args['exercicios'],
       
    }

    resultados = pet_filter.filter_pets(**filters)
    return render_template('search.html', resultados=resultados, filters=filters)

@app.context_processor
def inject_timezone():
    return {'BR_TZ': ZoneInfo("America/Sao_Paulo")}

@app.route('/suggestions')
def view_suggestions():
    suggestions = Suggestion.query.order_by(Suggestion.timestamp.desc()).all()
    
    return render_template('suggestions.html', suggestions=suggestions)
 
# Cria o banco de dados 
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5772)