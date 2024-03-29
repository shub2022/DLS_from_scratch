# -*- coding: utf-8 -*-
"""optimizer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/shub2022/Optimizers_DLS/blob/main/code/optimizer.ipynb
"""



from csv_data import HousePricesDatasetWrapper

wrapper = HousePricesDatasetWrapper()
train_data, valid_data, test_data = wrapper.get_flat_datasets()

# Show the train predictors
train_data[0][:2]

# Show the train target
train_data[1][:2]

# Defining a class for creating Dense layers
import math
import numpy as np

class Dense():
  def __init__(self,input_size,output_size,activation=True,seed=0): # Activation always set as true, set seed as zero for initializing random weight matrices
    self.add_activation=activation
    self.hidden=None
    self.prev_hidden=None # Hidden and previous hidden will be eventually used for creating a "Fully Connected Dense Neural Network"
    # Will be using ReLu activation function hence using LeCun Normal intializing strategy for weight matrices
    np.random.seed(seed)
    k=math.sqrt(1/input_size)
    self.weights = (k**2) * np.random.randn(input_size,output_size) + 0

    # Intializing bias to 1
    self.bias=np.ones((1,output_size))

  # Defining forward propagation function
  def forward(self,x):
    self.prev_hidden=x.copy()
    x=np.matmul(x,self.weights) + self.bias

    if self.add_activation:
      x=np.maximum(x,0)

    self.hidden=x.copy()
    return x

  # Defining the backward propagation function
  def backward(self,grad): # Grad is the gradient for the current layer
    # Undo ing the activation function (ReLu)
    if self.add_activation:
      grad = np.multiply(grad, np.heaviside(self.hidden, 0))

    # Calculating the weight and bias gradient
    w_grad=self.prev_hidden.T @ grad
    b_grad = np.mean(grad, axis=0)
    param_grads = [w_grad, b_grad]

    grad= grad @ self.weights.T
    return param_grads, grad

  # defining function to update the weights based on the gradient

  def update(self,w_grad,b_grad):
    self.weights += w_grad
    self.bias += b_grad

# 3 layer neural network - 7 inputs (dimension) making 25 hidden features, second layer makes 10 hidden features and then the last layer gives one output
layers = [
    Dense(7, 25),
    Dense(25, 10),
    Dense(10, 1, activation=False)
]

# Now creating a neural network

def forward(x, layers):
    # Loop through each layer
    for layer in layers:
        # Run the forward pass
        x = layer.forward(x)
    return x

def backward(grad, layers):
    # Save the gradients for each layer
    layer_grads = []
    # Loop through each layer in reverse order (starting from the output layer)
    for layer in reversed(layers):
        # Get the parameter gradients and the next layer gradient
        param_grads, grad = layer.backward(grad)
        layer_grads.append(param_grads)
    return layer_grads

import matplotlib.pyplot as plt
import numpy as np

class Optimizer():
    def __init__(self):
        self.w_vals = []
        self.final_weights = None

    def save_vector(self, layers):
        # Do SVD on the matrix to get singular values
        _, singular, _ = np.linalg.svd(layers[-1].weights)
        # Add the final layer singular value to the list
        self.w_vals.append(singular[0]) # Appending the highest singular value, singular value can be used for deciding the learning rate. High SV means high gradient and LR should be low
        self.final_weights = layers[-1].weights

    def plot_path(self):
        indices = np.linspace(0, len(self.w_vals)-1, 500, dtype=int)
        y = [self.w_vals[i] for i in indices]
        x = [i for i in range(len(y))]

        # Plot how the final layer singular value changes over time
        plt.scatter([x[0]], [y[0]], color='red')
        plt.scatter([x[-1]], [y[-1]], color='green')
        plt.plot(x, y)
        plt.show()

    def plot_final_weights(self):
        # flatten the final weights into a 1D array
        final_weights = self.final_weights.ravel()
        x = [i for i in range(final_weights.shape[0])]
        plt.bar(x, final_weights)
        plt.show()

