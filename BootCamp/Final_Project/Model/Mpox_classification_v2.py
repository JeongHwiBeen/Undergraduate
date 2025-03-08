'''
------------------------------------------
2차 모델
VGG19 모델 + 추가 Dense 층
최대 정확도: 88%
------------------------------------------
'''

from tensorflow.keras.applications import VGG19
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, models
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint
import tensorflow as tf

# 데이터셋 경로 설정
train_dir = './Mpox/Fold1/Fold1/Fold1/Train'
validation_dir = './Mpox/Fold1/Fold1/Fold1/Val'
test_dir = './Mpox/Fold1/Fold1/Fold1/Test'

# ImageDataGenerator를 사용하여 이미지 데이터 전처리
train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=180,
    width_shift_range=0.5,
    height_shift_range=0.5,
    shear_range=0.5,
    zoom_range=0.5,
    horizontal_flip=True,
    vertical_flip=True,
    fill_mode='nearest'
)

val_datagen = ImageDataGenerator(rescale=1./255)
test_datagen = ImageDataGenerator(rescale=1./255)

# Train generator 생성
train_generator = train_datagen.flow_from_directory(
    directory=train_dir,
    target_size=(224, 224),  # 이미지 크기 조정
    batch_size=32,
    class_mode='binary'  # 이진 분류
)

# Validation generator 생성
validation_generator = val_datagen.flow_from_directory(
    directory=validation_dir,
    target_size=(224, 224),
    batch_size=32,
    class_mode='binary'
)

# Test generator 생성
test_generator = test_datagen.flow_from_directory(
    directory=test_dir,
    target_size=(224, 224),
    batch_size=32,
    class_mode='binary',
    shuffle=False  # 평가 시에는 섞지 않음
)

# VGG19 모델 로드 (사전 학습된 가중치 사용, 최상위 분류 층 제외)
base_model = VGG19(weights='imagenet', include_top=False, input_shape=(224, 224, 3))

# 기존 가중치를 고정하여 학습되지 않도록 설정
base_model.trainable = False

# VGG19 모델 위에 새로운 분류 층 추가
model = models.Sequential([
    base_model,
    layers.Flatten(),
    layers.Dense(512, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(256, activation='relu'),  # 추가된 Dense 층
    layers.Dropout(0.3),
    layers.Dense(1, activation='sigmoid')
])

# 모델 컴파일
model.compile(loss='binary_crossentropy',
              optimizer=Adam(learning_rate=1e-5),  # 작은 학습률을 사용하는 것이 일반적
              metrics=['accuracy'])

model_save_path = 'monkeypox_classification_model2.keras'

# 모델 학습 도중 가장 좋은 성능을 보인 모델을 저장
checkpoint = ModelCheckpoint(
    filepath=model_save_path,
    monitor='val_accuracy',  # 검증 정확도를 기준으로 저장
    save_best_only=True,     # 가장 좋은 성능을 보인 경우만 저장
    mode='max',
    verbose=1
)

# 모델 학습
history = model.fit(
    train_generator,
    steps_per_epoch=train_generator.samples // 100,
    epochs=100,
    validation_data=validation_generator,
    validation_steps=validation_generator.samples // 100,
    callbacks=[checkpoint]
)

# 모델 평가
test_loss, test_acc = model.evaluate(test_generator, steps=test_generator.samples // 32)
print(f"Test Accuracy: {test_acc:.2f}")

model.save('monkeypox_classification_model2.keras')