import tkinter as tk
from tkinter import messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from statsmodels.tsa.arima.model import ARIMA

# Function to read product prices from the Excel file
def read_prices_from_excel(file_path='product_search_results.xlsx'):
    try:
        # Read the Excel file
        excel_data = pd.read_excel(file_path, sheet_name=None)  # None loads all sheets

        # Extract prices from both Amazon and Flipkart sheets
        amazon_prices = excel_data['Amazon Products']['price'].dropna().values
        flipkart_prices = excel_data['Flipkart Products']['price'].dropna().values

        # Combine both Amazon and Flipkart prices into one array (you can choose one if preferred)
        prices = np.concatenate([amazon_prices, flipkart_prices])
        return prices
    except Exception as e:
        messagebox.showerror("Error", f"Error reading Excel file: {e}")
        return np.array([])  # Return an empty array instead of an empty list

# Function to preprocess the price data and make predictions using ARIMA
def make_price_predictions(prices, order=(5, 1, 0)):
    # Fit ARIMA model
    try:
        model = ARIMA(prices, order=order)  # (p, d, q) - Adjust based on your data
        model_fit = model.fit()

        # Make predictions
        predicted_prices = model_fit.predict(start=0, end=len(prices)-1, typ='levels')

        return predicted_prices, prices
    except Exception as e:
        messagebox.showerror("Error", f"Error in ARIMA model: {e}")
        return np.array([]), np.array([])

# Tkinter GUI Application
class PricePredictionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Price Prediction")

        # Set window size
        self.root.geometry("600x400")

        # Add a label
        self.label = tk.Label(self.root, text="Product Price Prediction", font=("Arial", 18))
        self.label.pack(pady=20)

        # Add a Button to trigger the price prediction
        self.predict_button = tk.Button(self.root, text="Predict Prices", command=self.predict_prices,
                                        font=("Arial", 14))
        self.predict_button.pack(pady=20)

        # Add an exit button
        self.exit_button = tk.Button(self.root, text="Exit", command=self.root.quit, font=("Arial", 14))
        self.exit_button.pack(pady=10)

    def predict_prices(self):
        # Read the prices from the Excel file
        prices = read_prices_from_excel()

        # Check if the prices array is empty
        if prices.size == 0:
            messagebox.showerror("Error", "No prices found in the Excel file.")
            return  # Exit if no prices were read from the file

        # Make price predictions using ARIMA
        predicted_prices, actual_prices = make_price_predictions(prices)

        # Check if prediction is successful
        if predicted_prices.size == 0:
            return

        # Plot the actual vs predicted prices
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(actual_prices, color='blue', label='Actual Prices')
        ax.plot(predicted_prices, color='red', label='Predicted Prices')
        ax.set_title('Product Price Prediction vs Actual Prices')
        ax.set_xlabel('Time')
        ax.set_ylabel('Price')
        ax.legend()

        # Display the plot in Tkinter window
        self.show_plot(fig)

    def show_plot(self, figure):
        # Clear previous plot (if any)
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Canvas):
                widget.destroy()

        # Convert the matplotlib plot to an image that can be shown in Tkinter
        canvas = FigureCanvasTkAgg(figure, master=self.root)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=20)


# Running the Tkinter app
if __name__ == "__main__":
    root = tk.Tk()
    app = PricePredictionApp(root)
    root.mainloop()
