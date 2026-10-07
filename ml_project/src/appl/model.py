class LinearRegressionModel:
    def __init__(self, n_features, lr=0.001, model_l2=0.0):
        self.w = np.zeros(n_features, dtype=float)
        self.b = 0.0
        self.lr = lr
        self.model_l2 = model_l2

    def predict(self, x):
        x = np.asarray(x, dtype=float).reshape(-1)
        return float(np.dot(self.w, x) + self.b)

    def update(self, x, y):
        x = np.asarray(x, dtype=float).reshape(-1)
        y = float(y)

        pred = self.predict(x)
        err = pred - y

        self.w -= self.lr * (err * x + self.model_l2 * self.w)
        self.b -= self.lr * err

        return err