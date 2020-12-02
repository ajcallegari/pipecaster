import ray
import numpy as np
import unittest
import multiprocessing
import warnings
import timeit

from sklearn.datasets import make_classification, make_regression
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.metrics import roc_auc_score, explained_variance_score, make_scorer
from sklearn.model_selection import KFold

import sklearn.model_selection as sk_model_selection
import pipecaster.model_selection as pc_model_selection
from pipecaster.pipeline import Pipeline

test_seed = None

try:
    ray.nodes()
except RuntimeError:
    ray.init()
    
n_cpus = multiprocessing.cpu_count()

class TestCrossValScore(unittest.TestCase):
    
    def setUp(self):
        # get positive control values from sklearn cross_val_score selection
        
        # classification
        self.cv = KFold(n_splits=5)
        clf = KNeighborsClassifier(n_neighbors=5, weights='uniform')
        self.clf = clf
        self.X_cls, self.y_cls = make_classification(n_classes=2, n_samples=500, n_features=40, 
                                                     n_informative=20, random_state=test_seed)
        self.cls_scores = sk_model_selection.cross_val_score(clf, self.X_cls, self.y_cls, 
                                                             scoring=make_scorer(roc_auc_score), 
                                                             cv=self.cv, n_jobs=1)
        
        rgr = KNeighborsRegressor(n_neighbors=5, weights='uniform')
        self.rgr = rgr
        self.X_rgr, self.y_rgr = make_regression(n_targets=1, n_samples = 500, n_features=40, 
                                                 n_informative=20, random_state=test_seed)
        self.rgr_scores = sk_model_selection.cross_val_score(rgr, self.X_rgr, self.y_rgr, 
                                                             scoring=make_scorer(explained_variance_score), 
                                                             cv=self.cv, n_jobs=1)
        
    def test_single_input_classification(self):
        pc_scores = pc_model_selection.cross_val_score(self.clf, self.X_cls, self.y_cls, scorer=roc_auc_score,
                                                       cv=self.cv, n_jobs=1)  
        self.assertTrue(np.array_equal(self.cls_scores, pc_scores), 'classifier scores from pipecaster.model_selection.cross_val_score did not match sklearn control (single input predictor)')
        
    def test_multi_input_classification(self):
        mclf = Pipeline(n_inputs=1)
        mclf.get_next_layer()[:] = self.clf   
        pc_scores = pc_model_selection.cross_val_score(mclf, [self.X_cls], self.y_cls, scorer=roc_auc_score,
                                                       cv=self.cv, n_jobs=1) 
        self.assertTrue(np.array_equal(self.cls_scores, pc_scores), 'classifier scores from pipecaster.model_selection.cross_val_score did not match sklearn control (multi input predictor)')
        
    def test_multi_input_classification_parallel(self):
        mclf = Pipeline(n_inputs=1)
        mclf.get_next_layer()[:] = self.clf   
        pc_scores = pc_model_selection.cross_val_score(mclf, [self.X_cls], self.y_cls, scorer=roc_auc_score,
                                                       cv=self.cv, n_jobs=n_cpus) 
        self.assertTrue(np.array_equal(self.cls_scores, pc_scores), 'classifier scores from pipecaster.model_selection.cross_val_score did not match sklearn control (multi input predictor)')
                                                                    
    def test_single_input_regression(self):
        pc_scores = pc_model_selection.cross_val_score(self.rgr, self.X_rgr, self.y_rgr, scorer=explained_variance_score,
                                                       cv=self.cv, n_jobs=1)  
        self.assertTrue(np.array_equal(self.rgr_scores, pc_scores), 'regressor scores from pipecaster.model_selection.cross_val_score did not match sklearn control (single input predictor)')

    def test_multi_input_regression(self):
        mrgr = Pipeline(n_inputs=1)
        mrgr.get_next_layer()[:] = self.rgr  
        pc_scores = pc_model_selection.cross_val_score(mrgr, [self.X_rgr], self.y_rgr, scorer=explained_variance_score, 
                                                       cv=self.cv, n_jobs=1) 
        self.assertTrue(np.array_equal(self.rgr_scores, pc_scores), 'regressor scores from pipecaster.model_selection.cross_val_score did not match sklearn control (multi input predictor)')
        
    def test_multi_input_regression_parallel(self):
        mrgr = Pipeline(n_inputs=1)
        mrgr.get_next_layer()[:] = self.rgr  
        pc_scores = pc_model_selection.cross_val_score(mrgr, [self.X_rgr], self.y_rgr, scorer=explained_variance_score,
                                                       cv=self.cv, n_jobs=n_cpus) 
        self.assertTrue(np.array_equal(self.rgr_scores, pc_scores), 'regressor scores from pipecaster.model_selection.cross_val_score did not match sklearn control (multi input predictor)')
       
    def test_multiprocessing_speedup(self):
        X, y = self.X_cls, self.y_cls
        
        mclf = Pipeline(n_inputs=1)
        mclf.get_next_layer()[:] = self.clf   

        if n_cpus > 1:
            # shut off warnings because ray and redis generate massive numbers
            warnings.filterwarnings("ignore")
            
            SETUP_CODE = ''' 
import pipecaster.model_selection'''
            TEST_CODE = ''' 
pipecaster.model_selection.cross_val_score(mclf, [X], y, cv = 5, n_jobs = 1)'''
            t_serial = timeit.timeit(setup = SETUP_CODE, 
                                  stmt = TEST_CODE, 
                                  globals = locals(), 
                                  number = 5) 
            TEST_CODE = ''' 
pipecaster.model_selection.cross_val_score(mclf, [X], y, cv = 5, n_jobs = {})'''.format(n_cpus)
            t_parallel = timeit.timeit(setup = SETUP_CODE, 
                                  stmt = TEST_CODE, 
                                  globals = locals(), 
                                  number = 5) 
            
            warnings.resetwarnings()
    
            if t_serial <= t_parallel:
                warnings.warn('mulitple cpus detected, but parallel cross_val_score not faster than serial, possible problem with multiprocessing')
                
if __name__ == '__main__':
    unittest.main()