"""Bayesian regression for latent source model and Bitcoin.
This module implements the 'Bayesian regression for latent source model' method
for predicting price variation of Bitcoin. You can read more about the method
at https://arxiv.org/pdf/1410.1231.pdf.
This code was taken and adapted from: https://github.com/stavros0/bitcoin-price-prediction/blob/master/examples/millionaire.py#L8
"""
import numpy as np
import bigfloat as bg
from numpy.linalg import norm
from sklearn import linear_model
from sklearn.cluster import KMeans

def generate_timeseries(prices, n):
    """Use the first time period to generate time series
    Args:
        prices: A numpy array of floats representing prices over the first time
            period.
        n: An integer representing the length of time series.
    Returns:
        A 2-dimensional numpy array. Each row
        represents a time series of length n and its corresponding label
        (n+1-th column).
    """
    m = len(prices) - n
    ts = np.empty((m, n + 1))
    for i in range(m):
        ts[i, :n] = prices[i:i + n]
        ts[i, n] = prices[i + n] - prices[i + n - 1]
    return ts


def find_cluster_centers(timeseries, k):
    """Cluster timeseries in k clusters using k-means and return k cluster centers.
    Args:
        timeseries: A 2-dimensional numpy array generated by generate_timeseries().
        k: An integer representing the number of centers (e.g. 100).
    Returns:
        A 2-dimensional numpy array of size k x num_columns(timeseries). Each
        row represents a cluster center.
    """
    k_means = KMeans(n_clusters=k)
    k_means.fit(timeseries)
    return k_means.cluster_centers_

def choose_effective_centers(centers, n):
    """Choose n most effective cluster centers with high price variation."""
    return centers[np.argsort(np.ptp(centers, axis=1))[-n:]]

def predict_dpi(x, s):
    """Predict the average price change deltap_i, 1 <= i <= 3.
    Args:
        x: A numpy array of floats representing previous 180, 360, or 720 prices.
        s: A 2-dimensional numpy array generated by choose_effective_centers().
    Returns:
        A big float representing average price change deltap_i.
    """
    num = 0
    den = 0
    for i in range(len(s)):
        y_i = s[i, len(x)]
        x_i = s[i, :len(x)]
        exp = bg.exp(-0.25 * norm(x - x_i) ** 2)
        num += y_i * exp
        den += exp
    return num / den


def linear_regression_vars(prices, s1, s2, s3):
    """Use the second time period to generate the independent and dependent variables
       in the linear regression model
       deltap = w0 + w1 * deltap1 + w2 * deltap2 + w3 * deltap3
    Args:
        prices: A numpy array of floats representing prices over the second time
            period.
        s1-s3: A 2-dimensional numpy array generated by choose_effective_centers()
    Returns:
        A tuple (X, Y) representing the independent and dependent variables in
        the linear regression model. X represents [deltap1, deltap2, deltap3.
        Y is a numpy array of floats and each array element represents deltap.
    """
    X = np.empty((len(prices) - 721, 3))
    Y = np.empty(len(prices) - 721)
    for i in range(720, len(prices) - 1):
        dp = prices[i + 1] - prices[i]
        dp1 = predict_dpi(prices[i - 180:i], s1)
        dp2 = predict_dpi(prices[i - 360:i], s2)
        dp3 = predict_dpi(prices[i - 720:i], s3)
        X[i - 720, :] = [dp1, dp2, dp3]
        Y[i - 720] = dp
    return X, Y


def find_parameters_w(X, Y):
    """Find the parameter values w for the model which best fits X and Y.
    Args:
        X: A 2-dimensional numpy array representing the independent variables
            in the linear regression model.
        Y: A numpy array of floats representing the dependent variables in the
            linear regression model.
    Returns:
        A tuple (w0, w1, w2, w3) representing the parameter values w.
    """
    clf = linear_model.LinearRegression()
    clf.fit(X, Y)
    w0 = clf.intercept_
    w1, w2, w3 = clf.coef_
    return w0, w1, w2, w3


