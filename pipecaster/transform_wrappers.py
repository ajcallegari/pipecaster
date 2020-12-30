import functools
import numpy as np

import pipecaster.utils as utils
from pipecaster.utils import Cloneable, Saveable
from pipecaster.cross_validation import cross_val_predict

"""
Wrapper classes that provide single channel and multichannel predictors with transform/fit_transform methods, internal cv_training, and internal_cv performance scoring.  Used for meta-prediction and model selection.  Conversion of 
prediction methods to tranform methods is done using the transform_method_name argument, but this argument can usually
be left at it's default value of None to allow autoconversion using the precedence of prediction functions defined in the 
transform_method_precedence module variable.

Examples
--------
# give a single channel predictor transform and fit_transform methods
import pipecaster as pc
model = pc.transformer_wrappers.SingleChannel(model)

# give a single channel predictor transform & fit_transform methods, and internal_cv training
import pipecaster as pc
model = pc.transformer_wrappers.SingleChannelCV(model, internal_cv, cv_processes=1)

# give a multichannel predictor transform and fit_transform methods
import pipecaster as pc
model = pc.transformer_wrappers.Multichannel(model)

# give a multichannel predictor transform & fit_transform methods, and internal_cv training
import pipecaster as pc
model = pc.transformer_wrappers.MultichannelCV(model, internal_cv, cv_processes=1)

"""

# when converting a predictor to a transformer, use these methods for transforming
transform_method_precedence = ['predict_proba', 'decision_function', 'predict_log_proba', 'predict']
                        
def get_transform_method(pipe):
    for method_name in transform_method_precedence:
        if hasattr(pipe, method_name):
            return getattr(pipe, method_name)
    return None

def get_transform_method_name(pipe):
    for method_name in transform_method_precedence:
        if hasattr(pipe, method_name):
            return method_name
    return None

class SingleChannel(Cloneable, Saveable):
    """
    Wrapper class that provides scikit-learn conformant predictors with transform/fit_transform methods.
    
    arguments
    ---------
    predictor: instance of object with scikit-learn predictor interface, default=None
        The sklearn predictor to be wrapped
    transform_method_name: string, default=none
        Indicates the name of the prediction method to use for during calls to transform. If None, 
        the method is automatically chosen using the order in transform_method_precedence.
    
    notes
    -----
    This class uses reflection to expose the predictor methods found in the object that it wraps, so 
    the method attributes in a SingleChannel instance are not identical to the method attributes of the SingleChannel class.
    """
    state_variables = ['classes_']
    
    def __init__(self, predictor=None, transform_method_name=None):
        self._params_to_attributes(SingleChannel.__init__, locals())
        utils.enforce_fit(predictor)
        if transform_method_name is None:
            self.transform_method_name = get_transform_method_name(predictor)
            if self.transform_method_name is None:
                raise NameError('predictor lacks a recognized method for conversion to transformer')
        self._expose_predictor_interface(predictor)
        self._estimator_type = utils.detect_predictor_type(predictor)
        if self._estimator_type is None:
            raise TypeError('could not detect predictor type for {}'.format(predictor))
        
    def _expose_predictor_interface(self, predictor):
        for method_name in utils.recognized_pred_methods:
            if hasattr(predictor, method_name):
                prediction_method = functools.partial(self.predict_with_method, method_name=method_name)
                setattr(self, method_name, prediction_method)
        
    def set_transform_method(self, method_name):
        self.transform_method_name = method_name
                
    def fit(self, X, y=None, **fit_params):
        self.model = utils.get_clone(self.predictor)
        if y is None:
            self.model.fit(X, **fit_params)
        else:
            self.model.fit(X, y, **fit_params)
        if self._estimator_type == 'classifier':
            self.classes_ = self.model.classes_
            
        return self
    
    def predict_with_method(self, X, method_name):
        if hasattr(self, 'model') == False:
            raise utils.FitError('prediction attempted before model fitting') 
        if hasattr(self.model, method_name):
            predict_method = getattr(self.model, method_name)
            return predict_method(X)
        else:
            raise NameError('prediction method {} not found in {} attributes'.format(method_name, self.model))
            
    def transform(self, X):
        if hasattr(self, 'model'):
            transform_method = getattr(self.model, self.transform_method_name)
            X_t = transform_method(X)
            X_t = X_t.reshape(-1, 1) if (X_t is not None and len(X_t.shape) == 1 ) else X_t
            return X_t
        else:
            raise utils.FitError('transform called before model fitting')
    
    def fit_transform(self, X, y=None, **fit_params):
        if hasattr(self.predictor, 'fit_transform'):
            self.model = utils.get_clone(self.predictor)
            if y is None:
                X_t = self.model.fit_transform(X, **fit_params)
            else:
                X_t = self.model.fit_transform(X, y, **fit_params)
        else:
            if y is None:
                self.fit(X, **fit_params)
            else:
                self.fit(X, y, **fit_params)
            transform_method = getattr(self.model, self.transform_method_name)
            X_t = transform_method(X)
            X_t = X_t.reshape(-1, 1) if len(X_t.shape) == 1 else X_t
            
        return X_t

    def _more_tags(self):
        return {'multichannel': False}
    
    def get_clone(self):
        clone = super().get_clone()
        if hasattr(self, 'model'):
            clone.model = utils.get_clone(self.model)
        return clone
    
