import random
import numpy as np
from sklearn.datasets import make_classification, make_regression

def make_multi_input_classification(n_informative_Xs=3, 
                                    n_weak_Xs=0,
                                    n_random_Xs=0,
                                    weak_noise_sd=0.2,
                                    seed = None,
                                    **sklearn_params                                   
                                    ):
    
    """Wrapper for sklearn's make_classification to make matrix sets with informative, weak, and random matrices.
    
    Parameters
    ---------
    n_informative_Xs: int, the number of informative matrices
    n_weak_Xs: int, the number of weak matrices generated by degrading informative matrices with added Gausisan noise
    n_random_Xs: int, the number of random matrices generated by shuffling the feature rows of informative matrices
    sklearn_params: parameters for sklearn make_classification, which generates the data
    weak_noise_sd: float, standard deviation of the Gaussian noise term used to generate weak matrices
    seed: int, seed for random number generator
    
    returns
    -------
    Xs: list, list of synthetic feature matrices
    y: ndarray(dtype=int), synthetic sample labels
    X_types: list of strings, ordered description of each synthetic matrix as 'informative', 'weak', or 'random'
    
    """
    
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        sklearn_params['random_state'] = seed
            
    n_Xs = n_informative_Xs + n_weak_Xs + n_random_Xs
    n_samples, n_features = sklearn_params['n_samples'], sklearn_params['n_features']
    
    for p in sklearn_params:
        if p in ['n_features', 'n_informative', 'n_redundant', 'n_repeated']:
            sklearn_params[p] *= n_Xs
            
    X, y = make_classification(**sklearn_params)
    
    # split synthetic data into separate matrices
    Xs = [X[:, i*n_features:(i+1)*n_features] for i in range(n_Xs)]
    
    # add extra gaussian noise to create weak matrices
    for i in range(n_weak_Xs):
        Xs[i] += np.random.normal(loc=0, scale=weak_noise_sd, size=(n_samples, n_features))
        
    # shuffle matrices that are neither informative or weak
    for i in range(n_weak_Xs, n_Xs - n_informative_Xs):
        np.random.shuffle(Xs[i])
        
    X_types = ['weak' for i in range(n_weak_Xs)] 
    X_types += ['random' for i in range(n_random_Xs)] 
    X_types += ['informative' for i in range(n_informative_Xs)]
    tuples = list(zip(Xs, X_types))
    random.shuffle(tuples)
    Xs, X_types = zip(*tuples)
    
    return list(Xs), y, list(X_types)


def make_multi_input_regression(n_informative_Xs=3, 
                                n_weak_Xs=0,
                                n_random_Xs=0,
                                weak_noise_sd=0.2,
                                seed = None,
                                **sklearn_params):
    
    """Get a synthetic regression dataset with multiple feature matrices that are either informative, weak, or random.
    
    Parameters
    ---------
    n_informative_Xs: int, the number of informative input matrices, each with information content specified by 
        n_features, n_informative, n_redundant
    n_weak_Xs: int, the number of input matrices generated by degrading informative matrices with added Gausisan noise
    n_random_Xs: int, the number of input matrices generated by shuffling the feature rows of informative matrices
    weak_noise_sd: float, standard deviation of the Gaussian noise term used to generate weak matrices
    seed: int, seed for random number generator
    
    returns
    -------
    Xs: list, list of synthetic feature matrices
    y: ndarray(dtype=int), synthetic sample labels
    X_types: list of strings, ordered description of each synthetic matrix as 'informative', 'weak', or 'random'
    
    """
    
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        sklearn_params['random_state'] = seed
            
    n_Xs = n_informative_Xs + n_weak_Xs + n_random_Xs
    n_samples, n_features = sklearn_params['n_samples'], sklearn_params['n_features']
      
    for p in sklearn_params:
        if p in ['n_features', 'n_informative', 'n_redundant', 'n_repeated']:
            sklearn_params[p] *= n_Xs
    
    X, y = make_regression(**sklearn_params)
    
    # split synthetic data into separate matrices
    Xs = [X[:, i*n_features:(i+1)*n_features] for i in range(n_Xs)]
    
    # add extra gaussian noise to create weak matrices
    for i in range(n_weak_Xs):
        Xs[i] += np.random.normal(loc=0, scale=weak_noise_sd, size=(n_samples, n_features))
        
    # shuffle matrices that are neither informative or weak
    for i in range(n_weak_Xs, n_Xs - n_informative_Xs):
        np.random.shuffle(Xs[i])
        
    X_types = ['weak' for i in range(n_weak_Xs)] 
    X_types += ['random' for i in range(n_random_Xs)] 
    X_types += ['informative' for i in range(n_informative_Xs)]
    tuples = list(zip(Xs, X_types))
    random.shuffle(tuples)
    Xs, X_types = zip(*tuples)
    
    return list(Xs), y, list(X_types)