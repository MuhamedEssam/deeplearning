import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# data parsing
headers = ['buying','maint','doors','persons','lug_boot','safety','class']
df = pd.read_csv('car.data.txt', names=headers)
cleanup_nums = {'buying': {'vhigh': 0, 'high': 1, 'med': 2, 'low': 3},
                'maint': {'vhigh': 0, 'high': 1, 'med': 2, 'low': 3},
                'doors': {'2': 2, '3': 3, '4': 4, '5more': 5},
                'persons': {'2': 2, '3': 3, '4': 4, 'more': 5},
                'lug_boot': {'small': 0, 'med': 1, 'big': 2},
                'safety': {'low': 0, 'med': 1, 'high': 2},
                'class': {'unacc': 0, 'acc': 1, 'good': 2, 'vgood' : 3}}
df.replace(cleanup_nums, inplace=True)

def make_one_hot(x): 
  n_values = np.max(x) + 1
  x = np.eye(n_values)[x].astype('float32')
  return x
data_y = make_one_hot(np.array(df['class']))
data_X = np.array(df.drop('class', axis=1))

# sep training and testing data
X_train, X_test, y_train, y_test = train_test_split(data_X, data_y, test_size=0.2)

class dnn:
    def __init__(
        self,
        n_features,
        n_classes,
        n_layers=3,
        batch_size=100,
        learning_rate=0.01,
        n_epochs=50

        ):
        self.n_features = n_features
        self.n_classes = n_classes
        self.n_layers = n_layers
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.n_epochs = n_epochs

        self.n_nodes_list = n_layers*[500]
        self.x = tf.placeholder(dtype=tf.float32, shape=[None, self.n_features])
        self.y = tf.placeholder(dtype=tf.float32, shape=[None, self.n_classes])

    # returns rensorflow variable of desired shape
    def get_variable(self, shape):
        return tf.Variable(tf.random_normal(shape))

    def model(self, data):
        n_nodes_prev_layer = self.n_features
        prev_layer = data
        for i in range(self.n_layers):
            weights = self.get_variable([n_nodes_prev_layer, self.n_nodes_list[i]])
            biases = self.get_variable([self.n_nodes_list[i]])
            layer = tf.add(tf.matmul(prev_layer, weights), biases)
            layer = tf.nn.relu(layer)
            n_nodes_prev_layer = self.n_nodes_list[i]
            prev_layer = layer

        # weights and biases for output
        weights = self.get_variable(
            [self.n_nodes_list[len(self.n_nodes_list) - 1], self.n_classes])
        biases = self.get_variable([self.n_classes])
        layer = tf.add(tf.matmul(prev_layer, weights), biases)
        return layer

    def train(self, featureset):
        model = self.model(featureset)
        cost_function = tf.reduce_mean(
            tf.nn.softmax_cross_entropy_with_logits(labels=self.y, logits=model))
        optimizer = tf.train.AdamOptimizer(self.learning_rate).minimize(cost_function)


        init = tf.global_variables_initializer()

        with tf.Session() as sess:
            sess.run(init)

            for i in range(1, self.n_epochs+1):
                avg_cost = 0


                sess.run(optimizer, feed_dict = {self.x: X_train, self.y: y_train})

                avg_cost += sess.run(cost_function, feed_dict={self.x: X_train, self.y: y_train})

            print('epoch', i, 'complete')
            predictions = tf.equal(tf.argmax(model, 1), tf.argmax(self.y, 1))
            accuracy = tf.reduce_mean(tf.cast(predictions, 'float'))
            print('accuracy:', accuracy.eval({self.x : X_test, self.y: y_test}))
        print(':)')


d = dnn(6, 4)
x = d.x
d.train(x)


