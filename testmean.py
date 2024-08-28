import numpy as np
import statsmodels.api as sm

def estimate_mean_reversion_rate(spread_data):
    # Calculate the changes in spread (Delta S)
    delta_S = np.diff(spread_data)
    
    # Align S(t) and Delta S(t)
    S_t = spread_data[:-1]  # Remove the last element to match the size of delta_S
    
    # Add a constant to S_t for the intercept in the regression
    S_t_with_const = sm.add_constant(S_t)
    
    # Perform the linear regression: Delta S = c - alpha * S(t)
    model = sm.OLS(delta_S, S_t_with_const).fit()
    
    # alpha is the negative of the slope coefficient
    alpha = -model.params[1]
    
    # Equilibrium spread S_eq can be estimated from the intercept
    S_eq = model.params[0] / alpha

    return alpha, S_eq, model

# Example Usage
spread_data = np.array([6.0, 5.9, 5.7, 5.5, 5.3, 5.2, 5.0, 4.9, 5.1, 5.0, 4.8, 4.9, 5.0])

alpha, S_eq, model = estimate_mean_reversion_rate(spread_data)
print(f"Estimated mean-reversion rate (alpha): {alpha:.4f}")
print(f"Estimated equilibrium spread (S_eq): {S_eq:.4f}")
