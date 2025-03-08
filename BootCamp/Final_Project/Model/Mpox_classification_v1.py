'''
-----------------------------
1차 모델
CNN을 이용하여 모델 자체 제작
최대 정확도: 79%
-----------------------------
'''

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras import layers, models
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import tensorflow as tf

# 데이터셋 경로 설정
train_dir = './Mpox/Fold1/Fold1/Fold1/Train'
validation_dir = './Mpox/Fold1/Fold1/Fold1/Val'
test_dir = './Mpox/Fold1/Fold1/Fold1/Test'

val_datagen = ImageDataGenerator(rescale=1./255)
test_datagen = ImageDataGenerator(rescale=1./255)
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


# 모델 구축
model = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Flatten(),
    layers.Dense(512, activation='relu'),
    layers.Dropout(0.5),  # 드롭아웃 추가
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.3),  # 드롭아웃 추가
    layers.Dense(1, activation='sigmoid')
])

model.compile(loss='binary_crossentropy', metrics=['accuracy'],optimizer='adam')

model_save_path = 'monkeypox_classification_model.keras'

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
    steps_per_epoch=train_generator.samples // 200,
    epochs=200,
    validation_data=validation_generator,
    validation_steps=validation_generator.samples // 200
)

# 모델 평가
test_loss, test_acc = model.evaluate(test_generator, steps=test_generator.samples // 32)
print(f"Test Accuracy: {test_acc:.2f}")

model.save('monkeypox_classification_model.keras')