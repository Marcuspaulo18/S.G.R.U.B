import os
import io
import numpy as np
from PIL import Image
from ultralytics import YOLO
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import image_dataset_from_directory
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GlobalAveragePooling2D, Dropout, Dense, Rescaling, RandomRotation, \
    RandomTranslation, RandomFlip, RandomZoom
from tensorflow.keras.optimizers import Adam
import kagglehub
from kagglehub.config import set_kaggle_credentials
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
from tensorflow.keras.preprocessing import image
from transformers import pipeline
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '1'
modelodiretorio = None
diretoriodataset = None
MODELO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modelo_sgrub.keras')

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

KAGGLE_USERNAME = "theonlymp"
KAGGLE_KEY = "KGAT_7e0278abb8b7de1e1975b0152bdce9a4"



def obterdiretorio():
    global diretoriodataset
    if diretoriodataset is None:
        set_kaggle_credentials(KAGGLE_USERNAME, KAGGLE_KEY)
        diretoriodataset = kagglehub.dataset_download("theonlymp/sgrubdataset")
    return diretoriodataset


def treinarmodelo(epochs=10, batch_size=64):  # 2. BATCH SIZE AUMENTADO PARA 64 (Mais rápido na CPU)

    diretoriodataset = obterdiretorio()
    classes = os.path.join(diretoriodataset, "dataset_bioplastico")
    AUTOTUNE = tf.data.AUTOTUNE

    treinamento = image_dataset_from_directory(
        classes,
        validation_split = 0.2,
        subset = "training",
        seed = 123,
        image_size = (224, 224),
        batch_size = batch_size,
        label_mode = 'binary',
        shuffle = True
    )

    gerador = image_dataset_from_directory(
        classes,
        validation_split = 0.2,
        subset = "validation",
        seed = 123,
        image_size = (224, 224),
        batch_size = batch_size,
        label_mode = 'binary',
        shuffle = False
    )

    # Otimização de leitura e cache em memória
    AUTOTUNE = tf.data.AUTOTUNE
    treinamento = treinamento.prefetch(buffer_size=AUTOTUNE)
    gerador = gerador.prefetch(buffer_size=AUTOTUNE)

    modelobase = MobileNetV2(
        weights='imagenet',
        include_top=False,
        input_shape=(224, 224, 3)
    )
    modelobase.trainable = False

    # 4. DATA AUGMENTATION INTEGRADO AO MODELO (Roda direto na estrutura do TF de forma paralela)
    modelo = Sequential([
        # Camada de normalização (Rescale 1./255)
        Rescaling(1.0 / 255, input_shape=(224, 224, 3)),
        # Data Augmentation equivalente ao seu antigo ImageDataGenerator
        RandomRotation(0.05),  # ~20 graus
        RandomTranslation(height_factor=0.2, width_factor=0.2),
        RandomFlip("horizontal"),
        RandomZoom(0.2),
        modelobase,
        GlobalAveragePooling2D(),
        Dropout(0.2),
        Dense(1, activation='sigmoid')
    ])

    modelo.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    modelo.fit(
        treinamento,
        epochs=epochs,
        validation_data=gerador
    )

    modelobase.trainable = True

    for layer in modelobase.layers[:100]:
        layer.trainable = False

    modelo.compile(
        optimizer=Adam(learning_rate=0.0001),
        loss='binary_crossentropy',
        metrics=['accuracy']
    )

    modelo.fit(
        treinamento,
        epochs=epochs,
        validation_data=gerador
    )

    modelo.save(MODELO_PATH)
    return modelo


def carregarmodelo():
    global modelodiretorio
    if modelodiretorio is None:
        if os.path.exists(MODELO_PATH):
            modelodiretorio = load_model(MODELO_PATH)
        else:
            modelodiretorio = treinarmodelo()
    return modelodiretorio