class SingleChannelCV(SingleChannel):
    """
    Wrapper class that provides scikit-learn conformant predictors with transform/fit_transform methods and 
    internal cross validation functionality.
    
    arguments
    ---------
    predictor: scikit-learn conformant predictor instance
        The predictor to wrap.
    transform_method: string, default=None
        The name of the method to use to generate output when transform is called on the predictor, as occurs
        when the predictor is not the last layer in the pipeline.
    internal_cv: None, int, or sklearn cross validation splitter, default=5  
        Set the internal cv method used for transforming when fit_tranform() is called.  If 1, internal cv 
        is inactivated. For integers > 1, KFold is used for regressors and StratifiedKFold used for 
        classifiers.  If None, the default value of 5 is used.
    cv_processes: int, default=1
        Number of parallel fit jobs to run during internal cv training.
    scorer: callable, default=None
        Callable with the pattern scorer(y_pred, y_true) that computes a figure of merit for the internal_cv
        run.  The figure of merit is exposed through creation of a score_ attribute. Used by ModelSelector 
        to select models based on performance.
    
    notes
    -----
    fit().transform() is not the same as fit_tranform() because only the latter uses internal cv training and inference.
    On calls to fit_transform() the model is fit on both the entire training set and cv splits of the training set.
    The model fit on the entire dataset is stored for inference on subsequent calls to predict(), predict_proba(), 
    decision_function(), or tranform().  The models fit on cv splits are used to make the predictions returned 
    by fit_transform but are not stored for future use. 

    This class uses reflection to expose the predictor methods found in the object that it wraps, so 
    the method attributes in a SingleChannelCV instance are not identical to the method attributes of the SingleChannelCV class.
    """
    
    state_variables = ['score_']
    
    def __init__(self, predictor, transform_method_name=None, internal_cv=5, cv_processes=1, scorer=None):
        self._params_to_attributes(SingleChannelCV.__init__, locals())
        self._inherit_state_variables(super())
        super().__init__(predictor, transform_method_name)
        self.internal_cv = 5 if internal_cv is None else internal_cv 
                
    def fit_transform(self, X, y=None, groups=None, **fit_params):
        self.fit(X, y, **fit_params)
        
        # internal cv training is disabled
        if self.internal_cv is None or (type(self.internal_cv) == int and self.internal_cv < 2):
            X_t = self.transform(X)
        # internal cv training is enabled
        else:
            X_t = cross_val_predict(self.predictor, X, y, groups=groups, predict_method=self.transform_method_name, 
                                     cv=self.internal_cv, combine_splits=True, n_processes=self.cv_processes, 
                                     split_seed=None, fit_params=fit_params)
            
            if self.scorer is not None:
                if self.transform_method_name in ['predict_proba', 'decision_function', 'predict_log_proba']:
                    self.score_ = self.scorer(y, utils.classify_samples(X_t))
                else:
                    self.score_ = self.scorer(y, X_t)
                    
        X_t = X_t.reshape(-1, 1) if (X_t is not None and len(X_t.shape) == 1) else X_t
        
        return X_t

    def _more_tags(self):
        return {'multichannel': False}
    
    def get_clone(self):
        return super().get_clone()
    
class Multichannel(Cloneable, Saveable):
    """
    Wrapper class that provides MultichannelPredictor instances with transform methods.
    
    Notes
    -----
    This class uses reflection to expose the predictor methods found in the object that it wraps, so 
    the method attributes in a Multichannel instance are not identical to the method attributes of the Multichannel class.
    """
    state_variables = ['classes_']
    
    def __init__(self, multichannel_predictor=None, transform_method_name=None):
        self._params_to_attributes(Multichannel.__init__, locals())
        utils.enforce_fit(multichannel_predictor)
        utils.enforce_predict(multichannel_predictor)        
        self._estimator_type = utils.detect_predictor_type(multichannel_predictor)
        if self._estimator_type is None:
            raise AttributeError('could not detect predictor type')
        if transform_method_name is None:
            self.transform_method_name = get_transform_method_name(multichannel_predictor)
            if self.transform_method_name is None:
                raise TypeError('missing recognized method for transforming with a predictor')
        self._expose_predictor_interface(multichannel_predictor)
        
    def _expose_predictor_interface(self, multichannel_predictor):
        for method_name in utils.recognized_pred_methods:
            if hasattr(multichannel_predictor, method_name):
                prediction_method = functools.partial(self.predict_with_method, method_name=method_name)
                setattr(self, method_name, prediction_method)
                
    def fit(self, Xs, y=None, **fit_params):
        self.model = utils.get_clone(self.multichannel_predictor)
        if y is None:
            self.model.fit(Xs, **fit_params)
        else:
            self.model.fit(Xs, y, **fit_params)
        if hasattr(self.model, 'classes_'):
            self.classes_ = self.model.classes_
        return self
                
    def predict_with_method(self, Xs, method_name):
        if hasattr(self, 'model') == False:
            raise FitError('prediction attempted before call to fit()')
        live_Xs = [X for X in Xs if X is not None]
        X = np.concatenate(live_Xs, axis=1)
        prediction_method = getattr(self.model, method_name)
        return prediction_method(Xs)
    
    def transform(self, Xs):
        if hasattr(self, 'model') == False:
            raise FitError('transform attempted before call to fit()')
        transform_method = getattr(self.model, self.transform_method_name)
        Xs_t = transform_method(Xs)
        Xs_t = [X.reshape(-1, 1) if (X is not None and len(X.shape) == 1) else X for X in Xs_t]
        return Xs_t
    
    def fit_transform(self, Xs, y=None, **fit_params):
        self.fit(Xs, y=None, **fit_params)
        return self.transform(Xs)
    
