import torch
import logging
import pandas as pd
from sklearn.model_selection import train_test_split
import torch.optim as optim
import torch.nn as nn
from .model import CNNGRUModel
from .data_loader import DataProcessor
from .trainer import evaluate_model
import pickle

class ModelTrainer:
    @staticmethod
    def load_and_preprocess_data(data_paths, seq_cols, target_cols):
        """
        Function to load and preprocess data.
        """
        # Load CSV files and concatenate them
        dataframes = [pd.read_csv(path) for path in data_paths]
        data = pd.concat(dataframes, ignore_index=True)
      
        # Preprocess the data
        data = DataProcessor.preprocess_data(data)
        data = DataProcessor.reset_week_numbers(data)
        data = DataProcessor.transform_target(data)

        # Split data into train and test sets
        patient_ids = data['key_id'].unique()
        train_ids, test_ids = train_test_split(patient_ids, test_size=0.2, random_state=42)
        train_data = data[data['key_id'].isin(train_ids)]
        test_data = data[data['key_id'].isin(test_ids)]

        # Find max sequence length and get data loaders
        max_length = DataProcessor.find_max_sequence_length_by_week(data, seq_cols)
        train_loader, val_loader = DataProcessor.get_dataloaders(train_data, test_data, seq_cols, target_cols, max_length)

        return train_loader, val_loader

    @staticmethod
    def initialize_model(seq_cols, target_cols, model_params, device):
        """
        Function to initialize the model.
        """
        model = CNNGRUModel(
            input_dim=len(seq_cols),
            cnn_out_channels=model_params.get('cnn_out_channels', 256),
            cnn_kernel_size=model_params.get('cnn_kernel_size', 4),
            gru_hidden_dim=model_params.get('gru_hidden_dim', 64),
            output_dim=len(target_cols),
            dropout_prob=model_params.get('dropout_prob', 0.5)
        )
        model.to(device)
        return model

    @staticmethod
    def train_model(model, train_loader, val_loader, training_params, target_cols, device):
        """
        Function to train the model.
        """
        criterion = nn.BCELoss()
        optimizer = optim.AdamW(model.parameters(), lr=training_params.get('learning_rate', 0.0001))
        epochs = training_params.get('epochs', 50)

        model.train()  # Switch to training mode
        for epoch in range(epochs):
            total_loss = 0
            for inputs, targets in train_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            avg_train_loss = total_loss / len(train_loader)
            logging.info(f'Epoch [{epoch+1}/{epochs}], Train Loss: {avg_train_loss:.4f}')

            # Validation after each epoch
            model.eval()  # Switch to evaluation mode
            val_loss = evaluate_model(model, val_loader, target_cols, device)
            model.train()  # Switch back to training mode

            # Handle val_loss if it's a dictionary
            if isinstance(val_loss, dict):
                loss_value = val_loss.get('loss', 0.0)
                logging.info(f'Epoch [{epoch+1}/{epochs}], Val Loss: {loss_value:.4f}')
            else:
                logging.info(f'Epoch [{epoch+1}/{epochs}], Val Loss: {val_loss:.4f}')

            
    # @staticmethod
    # def save_final_model(model, path='./model2/model/final_model.pkl'):
    #     """
    #     Function to save the final model as a pickle file.
    #     """
    #     with open(path, 'wb') as f:
    #         pickle.dump(model, f)
    #     print(f'Final model saved at {path}')

    # @staticmethod
    # def load_model(path='./model2/model/final_model.pkl', device='cpu'):
    #     """
    #     Function to load the model saved as a pickle file.
    #     """
    #     with open(path, 'rb') as f:
    #         model = pickle.load(f)
    #     model.to(device)
    #     model.eval()  # Set the model to evaluation mode
    #     print(f'Model loaded from {path}')
    #     return model