class Scheduler():
    def __init__(self):
        pass

    def __call__(self):
        pass

    def plot_lr(self):
        x = np.linspace(0, self.total_steps, 500, dtype=int)
        y = [self(i) for i in x]
        plt.plot(x, y)
        plt.show()

# Now,building the SGD optimizer

class SGD(Optimizer):
  def __init__(self,lr):
    self.lr=lr
    super().__init__()

  def __call__(self,layer_grads,layers,batch_size,step):
    for layer_grad, layer in zip(layer_grads,reversed(layers)):
      w_grad,b_grad=layer_grad

      # Normalize the weight gradient by batch size (bias gradient is already normalized)
      w_grad/=batch_size

      # Calculating the new weights
      w_update= -self.lr * w_grad
      b_update= -self.lr * b_grad

      layer.update(w_update,b_update)


    # Saving only for the first layers (weight and singular values) -- will generate a graph later on

    self.save_vector(layers)


import wandb
wandb.login()

# Commented out IPython magic to ensure Python compatibility.
import time
# %env WANDB_SILENT=False
def training_run(epochs, batch_size, optimizer, train_data, valid_data, name=None):
    # Initialize a new W&B run, with the right parameters
    wandb.init(project="optimizers",
               name=name,
               config={"batch_size": batch_size,
                       "lr": optimizer.lr,
                       "epochs": epochs,
                       "optimizer": type(optimizer).__name__})

    # Setup the metrics we want to track with wandb.  You usually don't need to do this, but we want a custom axis for each metric.
    wandb.define_metric("batch_step") # This will ensure that results from runs with different batch sizes line up
    wandb.define_metric("epoch") # This will ensure that results from runs with different batch sizes line up
    wandb.define_metric("valid_loss", step_metric="epoch") # The step metric is the x-axis scale
    wandb.define_metric("train_loss", step_metric="epoch")
    wandb.define_metric("runtime", step_metric="epoch")
    wandb.define_metric("running_loss", step_metric="batch_step")

    # Setup the layers for the training run
    layers = [
        Dense(7, 25),
        Dense(25,10),
        Dense(10, 1, activation=False)
    ]

    # Split the training and valid data into x and y
    train_x, train_y = train_data
    valid_x, valid_y = valid_data

    for epoch in range(epochs):
        running_loss = 0
        start = time.time() # The start time of our run

        for i in range(0, len(train_x), batch_size):
            # Get the x and y batches
            x_batch = train_x[i:(i+batch_size)]
            y_batch = train_y[i:(i+batch_size)]
            # Make a prediction
            pred = forward(x_batch, layers)

            # Run the backward pass
            loss = pred - y_batch
            layer_grads = backward(loss, layers)

            # Run the optimizer
            step_count = (i + batch_size) // batch_size + epoch * len(train_x) // batch_size
            optimizer(layer_grads, layers, batch_size, step_count)

            # Update running loss
            running_loss += np.mean(loss ** 2)

            batch_idx = i + batch_size # Get the last index of the current batch
            batch_step = batch_idx + epoch * len(train_x)
            # Log running loss.  We multiply by batch size to offset the mean from earlier.
            wandb.log({"running_loss": running_loss / batch_idx * batch_size, "batch_step": batch_step})

        # Calculate and log validation loss
        valid_preds = forward(valid_x, layers)
        valid_loss = np.mean((valid_preds - valid_y) ** 2)
        train_loss = running_loss / len(train_x) * batch_size
        wandb.log({
            "valid_loss": valid_loss,
            "epoch": epoch,
            "train_loss": train_loss,
            "runtime": time.time() - start
        })

    # Mark the run as complete
    wandb.finish()

# Setup our parameters
epochs = 10
batch_size = 4
lr = 1e-4

# Run our training loop
sgd = SGD(lr=lr)
training_run(epochs, batch_size, sgd, train_data, valid_data, name="sgd_small")

# Plot the path of the weights over time.
sgd.plot_path()

# Below is the plot of the singular value of the final layer weight over time. Showing the need of a dynamic learning rate

# Setup our parameters
epochs = 40 # higher number of epochs so total steps are equal for comparison purposes
batch_size = 16
lr = 1e-4

