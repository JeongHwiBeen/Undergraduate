"""
Model conversion for use with Android Studio
안드로이드 스튜디오에 탑재하기 위한 모델 변환
""" 
import tensorflow as tf

# 모델 파일 이름 리스트
model_filenames = [
    './models/monkeypox_classification_model1.keras',
    './models/monkeypox_classification_model2.keras',
    './models/monkeypox_classification_model3.keras',
    './models/monkeypox_classification_model4.keras',
    './models/monkeypox_classification_model5.keras',
    './models/monkeypox_classification_model6.keras',
    './models/monkeypox_classification_model7.keras',
    './models/monkeypox_classification_model8.keras',
    './models/monkeypox_classification_model9.keras'
]

# .tflite 파일로 저장할 이름 리스트
tflite_filenames = [
    './converted_models/model_v1.tflite',
    './converted_models/model_v2.tflite',
    './converted_models/model_v3.tflite',
    './converted_models/model_v4.tflite',
    './converted_models/model_v5.tflite',
    './converted_models/model_v6.tflite',
    './converted_models/model_v7.tflite',
    './converted_models/model_v8.tflite',
    './converted_models/model_v9.tflite'
]

# 각 모델을 로드하고 변환하여 저장
for i in range(len(model_filenames)):
    # .keras 모델 로드
    model = tf.keras.models.load_model(model_filenames[i])
    
    # TFLite 형식으로 변환
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    
    # .tflite 파일로 저장
    with open(tflite_filenames[i], 'wb') as f:
        f.write(tflite_model)
    
    print(f"Converted {model_filenames[i]} to {tflite_filenames[i]}")