from inspect import signature
import sklearn.base
import joblib

def is_classifier(obj):
    return getattr(obj, "_estimator_type", None) == "classifier"

def is_multi_input(pipe):
    """Detect if a pipeline component is multi-input by determining if the first argument to fit() is 'Xs' 
    """
    first_param = list(signature(pipe.fit).parameters.keys())[0]
    return first_param == 'Xs'

def get_clone(pipe, disable_custom_cloning = False):
    
    """Get a new copy of a transformer/estimator/predictor instance. 
    Parameters
    ----------
    pipe : transformer, estimator, predictor
        Pipeline building block
    disable_custom_cloning : bool
        Flag that disables use of the pipe.get_clone() method
    Returns
    -------
    New transformer/estimator/predictor instance generated by the pipe.get_clone() method, if there is one. If not, the returned instance is created by the generic sklearn.base.clone() function which basically does: pipe.__class__(**pipe.get_params())
    Notes
    -----
    Cutoming cloning via pipe.get_clone() has been added in Pipecaster to enable neural net warm starts that don't conform to sklearn's stateless cloning mechanism.
    """
    
    if hasattr(pipe, 'get_clone') and disable_custom_cloning == False:
        return pipe.get_clone()
    else:
        return sklearn.base.clone(pipe)
    
def save_model(model, filepath):
    joblib.dump(model, filepath) 
    
def load_model(filepath):
    return joblib.load(filepath) 
    
def get_transform_method(pipe):
    if hasattr(pipe, 'transform'):
        transform_method = getattr(pipe, 'transform')
    elif hasattr(pipe, 'predict_proba'):
        transform_method = getattr(pipe, 'predict_proba')
    elif hasattr(pipe, 'decision_function'):
        transform_method = getattr(pipe, 'decision_function')
    elif hasattr(pipe, 'predict'):
        transform_method = getattr(pipe, 'predict')
    else:
        transform_method = None
            
    return transform_method

def get_predict_method(pipe):
    if hasattr(pipe, 'predict'):
        predict_method = getattr(pipe, 'predict')
    elif hasattr(pipe, 'predict_proba'):
        predict_method = getattr(pipe, 'predict_proba')
    elif hasattr(pipe, 'decision_function'):
        predict_method = getattr(pipe, 'decision_function')
    else:
        predict_method = None
            
    return predict_method

def is_predictor(pipe):
    return False if get_predict_method(pipe) is None else True

class FitError(Exception):
    """Exception raised when calls to fit() fail
    """
    def __init__(self, message="call to fit() method failed"):
        self.message = message
        super().__init__(self.message)