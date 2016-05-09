"""
Script that trains multitask tensorflow models on MUV dataset.
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os
import numpy as np
import shutil
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from deepchem.utils.save import load_from_disk
from deepchem.datasets import Dataset
from deepchem.featurizers.featurize import DataFeaturizer
from deepchem.featurizers.fingerprints import CircularFingerprint
from deepchem.splits import ScaffoldSplitter
from deepchem.splits import RandomSplitter
from deepchem.datasets import Dataset
from deepchem.transformers import BalancingTransformer
from deepchem.hyperparameters import HyperparamOpt
from deepchem.models.multitask import SingletaskToMultitask
from deepchem import metrics
from deepchem.metrics import Metric
from deepchem.metrics import to_one_hot
from deepchem.models.sklearn_models import SklearnModel
from deepchem.utils.evaluate import relative_difference
from deepchem.utils.evaluate import Evaluator
from deepchem.models.tensorflow_models.fcnet import TensorflowMultiTaskClassifier
from deepchem.models.tensorflow_models import TensorflowModel


np.random.seed(123)

# Set some global variables up top
reload = True
verbosity = "high"

# Create some directories for analysis
# The base_dir holds the results of all analysis
#base_dir = "/scratch/users/rbharath/muv_multitask_analysis"
base_dir = "/scratch/users/rbharath/small_muv_multitask_analysis"
current_dir = os.path.dirname(os.path.realpath(__file__))
#Make directories to store the raw and featurized datasets.
feature_dir = os.path.join(base_dir, "features")
samples_dir = os.path.join(base_dir, "samples")
full_dir = os.path.join(base_dir, "full_dataset")
train_dir = os.path.join(base_dir, "train_dataset")
train_dir2 = os.path.join(base_dir, "train_dataset_2")
valid_dir = os.path.join(base_dir, "valid_dataset")
test_dir = os.path.join(base_dir, "test_dataset")
model_dir = os.path.join(base_dir, "model")

# Remove existing model directory since TF doesn't overwrite by default...
if os.path.exists(model_dir):
  shutil.rmtree(model_dir)
os.makedirs(model_dir)

# Load MUV dataset
print("About to load MUV dataset.")
dataset_file = os.path.join(
    current_dir, "../datasets/muv.csv.gz")
dataset = load_from_disk(dataset_file)
print("Columns of dataset: %s" % str(dataset.columns.values))
print("Number of examples in dataset: %s" % str(dataset.shape[0]))

# Featurize MUV dataset
print("About to featurize MUV dataset.")
featurizers = [CircularFingerprint(size=1024)]
MUV_tasks = sorted(['MUV-692', 'MUV-689', 'MUV-846', 'MUV-859', 'MUV-644',
                    'MUV-548', 'MUV-852', 'MUV-600', 'MUV-810', 'MUV-712',
                    'MUV-737', 'MUV-858', 'MUV-713', 'MUV-733', 'MUV-652',
                    'MUV-466', 'MUV-832'])
# For debugging purposes
MUV_tasks = MUV_tasks[0:1]
print("Using following tasks")
print(MUV_tasks)
featurizer = DataFeaturizer(tasks=MUV_tasks,
                            smiles_field="smiles",
                            compound_featurizers=featurizers,
                            verbosity="low")
featurized_samples = featurizer.featurize(
    dataset_file, feature_dir,
    samples_dir, shard_size=8192,
    reload=reload)

assert len(featurized_samples) == len(dataset)
# Train/Valid/Test Split dataset
#print("About to perform train/valid/test split.")
#splitter = RandomSplitter(verbosity=verbosity)
#frac_train, frac_valid, frac_test = .8, .1, .1
#train_samples, valid_samples, test_samples = \
#    splitter.train_valid_test_split(
#        featurized_samples, train_dir, valid_dir, test_dir,
#        log_every_n=1000, reload=reload)
#
#len_train_samples, len_valid_samples, len_test_samples = \
#  len(train_samples), len(valid_samples), len(test_samples)
#assert relative_difference(
#    len(train_samples), frac_train * len(featurized_samples)) < 1e-3
#assert relative_difference(
#    len(valid_samples), frac_valid * len(featurized_samples)) < 1e-3
#assert relative_difference(
#    len(test_samples), frac_test * len(featurized_samples)) < 1e-3

# Generate datasets
print("About to create datasets")
print("MUV_tasks")
print(MUV_tasks)
full_dataset = Dataset(data_dir=full_dir, samples=featurized_samples, 
                        featurizers=featurizers, tasks=MUV_tasks,
                        verbosity=verbosity, reload=reload)
print("len(full_dataset)")
print(len(full_dataset))
# Do train/valid split.
#num_train = 2048
#num_train = 4096
#num_train = 8192
num_train = 12800 
#num_train = 13000
#num_train = 16384 ## BROKEN
num_valid = 1024
X, y, w, ids = full_dataset.to_numpy()

w_flat = w.flatten()
#y_flat = y.flatten()


####### DEBUG
#    num_nonzero = np.count_nonzero(y)
#    weight_nonzero = len(y)/num_nonzero
#    print("weight_nonzero")
#    print(weight_nonzero)
#    w[y_flat != 0] = weight_nonzero
####### DEBUG

X, y, w, ids = X[w_flat != 0], y[w_flat != 0], w[w_flat != 0], ids[w_flat != 0]
print("Shape after removing zeros")
print("X.shape")
print(X.shape)
X_train, X_valid = X[:num_train], X[num_train:num_train+num_valid]
y_train, y_valid = y[:num_train], y[num_train:num_train+num_valid]
w_train, w_valid = w[:num_train], w[num_train:num_train+num_valid]
ids_train, ids_valid = ids[:num_train], ids[num_train:num_train+num_valid]


if os.path.exists(train_dir):
  shutil.rmtree(train_dir)
train_dataset = Dataset.from_numpy(train_dir, MUV_tasks, X_train, y_train,
                                   w_train, ids_train)
print("len(train_dataset)")
print(len(train_dataset))
if os.path.exists(valid_dir):
  shutil.rmtree(valid_dir)
valid_dataset = Dataset.from_numpy(valid_dir, MUV_tasks, X_valid, y_valid,
                                   w_valid, ids_valid)
print("len(valid_dataset)")
print(len(valid_dataset))

#y = full_dataset.get_labels()
#train_dataset = Dataset(data_dir=train_dir, samples=train_samples, 
#                        featurizers=featurizers, tasks=MUV_tasks,
#                        verbosity=verbosity, reload=reload)
#y_train  = train_dataset.get_labels()
#
#X_train, y_train, w_train, ids_train = train_dataset.to_numpy()
#w_flat = w_train.flatten()
#X_train = X_train[w_flat != 0]
#y_train = y_train[w_flat != 0]
#ids_train = ids_train[w_flat != 0]
#w_train = w_train[w_flat != 0]
######
#w_train = np.ones_like(w_train)
######
#train_dataset = Dataset.from_numpy(train_dir2, MUV_tasks, X_train, y_train,
#                                   w_train, ids_train)
#y_train  = train_dataset.get_labels()
#
#valid_dataset = Dataset(data_dir=valid_dir, samples=valid_samples, 
#                        featurizers=featurizers, tasks=MUV_tasks,
#                        verbosity=verbosity, reload=reload)
#y_valid = valid_dataset.get_labels()
#test_dataset = Dataset(data_dir=test_dir, samples=test_samples, 
#                       featurizers=featurizers, tasks=MUV_tasks,
#                       verbosity=verbosity, reload=reload)
#y_test = test_dataset.get_labels()
#len_train_dataset, len_valid_dataset, len_test_dataset = \
#  len(train_dataset), len(valid_dataset), len(test_dataset)

transformers = []

# Fit tensorflow models
MUV_task_types = {task: "Classification" for task in MUV_tasks}
classification_metric = Metric(metrics.roc_auc_score, np.mean,
                               verbosity=verbosity,
                               mode="classification")
params_dict = { 
    "batch_size": 128,
    #"batch_size": 5120,
    "nb_epoch": 50,
    "data_shape": train_dataset.get_data_shape(),
    "layer_sizes": [1000],
    "weight_init_stddevs": [1.],
    "bias_init_consts": [1.],
    "dropouts": [.25],
    "num_classification_tasks": len(MUV_tasks),
    "num_classes": 2,
    "penalty": .0,
    "optimizer": "adam",
    "learning_rate": .0003,
}   

model = TensorflowModel(MUV_tasks, MUV_task_types, params_dict, model_dir,
                        tf_class=TensorflowMultiTaskClassifier,
                        verbosity=verbosity)


# Fit trained model
model.fit(train_dataset)
model.save()

############# DEBUG
#import sklearn
#y_train_pred_proba = np.squeeze(model.predict_proba(train_dataset))
#y_train = train_dataset.get_labels()
#w_train = train_dataset.get_weights()
#print("y_train.shape, y_train_pred_proba.shape")
#print(y_train.shape, y_train_pred_proba.shape)
#print("sklearn.metrics.roc_auc_score(to_one_hot(y_train), y_train_pred_proba)")
#print(sklearn.metrics.roc_auc_score(to_one_hot(y_train), y_train_pred_proba))
#print("sklearn.metrics.roc_auc_score(to_one_hot(y_train), y_train_pred_proba, sample_weight=w_train)")
#print(sklearn.metrics.roc_auc_score(to_one_hot(y_train), y_train_pred_proba, sample_weight=w_train))
############# DEBUG

train_evaluator = Evaluator(model, train_dataset, transformers, verbosity=verbosity)
train_scores = train_evaluator.compute_model_performance([classification_metric])

print("Train scores")
print(train_scores)

valid_evaluator = Evaluator(model, valid_dataset, transformers, verbosity=verbosity)
valid_scores = valid_evaluator.compute_model_performance([classification_metric])

print("Validation scores")
print(valid_scores)