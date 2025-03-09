from tensorflow.keras.models import load_model
import tensorflow as tf
# .keras 모델 파일 로드
model = load_model('monkeypox_classification_model2.keras')

# 첫 번째 레이어의 'batch_input_shape'를 'input_shape'로 변경
for layer in model.layers:
    if isinstance(layer, tf.keras.layers.Conv2D):
        config = layer.get_config()
        if 'batch_input_shape' in config:
            del config['batch_input_shape']
        layer.__init__(**config)

# 변환기 사용
converter = tf.lite.TFLiteConverter.from_keras_model(model)

# .tflite 파일로 변환
tflite_model = converter.convert()

# 파일로 저장
with open('model.tflite', 'wb') as f:
    f.write(tflite_model)
