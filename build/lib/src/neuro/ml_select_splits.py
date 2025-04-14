import os
import pickle
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.preprocessing import image
import numpy as np
import msk_modelling_python as msk

def train_model(train_dir, validation_dir):
    # Image data generators for loading and augmenting images
    train_datagen = ImageDataGenerator(rescale=1./255)
    validation_datagen = ImageDataGenerator(rescale=1./255)

    train_generator = train_datagen.flow_from_directory(
        train_dir,
        target_size=(150, 150),
        batch_size=20,
        class_mode='binary'
    )

    validation_generator = validation_datagen.flow_from_directory(
        validation_dir,
        target_size=(150, 150),
        batch_size=20,
        class_mode='binary'
    )

    # Define a simple CNN model
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(150, 150, 3)),
        MaxPooling2D(2, 2),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D(2, 2),
        Flatten(),
        Dense(512, activation='relu'),
        Dense(1, activation='sigmoid')
    ])

    # Compile the model
    model.compile(optimizer='adam',
                loss='binary_crossentropy',
                metrics=['accuracy'])

    # Train the model
    history = model.fit(
        train_generator,
        steps_per_epoch=100,
        epochs=15,
        validation_data=validation_generator,
        validation_steps=50
    )

    # Save the model
    save_path = os.path.dirname(train_dir)
    # Save the model
    # Save the generator configuration instead of the generator itself
    generator_config = {
        'train_dir': train_dir,
        'validation_dir': validation_dir,
        'target_size': (150, 150),
        'batch_size': 20,
        'class_mode': 'binary'
    }
    model.train_generator = train_generator
    model.save(os.path.join(save_path, 'image_classification_model.h5'))
    
    # Save the train_generator separately
    with open(os.path.join(save_path, 'train_generator.pkl'), 'wb') as f:
        pickle.dump(train_generator, f)

    # Evaluate the model accuracy on the validation set
    val_loss, val_accuracy = model.evaluate(validation_generator)
    print(f'Validation accuracy: {val_accuracy * 100:.2f}%')

    

    return model

# Function to classify a single image
def classify_image(image_path,model, train_generator):

    img = image.load_img(image_path, target_size=(150, 150))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0

    prediction = model.predict(img_array)
    class_indices = train_generator.class_indices
    class_labels = {v: k for k, v in class_indices.items()}
    
    predicted_class = 1 if prediction[0] > 0.5 else 0
    class_name = class_labels[predicted_class]
    
    print(f'The image at {image_path} is classified as {class_name}')


if __name__ == "__main__":
    # Define paths to your image folders
    train_dir = r'C:\Users\Bas\ucloud\BSc_thesis_S2024\Lukas_Weilharter\data\session11\RC11_2_splits\training'
    validation_dir = r'C:\Users\Bas\ucloud\BSc_thesis_S2024\Lukas_Weilharter\data\session11\RC11_2_splits\testing'
    model_dir = os.path.join(os.path.dirname(train_dir), 'image_classification_model.h5')
    train_generator_dir = os.path.join(os.path.dirname(train_dir), 'train_generator.pkl')
    
    if not os.path.exists(model_dir):
        model = train_model(train_dir, validation_dir)
    else:
        model = tf.keras.models.load_model(os.path.join(model_dir))

    # Load the train_generator separately
    with open(train_generator_dir, 'rb') as f:
        train_generator = pickle.load(f)

    # Example usage of classify_image function
    example_image_path = msk.ut.select_file()
    classify_image(example_image_path, model, train_generator)