def predict_dps(prices, s1, s2, s3, w):
    """Predict average price changes (final estimations deltap) over the third
       time period.
    Args:
        prices: A numpy array of floats representing prices over the third time
            period.
        s1-s3: A 2-dimensional numpy array generated by choose_effective_centers()
    Returns:
        A numpy array of floats. Each array element represents the final
        estimation deltap.
    """
    dps = []
    w0, w1, w2, w3 = w
    for i in range(720, len(prices) - 1):
        dp1 = predict_dpi(prices[i - 180:i], s1)
        dp2 = predict_dpi(prices[i - 360:i], s2)
        dp3 = predict_dpi(prices[i - 720:i], s3)
        dp = w0 + w1 * dp1 + w2 * dp2 + w3 * dp3
        dps.append(float(dp))
    return dps


def evaluate_performance(prices, dps, t, step):
    """Use the third time period to evaluate the performance of the algorithm.
    Args:
        prices: A numpy array of floats representing prices over the third time
            period.
        dps: A numpy array of floats generated by predict_dps().
        t: the threshold.
        step: An integer representing time steps (when we make trading decisions).
    Returns:
        A number representing the bank balance.
    """
    bank_balance = 0
    position = 0
    for i in range(720, len(prices) - 1, step):
        # long position - BUY
        if dps[i - 720] > t and position <= 0:
            position += 1
            bank_balance -= prices[i]
        # short position - SELL
        if dps[i - 720] < -t and position >= 0:
            position -= 1
            bank_balance += prices[i]
    # sell what you bought
    if position == 1:
        bank_balance += prices[len(prices) - 1]
    # pay back what you borrowed
    if position == -1:
        bank_balance -= prices[len(prices) - 1]
    return bank_balance

def evaluate_performance2(prices, dps, t, step):
    """Use the third time period to evaluate the performance of the algorithm.
    Args:
        prices: A numpy array of floats representing prices over the third time
            period.
        dps: A numpy array of floats generated by predict_dps().
        t: the threshold.
        step: An integer representing time steps (when we make trading decisions).
    Returns:
        A number representing the bank balance.
    """
    bank_balance2 = 0
    bitcoin = 0
    for i in range(720, len(prices) - 1, step):
        #BUY
        if dps[i - 720] > t:
            bitcoin += 1
            bank_balance2 -= prices[i]
        # SELL
        if dps[i - 720] < -t:
            bitcoin -= 1
            bank_balance2 += prices[i]
    return bank_balance2, bitcoin

# Retrieve price from the textfile
'''here we take data from the MongoDB collection that has been saved as a json
file and converted to CSV for easy reading. We pull the prices out of the collection
'''
prices=[]
import csv
fhand = csv.reader(open("bitcoinprices.csv"), delimiter=",")
for line in fhand:
    for i in line:
        if i.startswith('price'):
            num= i[6:12]
            floats = float(num)
            prices.append(floats)
'''our entire dataset consists of 23070 observations (prices)'''

# Divide prices into three, roughly equal sized, periods:
# prices1, prices2, and prices3.
[prices1, prices2, prices3] = np.array_split(prices, 3)
'''each third of our entire dataset has a length of 77690'''


'''Use the first time period (prices1) to generate all possible time series of
appropriate length (180, 360, and 720).'''
timeseries180 = generate_timeseries(prices1, 180)
timeseries360 = generate_timeseries(prices1, 360)
timeseries720 = generate_timeseries(prices1, 720)


'''Cluster timeseries180 in 100 clusters using k-means, return the cluster
 centers (centers180), and choose the 20 most effective centers (s1).'''
centers180 = find_cluster_centers(timeseries180, 100)
s1 = choose_effective_centers(centers180, 20)

centers360 = find_cluster_centers(timeseries360, 100)
s2 = choose_effective_centers(centers360, 20)

centers720 = find_cluster_centers(timeseries720, 100)
s3 = choose_effective_centers(centers720, 20)

''' Use the second time period to generate the independent and dependent
variables in the linear regression model:'''
'''deltap = w0 + w1*deltap1 + w2*deltap2 + w3*deltap3 '''
Dpi_r, Dp = linear_regression_vars(prices2, s1, s2, s3)

# Find the parameter values w (w0, w1, w2, w3).
w = find_parameters_w(Dpi_r, Dp)
print w

# Predict average price changes over the third time period.
dps = predict_dps(prices3, s1, s2, s3, w)

'''Here is our our trading algorithm. We use the last subset of data (prices3)
to determine whether we buy or sell our bitcoin given we start at 0'''
bank_balance = evaluate_performance(prices3, dps, t=0.0001, step=1)
print bank_balance

bank_balance2 = evaluate_performance2(prices3, dps, t=0.0001, step=1)
print bank_balance2
