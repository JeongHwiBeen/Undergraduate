import tensorflow as tf
import numpy as np

# 모델 로드
interpreter = tf.lite.Interpreter(model_path="model.tflite")
interpreter.allocate_tensors()

# 입력 텐서 가져오기
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# 입력 데이터 준비 (Bitmap -> ByteBuffer로 변환한 데이터와 동일하게 처리)
input_data = np.random.rand(1, 224, 224, 3).astype(np.float32)  # 예시 데이터

# 모델 실행
interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()

# 출력 결과 확인
output_data = interpreter.get_tensor(output_details[0]['index'])
print("Prediction result:", output_data)