detector_nomes = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# 2. Mapeamento Inglês -> Português (Termos otimizados para CLIP + Bioplásticos)
DICIONARIO_MATERIAIS = {
    # Celulose e Amidos
    "cellulose": "Celulose",
    "cellulose fiber": "Fibra de Celulose",
    "wood fiber": "Fibra de Madeira",
    "wood pulp": "Polpa de Madeira",
    "paper pulp": "Polpa de Papel",
    "starch": "Amido",
    "corn starch": "Amido de Milho",
    "potato starch": "Amido de Batata",
    "tapioca starch": "Amido de Mandioca",
    "rice starch": "Amido de Arroz",
    "wheat starch": "Amido de Trigo",
    
    # Resíduos Agrícolas e Fibras
    "agricultural waste": "Resíduo Agrícola",
    "crop residue": "Resíduo de Colheita",
    "straw": "Palha",
    "bagasse": "Bagaço de Cana",
    "wheat bran": "Farelo de Trigo",
    "corn husk": "Palha de Milho",
    "rice hull": "Casca de Arroz",
    "bamboo fiber": "Fibra de Bambu",
    "coconut fiber": "Fibra de Coco",
    "hemp": "Cânhamo",
    
    # Cascas, Polpas e Alimentos
    "banana peel": "Casca de Banana",
    "apple pulp": "Polpa de Maçã",
    "orange peel": "Casca de Laranja",
    "citrus peel": "Casca de Citros",
    "potato peel": "Casca de Batata",
    "watermelon rind": "Casca de Melancia",
    "melon rind": "Casca de Melão",
    "avocado pit": "Caroço de Abacate",
    "used tea leaves": "Folhas de Chá Usadas",
    "coffee pods": "Borra/Cápsula de Café",
    "spent grains from brewing": "Bagaço de Cervejaria",
    "food waste": "Resíduo Alimentar",
    "organic waste": "Resíduo Orgânico",
    "eggshell": "Casca de Ovo",
    
    # Óleos e Proteínas
    "vegetable oil": "Óleo Vegetal",
    "soybean oil": "Óleo de Soja",
    "used cooking oil": "Óleo de Cozinha Usado",
    "chitosan": "Quitosana",
    "gelatin": "Gelatina",
    "seaweed": "Alga Marinha",
    "alginate": "Alginato",
    
    # Plásticos e Inúteis (Para detecção de rejeitos)
    "plastic bag": "Sacola Plástica",
    "water bottle": "Garrafa PET",
    "water jug": "Garrafão de Água",
    "plastic cutlery": "Talher de Plástico",
    "styrofoam": "Isopor"
}

# Lista contendo apenas os termos em inglês para a busca do CLIP
LABELS_INGLES = list(DICIONARIO_MATERIAIS.keys())

def classificarimagem(arquivoimagem):
    # Leitura da imagem
    if isinstance(arquivoimagem, bytes):
        img = Image.open(io.BytesIO(arquivoimagem))
    elif isinstance(arquivoimagem, str):
        img = Image.open(arquivoimagem)
    else:
        img = Image.open(arquivoimagem)

    img = img.convert('RGB')

    # ETAPA A: CLIP executa a busca com termos em Inglês
    resultado_clip = detector_nomes(img, candidate_labels=LABELS_INGLES)
    
    # Obtém o rótulo em inglês com maior probabilidade
    nome_ingles = resultado_clip[0]['label']
    confianca_nome = round(resultado_clip[0]['score'] * 100, 2)
    
    # Traduz para Português usando o Dicionário
    nomeobjeto_pt = DICIONARIO_MATERIAIS.get(nome_ingles, nome_ingles.title())

    # ETAPA B: Classificador do seu modelo de Bioplásticos
    imgresized = img.resize((224, 224))
    imagens = np.array(imgresized)
    imagens = np.expand_dims(imagens, axis=0)

    modelo = carregarmodelo()  # Função que carrega seu modelo Keras/TensorFlow
    predicao = modelo.predict(imagens, verbose=0)

    probabilidadeutil = float(predicao[0][0]) * 100
    probabilidadenaoutil = 100.0 - probabilidadeutil
    resultadoutil = probabilidadeutil > 70

    return {
        "objetodetectado": nomeobjeto_pt,
        "termo_original_en": nome_ingles,
        "confianca_nome": confianca_nome,
        "acuracia": round(probabilidadeutil, 2),
        "util_para_bioplastico": resultadoutil,
        "classe_predita": "Úteis" if resultadoutil else "Não Úteis",
        "top3": [
            {"classe": "Úteis", "probabilidade": round(probabilidadeutil, 2)},
            {"classe": "Não Úteis", "probabilidade": round(probabilidadenaoutil, 2)},
        ]
    }