# Run our training loop
sgd = SGD(lr=lr)
training_run(epochs, batch_size, sgd, train_data, valid_data, name="sgd_large")
sgd.plot_path()

# Now using momentum for gradient descent

class SGDMomentum(Optimizer):
  def __init__(self,lr, beta): # Have a new hyperparameter called beta (decay term)
    self.lr=lr
    self.beta=beta
    # Making another matrix momentum
    self.momentums=None
    super().__init__()

  def initialize_momentums(self,layer_grads):
    self.momentums=[]

    # Initialize momentums to have the same shape as their parameters for each layer

    for layer_grad in layer_grads:
      w_grad,b_grad=layer_grad
      initial_momentums=[np.zeros_like(w_grad),np.zeros_like(b_grad)]
      self.momentums.append(initial_momentums)

  # Defining the call function now

  def __call__(self,layer_grads,layers,batch_size,step):

    if self.momentums is None:
      self.initialize_momentums(layer_grads)

    new_momentums=[]

    for layer_grad, layer, momentum in zip(layer_grads,reversed(layers),self.momentums):
      w_grad,b_grad=layer_grad
      w_vel, b_vel = momentum

      # Normalize the weight gradient by batch size (bias gradient is already normalized)
      w_grad/=batch_size

      # Calculating the new weights
      w_vel= w_vel * self.beta  -self.lr * w_grad
      b_vel= b_vel * self.beta -self.lr * b_grad

      layer.update(w_vel,b_vel)
      new_momentums.append([w_vel, b_vel])



    # Saving only for the first layers (weight and singular values) -- will generate a graph later on
    self.momentums=new_momentums
    self.save_vector(layers)

# Setup our parameters
epochs = 40
batch_size = 16
lr = 1e-4
beta = .9

# Run our training loop
sgd = SGDMomentum(lr, beta)
training_run(epochs, batch_size, sgd, train_data, valid_data, name="sgd_momentum")
sgd.plot_path()

# Adam optimizer

from copy import deepcopy

class Adam(Optimizer):
    def __init__(self, lr, beta1, beta2, eps, decay):
        # Track hyperparameters
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.decay = decay

        # Track first and secone moment
        self.moments = None

        super().__init__()

    def initialize_moments(self, layer_grads):
        self.moments = []
        for layer_grad in layer_grads:
            w_grad, b_grad = layer_grad
            # Initialize arrays to hold first moment values
            moment1 = [np.zeros_like(w_grad), np.zeros_like(b_grad)]
            moment2 = deepcopy(moment1)
            self.moments.append([moment1, moment2])

    def __call__(self, layer_grads, layers, batch_size, step):
        if self.moments is None:
            self.initialize_moments(layer_grads)

        new_moments = []
        for layer_grad, moment, layer in zip(layer_grads, self.moments, reversed(layers)):
            w_grad, b_grad = layer_grad
            moment1, moment2 = moment

            # Normalize the weight gradient by batch size
            w_grad /= batch_size

            corrected_moments = []
            for i, grad in enumerate([w_grad, b_grad]):
                # Calculate the first and second moments
                moment1[i] = moment1[i] * self.beta1 + (1 - self.beta1) * grad
                moment2[i] = moment2[i] * self.beta2 + (1 - self.beta2) * np.square(grad)

                # Correct the moments
                corrected_moments.append([
                    moment1[i] / (1 - self.beta1 ** step),
                    moment2[i] / (1 - self.beta2 ** step)
                ])

            # Calculate the updates
            w_update = -self.lr * corrected_moments[0][0] / (corrected_moments[0][1] ** .5 + self.eps)
            b_update = -self.lr * corrected_moments[1][0] / (corrected_moments[1][1] ** .5 + self.eps)
            layer.update(w_update, b_update)

            # Save moments for next iteration
            new_moments.append([moment1, moment2])
        self.moments = new_moments
        self.save_vector(layers)

# Setup our parameters
epochs = 40
batch_size = 16
lr = 1e-3

# Run our training loop
adam = Adam(lr, .9, .999, 1e-8, .1)
training_run(epochs, batch_size, adam, train_data, valid_data, name="adam")
adam.plot_path()
