import os
import sys
import utils
import numpy as np
import tensorflow as tf

class Network(object):
    # My Concern is that some of these activation function might be numerically unstable due to the implementation
    # tf.log(1+exp(x)) is one of these things
    unary = {1:lambda x:x ,2:lambda x: -x, 3: tf.abs, 4:lambda x : tf.pow(x,2),5:lambda x : tf.pow(x,3),
      6:tf.sqrt,7:lambda x: tf.Variable(tf.truncated_normal([1], stddev=0.08))*x,
      8:lambda x : x + tf.Variable(tf.truncated_normal([1], stddev=0.08)),9:lambda x: tf.log(tf.abs(x)+10e-8),
      10:tf.exp,11:tf.sin,12:tf.sinh,13:tf.cosh,14:tf.tanh,15:tf.asinh,16:tf.atan,17:lambda x: tf.sin(x)/x,
      18:lambda x : tf.maximum(x,0),19:lambda x : tf.minimum(x,0),20:tf.sigmoid,21:lambda x:tf.log(1+tf.exp(x)),
      22:lambda x:tf.exp(-tf.pow(x,2)),23:tf.erf,24:lambda x: tf.Variable(tf.truncated_normal([1], stddev=0.08))}

    binary = {1:lambda x,y: x+y,2:lambda x,y:x*y,3:lambda x,y:x-y,4:lambda x,y:x/(y+10e-8),
    5:lambda x,y:tf.maximum(x,y),6:lambda x,y: tf.sigmoid(x)*y,7:lambda x,y:tf.exp(-tf.Variable(tf.truncated_normal([1], stddev=0.08))*tf.pow(x-y,2)),
    8:lambda x,y:tf.exp(-tf.Variable(tf.truncated_normal([1], stddev=0.08))*tf.abs(x-y)),
    9:lambda x,y: tf.Variable(tf.truncated_normal([1], stddev=0.08))*x + (1-tf.Variable(tf.truncated_normal([1], stddev=0.08)))*y}

    def __init__(self, config):
        self.config = config
        self.n_steps = self.config.hyperparams
        self.n_input, self.n_hidden =  4, 2
        self.state = tf.Variable(tf.random_normal(shape=[1, 4]))
        self.lstm = tf.contrib.rnn.BasicLSTMCell(self.n_hidden, forget_bias=1.0, state_is_tuple=False)
        self.Wc, self.bc = self.init_controller_vars()

    def weight_variable(self, shape, name):
        return tf.Variable(tf.random_normal(shape=shape), name=name)

    def bias_variable(self, shape, name):
        return tf.Variable(tf.random_normal(shape=shape), name=name)

    def init_controller_vars(self):
        Wc = self.weight_variable(shape=[self.n_hidden, self.n_input], name="w_controller")
        bc = self.bias_variable(shape=[self.n_input], name="b_controller")
        return Wc, bc

    def neural_search(self):
        inp = tf.constant(np.ones((1, 4), dtype="float32"))
        output = list()
        for _ in range(self.n_steps):
            inp, self.state = self.lstm(inp, self.state)
            inp = tf.nn.softmax(tf.matmul(inp, self.Wc) + self.bc)
            output.append(inp[0, :])
        out = [utils.max(output[i]) for i in range(self.n_steps)]
        return out, output[-1]

    def gen_hyperparams(self, output):
        filter_dims = tf.constant([3, 5, 7, 9], dtype=tf.int32)
        n_filters = tf.constant([24, 36, 48, 64], dtype=tf.int32)
        strides = tf.constant([1, 2, 3, 4], dtype=tf.int32)
        hyperparams = [1 for _ in range(self.n_steps)]
        # Change the following based on number of hyperparameters to be predicted
        # Removing strides for now
        hyperparams[0], hyperparams[1] = filter_dims[output[0]], filter_dims[output[1]]
        hyperparams[2] = n_filters[output[2]]  # Layer 1
        hyperparams[3], hyperparams[4] = filter_dims[output[3]], filter_dims[output[5]]
        hyperparams[5] = n_filters[output[5]]  # Layer 2
        hyperparams[6], hyperparams[7] = filter_dims[output[6]], filter_dims[output[7]]
        hyperparams[8] = n_filters[output[8]] # Layer 3
        hyperparams[9] = n_filters[output[9]] # FNN Layer
        return hyperparams

    def REINFORCE(self, prob):
        loss = tf.reduce_mean(tf.log(prob)) # Might have to take the negative
        return loss

    def train_controller(self, reinforce_loss, val_accuracy):
        #Adam was used to train the RNN controller Bello et al 2017
        learning_rate = 1e-5 #As per Bello et al 2017
        optimizer = tf.train.AdamOptimizer(learning_rate)
        var_list = [self.Wc, self.bc]
        gradients = optimizer.compute_gradients(loss=reinforce_loss, var_list=var_list)
        for i, (grad, var) in enumerate(gradients):
            if grad is not None:
                gradients[i] = (grad * val_accuracy, var)
        return optimizer.apply_gradients(gradients)