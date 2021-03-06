# Introduction
Pipecaster is a Python library for building multichannel machine learning pipeline.  Pipecaster pipelines are "multichannel" in that they take multiple inputs that can be maintained in separate siloes during processing and combined through concatenation, voting, and meta-prediction.  

and have a number of in-pipeline workflow automations.  The pipeline construction workflow is designed to help manage complex architectures and is loosely based on Keras layers: pipelines are built layer by layer with visual feedback.  The current version supports algorithms with the scikit-learn estimator/transformer/predictor interfaces.

tutorial: https://github.com/ajcallegari/pipecaster/blob/master/tutorial.ipynb

![Use case 1](/images/tutorial_1.2.svg)

## What is multichannel machine learning?

ML pipelines often combine multiple input feature vectors derived from different data sources or feature extraction/engineering methods.  In these instances, the best performance is not always obtained by concatenating feature vectors into a single input vector.  Better accuracy can sometimes be obtained by **(1)** selecting the highest quality vectors or **(2)** training different ML models on each vector and making ensemble predictions (fig. 1).  In both cases, the different inputs are kept in separate channels for one or more data processing steps before the channels converge to make a single prediction.  Pipeline architectures with multiple I/O channels, which form the basis of pipecaster, are referred to as **"multichannnel pipelines"**.

![figure 1.](/images/performance_comparison.png)  
**figure 1**. Performance results from example 1.1 in [tutorial.ipynb](https://github.com/ajcallegari/pipecaster/blob/master/tutorial.ipynb).  

The **MultichannelPipeline** class simplifies the construction of multichannel architectures, making it easy to create wide pipelines (many inputs) by broadcasting construction operations across multiple input channels, and deep pipelines (many layers and model stacks) with a layer-by-layer construction workflow and support for automatic internal cross validation training (1).  
(1) Wolpert, David H. "Stacked generalization." Neural networks 5.2 (1992): 241-259.

MultichannelPipeline has the familiar scikit-learn estimator/transformer/predictor interfaces but its methods take a list of input matrices rather than a single matrix.  The pipeline illustrated in the graphic above can be constructed, tested, and deployed with the following code:
```
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectPercentile, f_classif
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.svm import SVC
import pipecaster as pc

# build the multichannel pipeline from the graphic above
clf = pc.MultichannelPipeline(n_channels=10)
clf.add_layer(StandardScaler())
clf.add_layer(SelectPercentile(percentile=25))
clf.add_layer(pc.SelectKBestScores(feature_scorer=f_classif,
                                     aggregator=np.mean, k=3))
clf.add_layer(GradientBoostingClassifier())
clf.add_layer(pc.MultichannelPredictor(SVC()))

# cross validate:
pc.cross_val_score(clf, Xs, y)

# train:
clf.fit(Xs_train, y_train)

# predict:
clf.predict(Xs)
```

## What is semi-auto-ML?
A typical ML workflow involves screening input sources, feature extraction & engineering steps, ML algorithms, and model hyperparameters.  Pipecaster allows you to semi-automate each of these screening tasks by including them in the ML pipeline and executing the screens during calls to pipeline.fit().  This can be useful when you are developing a large number of different pipelines in parallel and don't have time to optimize each one separately, and it may accelerate ML workflows in general.  

Relevant classes: **SelectiveStack**, **GridSearchStack**,  **SelectKBestScores**, **SelectKBestPerformers**, **SelectKBestModels**, **SelectKBestProbes**

## fast distributed computing with ray
Pipecaster uses the ray library to speed up multiprocessing by passing arguments through a distributed in-memory object store without the usual serialization/deserialization overhead and without passing the same object multiple times when needed by multiple jobs.  Ray also enables pipecaster to rapidly distribute jobs among networked computers.

## install pipecaster

`git clone https://github.com/ajcallegari/pipecaster.git`  
`cd pipecaster`  
`pip install .`

pipecaster was developed with Python 3.7.5 and was tested with the following dependencies:
```
numpy==1.17.2
joblib==0.16.0
ray==1.1.0
scipy==1.3.1
pandas==0.24.2
scikit-learn==0.23.2
```

**Acknowledgments** Most of the ML concepts that motivated the development of pipecaster came up in fascinating conversations with [Ilya Goldberg](https://github.com/igg) and [Josiah Johnston](https://github.com/josiahjohnston).