class MultichannelCV(Multichannel):
    """
    Wrapper class that provides MultichannelPredictor instances with transform methods and internal cv training.
    
    arguments
    ---------
    multichannel_predictor: instance of an pipecaster conformant multichannel predictor
        The predictor to wrap.
    transform_method: string, default=None
        The name of the method to use to generate output when transform is called on the predictor, as occurs
        when the predictor is not the last layer in the pipeline.
    internal_cv: None, int, or sklearn cross validation splitter, default=5  
        Set the internal cv method used for transforming when fit_tranform() is called.  If 1, internal cv 
        is inactivated. For integers > 1, KFold is used for regressors and StratifiedKFold used for 
        classifiers.  If None, the default value of 5 is used.
    cv_processes: int, default=1
        Number of parallel fit jobs to run during internal cv training.
    scorer: callable, default=None
        Callable with the pattern scorer(y_pred, y_true) that computes a figure of merit for the internal_cv
        run.  The figure of merit is exposed through creation of a score_ attribute. Used by ModelSelector 
        to select models based on performance.
    
    notes
    -----
    fit().transform() is not the same as fit_tranform() because only the latter uses internal cv training and inference.
    On calls to fit_transform() the model is fit on both the entire training set and cv splits of the training set.
    The model fit on the entire dataset is stored for inference on subsequent calls to predict(), predict_proba(), 
    decision_function(), or tranform().  The models fit on cv splits are used to make the predictions returned 
    by fit_transform but are not stored for future use. 

    This class uses reflection to expose the predictor methods found in the object that it wraps, so 
    the method attributes in a SingleChannelCV instance are not identical to the method attributes of the SingleChannelCV class.
    """
    state_variables = ['score_']
    
    def __init__(self, multichannel_predictor=None, transform_method_name=None, internal_cv=5, 
                 cv_processes=1, scorer=None):
        internal_cv = 5 if internal_cv is None else internal_cv 
        super().__init__(multichannel_predictor, transform_method_name)
        self._params_to_attributes(MultichannelCV.__init__, locals())
        self._inherit_state_variables(super())
        
    def fit_transform(self, Xs, y=None, groups=None, **fit_params):
        self.fit(Xs, y, **fit_params)
        
        # internal cv training is disabled
        if self.internal_cv is None or (type(self.internal_cv) == int and self.internal_cv < 2):
            Xs_t = self.transform(Xs)
        # internal cv training is enabled
        else:
            Xs_t = cross_val_predict(self.multichannel_predictor, Xs, y, groups=groups, 
                                     predict_method=self.transform_method_name, 
                                     cv=self.internal_cv, combine_splits=True, n_processes=self.cv_processes, 
                                     split_seed=None, fit_params=fit_params)
            scores = []
            for X_t in Xs_t:
                if X_t is not None and self.scorer is not None:
                    scores.append(self.scorer(y, X_t))
                else:
                    scores.append(X_t)
                                  
            if len(scores) > 0:
                self.scores_ = np.nanmean(scores)
                                  
        Xs_t = [X.reshape(-1, 1) if (X is not None and len(X.shape) == 1) else X for X in Xs_t]
        
        return Xs_t
    
def unwrap_predictor(pipe):
    """
    Return a predictor that is wrapped in a transform wrapper. 
    """
    if type(pipe) not in [SingleChannel, SingleChannelCV, Multichannel, MultichannelCV]:
        return pipe
    if type(pipe) in [Multichannel, MultichannelCV]:
        return pipe.multichannel_predictor
    else:
        return pipe.predictor
    
def unwrap_model(pipe):
    """
    Return a model that is wrapped in a transform wrapper. 
    """
    if type(pipe) not in [SingleChannel, SingleChannelCV, Multichannel, MultichannelCV]:
        return pipe
    if hasattr(pipe, 'model') == True:
        return pipe.model
    else:
        raise utils.FitError('no model found')