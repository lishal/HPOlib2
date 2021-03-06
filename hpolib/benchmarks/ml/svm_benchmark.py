import time

import numpy as np
from sklearn import svm
import scipy.sparse as sps
import ConfigSpace as CS

from hpolib.abstract_benchmark import AbstractBenchmark
import hpolib.util.data_manager
import hpolib.util.openml_data_manager
import hpolib


class SupportVectorMachine(AbstractBenchmark):
    """
        Hyperparameter optimization task to optimize the regularization
        parameter C and the kernel parameter gamma of a support vector machine.
        Both hyperparameters are optimized on a log scale in [-10, 10].

        The test data set is only used for a final offline evaluation of
        a configuration. For that the validation and training data is
        concatenated to form the whole training data set.
    """
    def __init__(self, rng=None):
        """

        Parameters
        ----------
        rng: int/None/RandomState
            set up rng
        """

        self.train, self.train_targets, self.valid, self.valid_targets, \
            self.test, self.test_targets = self.get_data()

        # Use 10 time the number of classes as lower bound for the dataset
        # fraction
        n_classes = np.unique(self.train_targets).shape[0]
        self.s_min = float(10 * n_classes) / self.train.shape[0]

        super(SupportVectorMachine, self).__init__()

        self.n_calls = 0

        if rng is None:
            self.rng = np.random.RandomState()
        else:
            self.rng = rng

    def get_data(self):
        raise NotImplementedError()

    @AbstractBenchmark._check_configuration
    @AbstractBenchmark._configuration_as_array
    def objective_function(self, x, dataset_fraction=1, **kwargs):
        start_time = time.time()

        # Shuffle training data
        shuffle = self.rng.permutation(self.train.shape[0])
        size = int(dataset_fraction * self.train.shape[0])

        print("training configuration: ",x," on sample size: ",size)
        # Split of dataset subset
        train = self.train[shuffle[:size]]
        train_targets = self.train_targets[shuffle[:size]]

        # Transform hyperparameters to linear scale
        C = np.exp(float(x[0]))
        gamma = np.exp(float(x[1]))

        # Train support vector machine
        clf = svm.SVC(gamma=gamma, C=C, random_state=self.rng)
        clf.fit(train, train_targets)

        # Compute validation error
        y = 1 - clf.score(self.valid, self.valid_targets)
        c = time.time() - start_time

        print("achieved validation error of ",y," after duration of ",c)
        return {'function_value': y, "cost": c}
    
    @AbstractBenchmark._check_configuration
    @AbstractBenchmark._configuration_as_array
    def objective_function_test(self, x, **kwargs):
        start_time = time.time()
        print(self.train.shape,self.valid.shape)
        print("training configuration: ",x," on combined training and validation")
        # Concatenate training and validation dataset
        if sps.issparse(self.train):
            dt = self.train.toarray()
            dv = self.valid.toarray()
            train = sps.csr_matrix(np.concatenate((dt,dv)))
        else:
            train = np.concatenate((self.train, self.valid),axis=0)
        train_targets = np.concatenate((self.train_targets, self.valid_targets))

        # Transform hyperparameters to linear scale
        C = np.exp(float(x[0]))
        gamma = np.exp(float(x[1]))

        # Train support vector machine
        clf = svm.SVC(gamma=gamma, C=C, random_state=self.rng)
        clf.fit(train, train_targets)

        # Compute test error
        y = 1 - clf.score(self.test, self.test_targets)
        c = time.time() - start_time

        print("achieved validation error of ",y," after duration of ",c)
        return {'function_value': y, "cost": c}

    @staticmethod
    def get_configuration_space():
        cs = CS.ConfigurationSpace()
        cs.generate_all_continuous_from_bounds(SupportVectorMachine.get_meta_information()['bounds'])
        return cs

    @staticmethod
    def get_meta_information():
        return {'name': 'Support Vector Machine',
                'bounds': [[-10, 10],  # C
                           [-10, 10]],  # gamma
                'references': ["@article{klein-corr16,"
                               "author = {A. Klein and S. Falkner and S. Bartels and P. Hennig and F. Hutter},"
                               "title = {Fast Bayesian Optimization of Machine Learning"
                               "Hyperparameters on Large Datasets},"
                               "journal = corr,"
                               "llvolume = {abs/1605.07079},"
                               "lurl = {http://arxiv.org/abs/1605.07079}, year = {2016} }"]
                }


class SvmOnMnist(SupportVectorMachine):

    def get_data(self):
        dm = hpolib.util.data_manager.MNISTData()
        return dm.load()

    @staticmethod
    def get_meta_information():
        d = SupportVectorMachine.get_meta_information()
        d["references"].append("@article{lecun-ieee98,"
                               "title={Gradient-based learning applied to document recognition},"
                               "author={Y. LeCun and L. Bottou and Y. Bengio and P. Haffner},"
                               "journal={Proceedings of the IEEE},"
                               "pages={2278--2324},"
                               "year={1998},"
                               "publisher={IEEE}"
                               )
        return d


class SvmOnVehicle(SupportVectorMachine):

    def get_data(self):
        #used to be 75191 which was incorrect
        dm = hpolib.util.openml_data_manager.OpenMLData(openml_task_id=75145)
        return dm.load()


class SvmOnCovertype(SupportVectorMachine):

    def get_data(self):
        dm = hpolib.util.openml_data_manager.OpenMLData(openml_task_id=75164)
        return dm.load()
