'''
-----------------------------------------------------------------------
3차 모델
최대 정확도 88% 모델(2차 모델)을 활용하여 파인 튜닝
서로 다른 하이퍼 파라미터(학습률, 드롭아웃 계수)를 적용한 9개의 모델 생성
앙상블 기법을 적용
-----------------------------------------------------------------------
'''

import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.layers import Dense, Dropout

# 9개의 하이퍼파라미터 조합
learning_rates = [0.001, 0.0001, 0.01]
dropout_rates = [0.2, 0.3, 0.4]

models = []

# 데이터 경로 설정
train_data_dir = './Mpox/Fold1/Fold1/Fold1/Train'
validation_data_dir = './Mpox/Fold1/Fold1/Fold1/Val'

# 이미지 크기 설정
img_height = 224
img_width = 224

# ImageDataGenerator를 사용하여 이미지 로드 및 전처리
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True
)

validation_datagen = ImageDataGenerator(rescale=1./255)

# 훈련 데이터 생성
train_generator = train_datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_height, img_width),
    batch_size=32,
    class_mode='binary'
)

# 검증 데이터 생성
validation_generator = validation_datagen.flow_from_directory(
    validation_data_dir,
    target_size=(img_height, img_width),
    batch_size=32,
    class_mode='binary'
)

# 1. 기존 학습된 모델 로드
base_model = load_model('monkeypox_classification_model.keras')

# 2. 모델 구조 변경 및 파인튜닝 준비
for lr in learning_rates:
    for dr in dropout_rates:
        # 기존 모델의 출력 레이어 제거 및 새로운 레이어 추가
        x = base_model.layers[-2].output  # 기존 모델의 마지막 레이어 직전 출력 가져오기
        x = Dropout(dr, name=f'dropout_{dr}_lr_{lr}')(x)  # 드롭아웃 레이어에 고유한 이름 지정
        predictions = Dense(1, activation='sigmoid', name=f'output_dense_lr_{lr}_dr_{dr}')(x)  # Dense 레이어에 고유한 이름 지정

        # 새로운 모델 구성
        model = tf.keras.Model(inputs=base_model.input, outputs=predictions)

        # 모델의 일부 레이어 동결 (선택사항)
        for layer in model.layers[:-2]:  # 새로운 레이어 제외하고 동결
            layer.trainable = False

        # 3. 모델 컴파일
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
                      loss='binary_crossentropy',
                      metrics=['accuracy'])

        # 모델 리스트에 추가
        models.append((model, lr, dr))

# 4. 모델 학습
for i, (model, lr, dr) in enumerate(models):
    print(f"Training model {i+1}/9 with learning rate={lr}, dropout rate={dr}")
    model.fit(train_generator,
              epochs=10,
              validation_data=validation_generator)
    
    # 모델 저장
    model.save(f'./models/monkeypox_classification_model{i+1}.keras')
